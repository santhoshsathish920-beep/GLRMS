import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'glrms.settings')
django.setup()

from django.contrib.auth.models import User
from lands.models import Officer, District

# Create a superuser
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser 'admin' created.")
else:
    user = User.objects.get(username='admin')
    print("Superuser 'admin' already exists.")

# Create an Officer profile for the superuser
if not Officer.objects.filter(user=user).exists():
    officer = Officer.objects.create(
        user=user,
        role='ADMIN',
        employee_id='TN-ADMIN-001',
        phone='9840012345'
    )
    print("Officer profile 'TN-ADMIN-001' created for user 'admin'.")
else:
    print("Officer profile already exists.")
