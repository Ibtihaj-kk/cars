#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from business_partners.models import BusinessPartner

vendors = BusinessPartner.objects.filter(type='vendor')
print('Vendors found:', vendors.count())
for v in vendors:
    print(f'ID: {v.id}, Name: {v.name}, Email: {v.user.email if v.user else "No user"}')