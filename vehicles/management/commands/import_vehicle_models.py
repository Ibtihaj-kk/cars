import csv
import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from vehicles.models import VehicleMake, VehicleModelTaxonomy


class Command(BaseCommand):
    help = 'Bulk import vehicle models from CSV or JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the CSV or JSON file containing vehicle models data'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            default='csv',
            help='File format (csv or json). Default is csv.'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing models if they already exist'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
        parser.add_argument(
            '--create-makes',
            action='store_true',
            help='Create vehicle makes if they do not exist'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        file_format = options['format']
        update_existing = options['update']
        dry_run = options['dry_run']
        create_makes = options['create_makes']

        if not os.path.exists(file_path):
            raise CommandError(f'File "{file_path}" does not exist.')

        # Auto-detect format from file extension if not specified
        if file_format == 'csv' and file_path.endswith('.json'):
            file_format = 'json'
        elif file_format == 'json' and file_path.endswith('.csv'):
            file_format = 'csv'

        self.stdout.write(f'Importing vehicle models from {file_path} ({file_format} format)')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        try:
            if file_format == 'csv':
                models_data = self.read_csv_file(file_path)
            else:
                models_data = self.read_json_file(file_path)

            self.import_models(models_data, update_existing, dry_run, create_makes)

        except Exception as e:
            raise CommandError(f'Error importing data: {str(e)}')

    def read_csv_file(self, file_path):
        """Read vehicle models from CSV file"""
        models_data = []
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Expected columns: make_name, name, model_code (optional)
            required_columns = ['make_name', 'name']
            if not all(col in reader.fieldnames for col in required_columns):
                raise CommandError(f'CSV file must contain columns: {", ".join(required_columns)}')
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is row 1)
                if not row['make_name'].strip() or not row['name'].strip():
                    self.stdout.write(
                        self.style.WARNING(f'Row {row_num}: Skipping row with empty make_name or name')
                    )
                    continue
                
                model_data = {
                    'make_name': row['make_name'].strip(),
                    'name': row['name'].strip(),
                    'model_code': row.get('model_code', '').strip() or None,
                }
                models_data.append(model_data)
        
        return models_data

    def read_json_file(self, file_path):
        """Read vehicle models from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
        
        # Handle both array of objects and object with models array
        if isinstance(data, list):
            models_data = data
        elif isinstance(data, dict) and 'models' in data:
            models_data = data['models']
        else:
            raise CommandError('JSON file must contain an array of models or an object with "models" key')
        
        # Validate required fields
        for i, model_data in enumerate(models_data):
            if not isinstance(model_data, dict):
                raise CommandError(f'Model {i+1}: Must be an object')
            if 'make_name' not in model_data or not model_data['make_name'].strip():
                raise CommandError(f'Model {i+1}: Missing or empty "make_name" field')
            if 'name' not in model_data or not model_data['name'].strip():
                raise CommandError(f'Model {i+1}: Missing or empty "name" field')
        
        return models_data

    def import_models(self, models_data, update_existing, dry_run, create_makes):
        """Import vehicle models into database"""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        makes_created = 0
        errors = []

        # Cache for makes to avoid repeated database queries
        makes_cache = {}

        with transaction.atomic():
            for model_data in models_data:
                try:
                    make_name = model_data['make_name']
                    model_name = model_data['name']
                    model_code = model_data.get('model_code')
                    
                    # Get or create vehicle make
                    if make_name not in makes_cache:
                        try:
                            make = VehicleMake.objects.get(name__iexact=make_name)
                            makes_cache[make_name] = make
                        except VehicleMake.DoesNotExist:
                            if create_makes:
                                if not dry_run:
                                    make = VehicleMake.objects.create(name=make_name)
                                    makes_cache[make_name] = make
                                    makes_created += 1
                                    self.stdout.write(f'Created make: {make_name}')
                                else:
                                    # In dry run, create a mock make object
                                    make = VehicleMake(name=make_name)
                                    makes_cache[make_name] = make
                                    makes_created += 1
                                    self.stdout.write(f'Would create make: {make_name}')
                            else:
                                error_msg = f'Make "{make_name}" does not exist. Use --create-makes to create it.'
                                errors.append(error_msg)
                                self.stdout.write(self.style.ERROR(error_msg))
                                continue
                    
                    make = makes_cache[make_name]
                    
                    # Check if model already exists
                    existing_model = VehicleModelTaxonomy.objects.filter(
                        make=make, name__iexact=model_name
                    ).first()
                    
                    if existing_model:
                        if update_existing:
                            if not dry_run:
                                # Update existing model
                                if model_code:
                                    existing_model.model_code = model_code
                                existing_model.save()
                            
                            updated_count += 1
                            self.stdout.write(f'Updated: {make_name} {model_name}')
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'Skipped (already exists): {make_name} {model_name}')
                            )
                    else:
                        if not dry_run:
                            # Create new model
                            VehicleModelTaxonomy.objects.create(
                                make=make,
                                name=model_name,
                                model_code=model_code
                            )
                        
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Created: {make_name} {model_name}'))

                except Exception as e:
                    error_msg = f'Error processing model "{model_data.get("make_name", "Unknown")} {model_data.get("name", "Unknown")}": {str(e)}'
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))

            if dry_run:
                # Rollback transaction in dry run mode
                transaction.set_rollback(True)

        # Print summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('IMPORT SUMMARY')
        self.stdout.write('='*50)
        self.stdout.write(f'Total processed: {len(models_data)}')
        self.stdout.write(self.style.SUCCESS(f'Models created: {created_count}'))
        self.stdout.write(self.style.WARNING(f'Models updated: {updated_count}'))
        self.stdout.write(f'Models skipped: {skipped_count}')
        if makes_created > 0:
            self.stdout.write(self.style.SUCCESS(f'Makes created: {makes_created}'))
        self.stdout.write(self.style.ERROR(f'Errors: {len(errors)}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN COMPLETED - No changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nImport completed successfully!'))

        if errors:
            self.stdout.write('\nErrors encountered:')
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))


# Sample CSV format:
"""
make_name,name,model_code
Toyota,Camry,XV70
Toyota,Corolla,E210
Honda,Civic,FC1
Honda,Accord,CV3
BMW,3 Series,G20
BMW,X5,G05
Mercedes-Benz,C-Class,W206
Mercedes-Benz,E-Class,W213
"""

# Sample JSON format:
"""
{
  "models": [
    {
      "make_name": "Toyota",
      "name": "Camry",
      "model_code": "XV70"
    },
    {
      "make_name": "Toyota",
      "name": "Corolla",
      "model_code": "E210"
    },
    {
      "make_name": "Honda",
      "name": "Civic",
      "model_code": "FC1"
    },
    {
      "make_name": "BMW",
      "name": "3 Series",
      "model_code": "G20"
    }
  ]
}
"""