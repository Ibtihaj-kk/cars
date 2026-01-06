"""
Management command to check and block unverified users after 3 days.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.email_service.handlers.verification_handler import EmailVerificationHandler


class Command(BaseCommand):
    help = 'Check and block unverified user accounts after 3 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the operation without actually blocking users'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        handler = EmailVerificationHandler()
        
        if verbose:
            # Show verification statistics
            stats = handler.get_verification_stats()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Verification Statistics:\n"
                    f"- Total Users: {stats['total_users']}\n"
                    f"- Verified Users: {stats['verified_users']} ({stats['verification_rate']:.1f}%)\n"
                    f"- Unverified Active: {stats['unverified_active']}\n"
                    f"- Approaching 3-day limit: {stats['approaching_limit']}"
                )
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run mode: Would check for unverified users exceeding 3-day limit"
                )
            )
            
            # Show users who would be blocked
            from django.contrib.auth import get_user_model
            from datetime import timedelta
            
            User = get_user_model()
            expiry_time = timezone.now() - timedelta(days=3)
            
            unverified_users = User.objects.filter(
                is_verified=False,
                email_verification_sent_at__lte=expiry_time,
                is_active=True
            )
            
            if unverified_users.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Would block {unverified_users.count()} users:"
                    )
                )
                for user in unverified_users:
                    days_unverified = (timezone.now() - user.email_verification_sent_at).days
                    self.stdout.write(
                        f"  - {user.email} (unverified for {days_unverified} days)"
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS("No users would be blocked at this time")
                )
                
            return
        
        # Actually perform the check and block
        blocked_count = handler.check_verification_expiry()
        
        if blocked_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Blocked {blocked_count} user(s) who exceeded 3-day verification limit"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("No users exceeded 3-day verification limit")
            )