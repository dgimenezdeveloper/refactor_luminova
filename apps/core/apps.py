from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Aplicación core: autenticación, empresas, usuarios y configuración base."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core - Autenticación y Empresas"
