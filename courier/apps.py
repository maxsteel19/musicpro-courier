from django.apps import AppConfig


class CourierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courier'
    verbose_name = 'Courier (Proveedor - Cliente)'

    def ready(self):
        from . import signals  # noqa: F401  (conecta la auditoría de login/logout)
