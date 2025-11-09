#!/usr/bin/env python
"""
Setup script for automated stock monitoring cron jobs.
This script creates cron entries for regular stock monitoring and notification generation.
"""

import os
import sys
import subprocess
from datetime import datetime

def setup_cron_jobs():
    """Setup cron jobs for automated stock monitoring"""
    
    # Define cron jobs
    cron_jobs = [
        {
            'description': 'Stock Level Monitoring - Every 2 hours during business hours',
            'schedule': '0 8-18/2 * * *',  # Every 2 hours from 8 AM to 6 PM
            'command': 'cd /path/to/your/project && python manage.py monitor_stock_levels --send-email --critical-only'
        },
        {
            'description': 'Reorder Notification Generation - Daily at 9 AM',
            'schedule': '0 9 * * *',  # Daily at 9 AM
            'command': 'cd /path/to/your/project && python manage.py generate_reorder_notifications'
        },
        {
            'description': 'Comprehensive Stock Analysis - Daily at 6 PM',
            'schedule': '0 18 * * *',  # Daily at 6 PM
            'command': 'cd /path/to/your/project && python manage.py monitor_stock_levels --send-email'
        },
        {
            'description': 'Weekend Stock Check - Saturday at 10 AM',
            'schedule': '0 10 * * 6',  # Every Saturday at 10 AM
            'command': 'cd /path/to/your/project && python manage.py monitor_stock_levels --send-email --include-all'
        }
    ]

    print("Setting up automated stock monitoring cron jobs...")
    print("=" * 60)
    
    for job in cron_jobs:
        print(f"\nSetting up: {job['description']}")
        print(f"Schedule: {job['schedule']}")
        print(f"Command: {job['command']}")
        
        # Create cron entry
        cron_entry = f"{job['schedule']} {job['command']} # {job['description']}"
        
        try:
            # Add cron job
            subprocess.run(['crontab', '-l'], check=True, capture_output=True)
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout
            
            if cron_entry not in current_crontab:
                new_crontab = current_crontab + cron_entry + '\n'
                
                # Write new crontab
                process = subprocess.Popen(['crontab'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_crontab)
                process.wait()
                
                print("✓ Cron job added successfully")
            else:
                print("✓ Cron job already exists")
                
        except subprocess.CalledProcessError as e:
            print(f"✗ Error setting up cron job: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")

def create_systemd_service():
    """Create systemd service for stock monitoring (alternative to cron)"""
    
    service_content = f"""[Unit]
Description=Automated Stock Monitoring Service
After=network.target

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project
Environment=DJANGO_SETTINGS_MODULE=yallamotor.settings
ExecStart=/usr/bin/python manage.py monitor_stock_levels --send-email --critical-only

[Install]
WantedBy=multi-user.target
"""

    timer_content = f"""[Unit]
Description=Automated Stock Monitoring Timer
Requires=stock-monitoring.service

[Timer]
OnCalendar=*-*-* 08,10,12,14,16,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""

    print("\nCreating systemd service and timer for stock monitoring...")
    print("=" * 60)
    
    # Create service file
    service_file = '/etc/systemd/system/stock-monitoring.service'
    timer_file = '/etc/systemd/system/stock-monitoring.timer'
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        with open(timer_file, 'w') as f:
            f.write(timer_content)
        
        print("✓ Systemd service and timer files created")
        print("\nTo enable the timer, run:")
        print("sudo systemctl daemon-reload")
        print("sudo systemctl enable stock-monitoring.timer")
        print("sudo systemctl start stock-monitoring.timer")
        
    except PermissionError:
        print("✗ Permission denied. Run with sudo or as root user.")
        print("\nManual setup required:")
        print(f"1. Create {service_file} with the service content")
        print(f"2. Create {timer_file} with the timer content")
        print("3. Run: sudo systemctl daemon-reload")
        print("4. Run: sudo systemctl enable stock-monitoring.timer")
        print("5. Run: sudo systemctl start stock-monitoring.timer")

def create_monitoring_script():
    """Create a monitoring script that can be called by cron or systemd"""
    
    script_content = """#!/usr/bin/env python
"""
Automated stock monitoring script
This script can be called by cron or systemd for regular stock monitoring
"""

import os
import sys
import django
from datetime import datetime

# Add project path
PROJECT_PATH = '/path/to/your/project'
sys.path.insert(0, PROJECT_PATH)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor.settings')
django.setup()

from business_partners.management.commands.monitor_stock_levels import Command
from django.core.management import call_command

def main():
    print(f"Starting stock monitoring at {datetime.now()}")
    
    try:
        # Run stock monitoring
        call_command('monitor_stock_levels', 
                    send_email=True, 
                    critical_only=True,
                    verbosity=2)
        
        print("Stock monitoring completed successfully")
        
    except Exception as e:
        print(f"Error during stock monitoring: {e}")
        # Log error or send alert to admin
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
"""

    script_path = '/usr/local/bin/stock_monitoring.py'
    
    print("\nCreating monitoring script...")
    print("=" * 60)
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        print(f"✓ Monitoring script created at {script_path}")
        
    except PermissionError:
        print(f"✗ Permission denied. Manual setup required:")
        print(f"1. Create {script_path} with the script content")
        print("2. Make it executable: chmod +x stock_monitoring.py")
        print("3. Update the PROJECT_PATH in the script")

def main():
    """Main setup function"""
    
    print("Automated Stock Monitoring Setup")
    print("=" * 60)
    print("This script will set up automated stock monitoring for your Django application.")
    print("\nOptions:")
    print("1. Setup cron jobs (recommended for most systems)")
    print("2. Setup systemd service and timer (for systemd-based systems)")
    print("3. Create monitoring script only")
    print("4. Setup all options")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        setup_cron_jobs()
    elif choice == '2':
        create_systemd_service()
    elif choice == '3':
        create_monitoring_script()
    elif choice == '4':
        setup_cron_jobs()
        create_monitoring_script()
        print("\nNote: Systemd service setup requires root privileges.")
        print("Run 'sudo python setup_stock_monitoring_cron.py' and choose option 2 for systemd setup.")
    else:
        print("Invalid choice. Exiting.")
        return 1
    
    print("\nSetup completed!")
    print("\nNext steps:")
    print("1. Update the project paths in the cron jobs or scripts")
    print("2. Test the monitoring by running: python manage.py monitor_stock_levels")
    print("3. Monitor the logs to ensure automation is working")
    print("4. Configure email settings for notifications")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())