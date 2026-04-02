import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


User = get_user_model()

class Command(BaseCommand):
    help = 'Create a default superuser from environment variables'

    def handle(self, *args, **kwargs):
        email = os.environ.get('SUPERUSER_EMAIL')
        password = os.environ.get('SUPERUSER_PASSWORD')
        
        if not email or not password:
            self.stdout.write('SUPERUSER_EMAIL or SUPERUSER_PASSWORD not set, skipping.')
            return
            
        if User.objects.filter(email=email).exists():
            self.stdout.write(f'Superuser {email} already exists, skipping.')
            return
            
        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(f'Superuser {email} created successfully.')