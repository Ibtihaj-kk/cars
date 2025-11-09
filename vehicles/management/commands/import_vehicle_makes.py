import csv
import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from vehicles.models import VehicleMake


class Command(BaseCommand):
    help = 'Bulk import vehicle makes from CSV or JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the CSV or JSON file containing vehicle makes data'
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
            help='Update existing makes if they already exist'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        file_format = options['format']
        update_existing = options['update']
        dry_run = options['dry_run']

        if not os.path.exists(file_path):
            raise CommandError(f'File "{file_path}" does not exist.')

        # Auto-detect format from file extension if not specified
        if file_format == 'csv' and file_path.endswith('.json'):
            file_format = 'json'
        elif file_format == 'json' and file_path.endswith('.csv'):
            file_format = 'csv'

        self.stdout.write(f'Importing vehicle makes from {file_path} ({file_format} format)')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        try:
            if file_format == 'csv':
                makes_data = self.read_csv_file(file_path)
            else:
                makes_data = self.read_json_file(file_path)

            self.import_makes(makes_data, update_existing, dry_run)

        except Exception as e:
            raise CommandError(f'Error importing data: {str(e)}')

    def read_csv_file(self, file_path):
        """Read vehicle makes from CSV file"""
        makes_data = []
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Expected columns: name, name_arabic (optional), logo (optional)
            required_columns = ['name']
            if not all(col in reader.fieldnames for col in required_columns):
                raise CommandError(f'CSV file must contain columns: {", ".join(required_columns)}')
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is row 1)
                if not row['name'].strip():
                    self.stdout.write(
                        self.style.WARNING(f'Row {row_num}: Skipping empty name')
                    )
                    continue
                
                make_data = {
                    'name': row['name'].strip(),
                    'name_arabic': row.get('name_arabic', '').strip() or None,
                    'logo': row.get('logo', '').strip() or None,
                }
                makes_data.append(make_data)
        
        return makes_data

    def read_json_file(self, file_path):
        """Read vehicle makes from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
        
        # Handle both array of objects and object with makes array
        if isinstance(data, list):
            makes_data = data
        elif isinstance(data, dict) and 'makes' in data:
            makes_data = data['makes']
        else:
            raise CommandError('JSON file must contain an array of makes or an object with "makes" key')
        
        # Validate required fields
        for i, make_data in enumerate(makes_data):
            if not isinstance(make_data, dict):
                raise CommandError(f'Make {i+1}: Must be an object')
            if 'name' not in make_data or not make_data['name'].strip():
                raise CommandError(f'Make {i+1}: Missing or empty "name" field')
        
        return makes_data

    def import_makes(self, makes_data, update_existing, dry_run):
        """Import vehicle makes into database"""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        with transaction.atomic():
            for make_data in makes_data:
                try:
                    name = make_data['name']
                    
                    # Check if make already exists
                    existing_make = VehicleMake.objects.filter(name__iexact=name).first()
                    
                    if existing_make:
                        if update_existing:
                            if not dry_run:
                                # Update existing make
                                existing_make.name_arabic = make_data.get('name_arabic') or existing_make.name_arabic
                                if make_data.get('logo'):
                                    existing_make.logo = make_data['logo']
                                existing_make.save()
                            
                            updated_count += 1
                            self.stdout.write(f'Updated: {name}')
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'Skipped (already exists): {name}')
                            )
                    else:
                        if not dry_run:
                            # Create new make
                            VehicleMake.objects.create(
                                name=name,
                                name_arabic=make_data.get('name_arabic'),
                                logo=make_data.get('logo')
                            )
                        
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Created: {name}'))

                except Exception as e:
                    error_msg = f'Error processing make "{make_data.get("name", "Unknown")}": {str(e)}'
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))

            if dry_run:
                # Rollback transaction in dry run mode
                transaction.set_rollback(True)

        # Print summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('IMPORT SUMMARY')
        self.stdout.write('='*50)
        self.stdout.write(f'Total processed: {len(makes_data)}')
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.WARNING(f'Updated: {updated_count}'))
        self.stdout.write(f'Skipped: {skipped_count}')
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
name,name_arabic,logo
Toyota,تويوتا,https://example.com/toyota-logo.png
Honda,هوندا,
BMW,بي إم دبليو,https://example.com/bmw-logo.png
Mercedes-Benz,مرسيدس بنز,
"""

# Sample JSON format:
"""
{
  "makes": [
    {
      "name": "Toyota",
      "name_arabic": "تويوتا",
      "logo": "https://example.com/toyota-logo.png"
    },
    {
      "name": "Honda",
      "name_arabic": "هوندا"
    },
    {
      "name": "BMW",
      "name_arabic": "بي إم دبليو",
      "logo": "https://example.com/bmw-logo.png"
    }
  ]
}
"""