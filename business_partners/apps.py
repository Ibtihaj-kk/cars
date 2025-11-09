from django.apps import AppConfig


class BusinessPartnersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'business_partners'
    verbose_name = 'Business Partners'
    
    def ready(self):
        """Import signals when the app is ready."""
        import business_partners.signals