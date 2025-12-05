import os
import sys
import django
from django.core.management import call_command
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

def setup_django():
    """Initialize Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
    try:
        django.setup()
        print("✅ Django environment loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading Django environment: {e}")
        sys.exit(1)

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def show_migrations():
    print_header("CURRENT MIGRATION STATUS")
    try:
        call_command('showmigrations')
    except Exception as e:
        print(f"❌ Error showing migrations: {e}")

def run_standard_migrations():
    print_header("RUNNING STANDARD MIGRATIONS")
    try:
        call_command('migrate')
        print("\n✅ All migrations completed successfully.")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\n💡 Tip: If tables already exist, try the 'Fake Initial' option.")

def run_fake_initial_migrations():
    print_header("RUNNING MIGRATIONS WITH --fake-initial")
    print("This option is useful if tables already exist in the database.\n")
    try:
        call_command('migrate', fake_initial=True)
        print("\n✅ Fake-initial migrations completed successfully.")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")

def make_migrations():
    print_header("MAKING MIGRATIONS")
    print("This will generate new migration files for changes in models.\n")
    try:
        call_command('makemigrations')
        print("\n✅ Make migrations completed.")
    except Exception as e:
        print(f"\n❌ Make migrations failed: {e}")

def run_safe_dependency_order():
    print_header("RUNNING MIGRATIONS IN SAFE ORDER")
    
    # Order matters! Core dependencies first.
    # users usually comes first if it has a custom user model.
    ordered_apps = [
        'users',           # Custom User model
        'contenttypes',    # Django core
        'auth',            # Django auth
        'admin',           # Django admin
        'sessions',        # Django sessions
        'messages',        # Django messages
        'sites',           # Django sites
        'core',            # Project core
        'content',         # CMS
        'vehicles',        # Vehicle models
        'listings',        # Listings depend on vehicles/users
        'business_partners', # Vendor profiles
        'parts',           # Parts system
        'orders',          # Orders (depends on parts)
        'inquiries',       # Messaging
        'reviews',         # Reviews
        'subscriptions',   # Payments
        'notifications',   # Notifications
        'analytics',       # Analytics
        'admin_panel',     # Custom admin
    ]
    
    for app in ordered_apps:
        print(f"\n🔄 Migrating app: {app}...")
        try:
            call_command('migrate', app)
            print(f"✅ {app} migrated.")
        except Exception as e:
            print(f"❌ Failed to migrate {app}: {e}")
            print(f"  Continuing to next app...")

    print("\n🔄 Running remaining migrations...")
    try:
        call_command('migrate')
        print("✅ Remaining migrations completed.")
    except Exception as e:
        print(f"❌ Final pass failed: {e}")

def run_specific_app():
    print_header("MIGRATE SPECIFIC APP")
    app_name = input("Enter app label (e.g., users, listings): ").strip()
    if not app_name:
        print("❌ No app name provided.")
        return
    
    fake = input("Run as fake? (y/n): ").lower() == 'y'
    
    try:
        if fake:
            print(f"🔄 Faking migrations for {app_name}...")
            call_command('migrate', app_name, fake=True)
        else:
            print(f"🔄 Migrating {app_name}...")
            call_command('migrate', app_name)
        print(f"✅ {app_name} migration completed.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")

def fix_content_types():
    print_header("FIXING CONTENT TYPES & PERMISSIONS")
    print("Removing stale content types and updating permissions...")
    try:
        call_command('remove_stale_contenttypes', interactive=False)
        print("✅ Stale content types removed.")
    except Exception as e:
        print(f"⚠️ Could not remove stale content types: {e}")

def main():
    setup_django()
    
    while True:
        print("\n" + "="*60)
        print(" CORPORATE DOCK - CPANEL MIGRATION HELPER")
        print("="*60)
        print("1. Show Migration Status")
        print("2. Make Migrations (Prepare changes)")
        print("3. Run All Migrations (Standard)")
        print("4. Run All Migrations (Fake Initial) - Use if tables exist")
        print("5. Run in Safe Dependency Order (Fixes dependency errors)")
        print("6. Migrate Specific App (Interactive)")
        print("7. Fix Content Types (Cleanup)")
        print("0. Exit")
        
        choice = input("\nEnter choice (0-7): ").strip()
        
        if choice == '1':
            show_migrations()
        elif choice == '2':
            make_migrations()
        elif choice == '3':
            run_standard_migrations()
        elif choice == '4':
            run_fake_initial_migrations()
        elif choice == '5':
            run_safe_dependency_order()
        elif choice == '6':
            run_specific_app()
        elif choice == '7':
            fix_content_types()
        elif choice == '0':
            print("\nGoodbye! 👋")
            break
        else:
            print("\n❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == '__main__':
    main()
