from django.urls import path
from . import views

app_name = 'vendor_employees'

urlpatterns = [
    path('vendor/employees/', views.employee_list, name='employee_list'),
    path('vendor/employees/invite/', views.employee_invite, name='employee_invite'),
    path('vendor/employees/accept-invitation/<str:uidb64>/<str:token>/', views.accept_invitation, name='accept_invitation'),
    path('vendor/employees/<int:employee_id>/update/', views.employee_update, name='employee_update'),
    path('vendor/employees/<int:employee_id>/deactivate/', views.employee_deactivate, name='employee_deactivate'),
    path('vendor/roles/', views.role_list, name='role_list'),
    path('vendor/roles/create/', views.role_create, name='role_create'),
    path('vendor/roles/<int:role_id>/edit/', views.role_edit, name='role_edit'),
    path('vendor/roles/<int:role_id>/permissions/', views.role_permissions, name='role_permissions'),
    
    # Locations
    path('vendor/locations/', views.location_list, name='location_list'),
    path('vendor/locations/create/', views.location_create, name='location_create'),
    path('vendor/locations/<int:location_id>/edit/', views.location_edit, name='location_edit'),
    path('vendor/locations/<int:location_id>/toggle-status/', views.location_toggle_status, name='location_toggle_status'),
]
