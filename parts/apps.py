from django.apps import AppConfig


class PartsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parts'

    def ready(self):
        import parts.signals
