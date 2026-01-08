"""
Management command to check and fix user status for group chat testing.
Run with: python manage.py check_users
"""
from django.core.management.base import BaseCommand
from myapp.models import User


class Command(BaseCommand):
    help = 'Check user status and fix inactive users for testing'

    def handle(self, *args, **options):
        self.stdout.write('Checking user status...\n')

        # Check all users
        users = User.objects.all().order_by('email')
        for user in users:
            status = 'ACTIVE' if user.status == 'active' else 'INACTIVE'
            self.stdout.write(f'{user.email} - {user.role} - {status}')

        # Fix common test users
        test_emails = ['staff@gmail.com', 'test@example.com', 'user@example.com']
        for email in test_emails:
            try:
                user = User.objects.get(email=email)
                if user.status != 'active':
                    user.status = 'active'
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Activated user: {email}'))
                else:
                    self.stdout.write(f'User {email} is already active')
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'User {email} does not exist'))

        self.stdout.write(self.style.SUCCESS('\nUser check complete!'))