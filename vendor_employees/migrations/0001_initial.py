from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('business_partners', '0027_vendorprofile_bank_account_holder_name_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='VendorPagePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=150)),
                ('name', models.CharField(max_length=255)),
                ('category', models.CharField(blank=True, max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vendor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='page_permissions', to='business_partners.businesspartner')),
            ],
            options={
                'ordering': ['category', 'name'],
                'unique_together': {('vendor', 'code')},
                'indexes': [
                    models.Index(fields=['vendor', 'code'], name='vendor_employees_vendor_i_d1f35b_idx'),
                    models.Index(fields=['code', 'is_active'], name='vendor_employees_code_i_4a0f3d_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='VendorRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('is_system', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_vendor_roles', to=settings.AUTH_USER_MODEL)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employee_roles', to='business_partners.businesspartner')),
            ],
            options={
                'ordering': ['name'],
                'unique_together': {('vendor', 'name')},
                'indexes': [
                    models.Index(fields=['vendor', 'is_active'], name='vendor_employees_vendor_i_109c63_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='VendorEmployee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invited_vendor_employees', to=settings.AUTH_USER_MODEL)),
                ('role', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='vendor_employees.vendorrole')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='vendor_employee', to=settings.AUTH_USER_MODEL)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employees', to='business_partners.businesspartner')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['vendor', 'is_active'], name='vendor_employees_vendor_i_6f4ef4_idx'),
                    models.Index(fields=['user', 'is_active'], name='vendor_employees_user_i_6ba5d8_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='VendorRolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vendor_employees.vendorpagepermission')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vendor_employees.vendorrole')),
            ],
            options={
                'unique_together': {('role', 'permission')},
                'indexes': [
                    models.Index(fields=['role', 'permission'], name='vendor_employees_role_i_3c2a88_idx'),
                ],
            },
        ),
        migrations.AddField(
            model_name='vendorrole',
            name='permissions',
            field=models.ManyToManyField(blank=True, through='vendor_employees.VendorRolePermission', to='vendor_employees.vendorpagepermission'),
        ),
    ]
