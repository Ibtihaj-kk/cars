# Generated manually to populate parts_number field

from django.db import migrations


def populate_parts_number(apps, schema_editor):
    """
    Populate parts_number field with unique values for existing parts.
    """
    Part = apps.get_model('parts', 'Part')
    
    # Get all parts that don't have a parts_number
    parts_without_number = Part.objects.filter(parts_number__isnull=True) | Part.objects.filter(parts_number='')
    
    # Generate unique parts numbers
    for index, part in enumerate(parts_without_number, start=1):
        # Use a combination of 'PN' prefix and zero-padded number
        parts_number = f"PN{index:06d}"
        
        # Ensure uniqueness by checking if it already exists
        while Part.objects.filter(parts_number=parts_number).exists():
            index += 1
            parts_number = f"PN{index:06d}"
        
        part.parts_number = parts_number
        part.save(update_fields=['parts_number'])


def reverse_populate_parts_number(apps, schema_editor):
    """
    Reverse operation - clear auto-generated parts numbers.
    """
    Part = apps.get_model('parts', 'Part')
    
    # Clear parts numbers that match our auto-generated pattern
    Part.objects.filter(parts_number__startswith='PN').update(parts_number=None)


class Migration(migrations.Migration):

    dependencies = [
        ('parts', '0006_add_parts_master_fields'),
    ]

    operations = [
        migrations.RunPython(
            populate_parts_number,
            reverse_populate_parts_number,
        ),
    ]