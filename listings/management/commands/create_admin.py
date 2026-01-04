from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser'

    def handle(self, *args, **options):
        if not User.objects.filter(email='admin@carsyncro.com').exists():
            User.objects.create_superuser(
                email='admin@carsyncro.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(
                self.style.SUCCESS('Successfully created superuser "admin@carsyncro.com"')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Superuser "admin@carsyncro.com" already exists')
            )