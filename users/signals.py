"""
Signals for user management and BP number assignment
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


@receiver(post_save, sender=User)
def assign_bp_number_on_user_creation(sender, instance, created, **kwargs):
    """
    Automatically assign ISO 8000 compliant BP number when a user is created
    """
    if created and not instance.bp_number:
        # Import here to avoid circular imports
        from core.bp_number_system import BPNumberSystem
        bp_system = BPNumberSystem()
        instance.bp_number = bp_system.generate_bp_number(instance)
        # Save without triggering signals again
        User.objects.filter(pk=instance.pk).update(bp_number=instance.bp_number)