from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from business_partners.models import ReorderNotification


class Command(BaseCommand):
    help = 'Clean up old reorder notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete completed notifications older than this many days (default: 30)'
        )
        parser.add_argument(
            '--dismissed-days',
            type=int,
            default=7,
            help='Delete dismissed notifications older than this many days (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dismissed_days = options['dismissed_days']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('Starting reorder notification cleanup...')
        )
        
        cutoff_date = timezone.now() - timedelta(days=days)
        dismissed_cutoff_date = timezone.now() - timedelta(days=dismissed_days)
        
        # Find completed notifications older than specified days
        completed_notifications = ReorderNotification.objects.filter(
            status='completed',
            created_at__lt=cutoff_date
        )
        
        # Find dismissed notifications older than specified days
        dismissed_notifications = ReorderNotification.objects.filter(
            status='dismissed',
            created_at__lt=dismissed_cutoff_date
        )
        
        completed_count = completed_notifications.count()
        dismissed_count = dismissed_notifications.count()
        total_count = completed_count + dismissed_count
        
        if total_count == 0:
            self.stdout.write('No notifications to clean up.')
            return
        
        self.stdout.write(
            f'Found {completed_count} completed notifications older than {days} days'
        )
        self.stdout.write(
            f'Found {dismissed_count} dismissed notifications older than {dismissed_days} days'
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Would delete {total_count} notifications (dry run mode)'
                )
            )
            
            # Show some examples
            if completed_count > 0:
                self.stdout.write('\nCompleted notifications to delete:')
                for notification in completed_notifications[:5]:
                    self.stdout.write(
                        f'  - {notification.part.name} for {notification.vendor.name} '
                        f'(created: {notification.created_at.strftime("%Y-%m-%d")})'
                    )
                if completed_count > 5:
                    self.stdout.write(f'  ... and {completed_count - 5} more')
            
            if dismissed_count > 0:
                self.stdout.write('\nDismissed notifications to delete:')
                for notification in dismissed_notifications[:5]:
                    self.stdout.write(
                        f'  - {notification.part.name} for {notification.vendor.name} '
                        f'(created: {notification.created_at.strftime("%Y-%m-%d")})'
                    )
                if dismissed_count > 5:
                    self.stdout.write(f'  ... and {dismissed_count - 5} more')
        else:
            # Actually delete the notifications
            deleted_completed = completed_notifications.delete()[0]
            deleted_dismissed = dismissed_notifications.delete()[0]
            total_deleted = deleted_completed + deleted_dismissed
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {total_deleted} old notifications:'
                )
            )
            self.stdout.write(f'  - {deleted_completed} completed notifications')
            self.stdout.write(f'  - {deleted_dismissed} dismissed notifications')
        
        # Show statistics for remaining notifications
        remaining_stats = self.get_notification_stats()
        self.stdout.write('\nRemaining notification statistics:')
        for status, count in remaining_stats.items():
            self.stdout.write(f'  - {status.title()}: {count}')

    def get_notification_stats(self):
        """Get statistics for remaining notifications"""
        stats = {}
        
        for status_choice in ReorderNotification.STATUS_CHOICES:
            status = status_choice[0]
            count = ReorderNotification.objects.filter(status=status).count()
            stats[status] = count
        
        return stats