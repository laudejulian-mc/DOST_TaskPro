#!/usr/bin/env python
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from myapp.models import User as MyUser
from myapp.views import export_full_report_pdf

# Create a mock request
factory = RequestFactory()
request = factory.get('/administrator/reports/export-full/?year=2025')

# Create or get an admin user
try:
    admin_user = MyUser.objects.filter(role='admin').first()
    if not admin_user:
        admin_user = MyUser.objects.create_user('testadmin', 'test@example.com', 'password', role='admin')
    request.user = admin_user

    print("Testing PDF export...")
    response = export_full_report_pdf(request)
    print('SUCCESS: PDF generated without errors')
    print(f'Response status: {response.status_code}')
    print(f'Content type: {response.get("Content-Type")}')
    print(f'Content length: {len(response.content)} bytes')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()