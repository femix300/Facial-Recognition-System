import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates a superuser from environment variables'

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not email or not password:
            self.stdout.write(self.style.ERROR('DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD environment variables must be set.'))
            return

        if User.objects.filter(username=email).exists():
            self.stdout.write(self.style.WARNING(f'Superuser with email {email} already exists.'))
        else:
            User.objects.create_superuser(username=email, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Successfully created superuser {email}'))