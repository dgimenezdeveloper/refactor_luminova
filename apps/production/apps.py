from django.apps import AppConfig


class ProductionConfig(AppConfig):
    """Aplicación de producción: órdenes de producción, reportes, sectores."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.production"
    label = "production"
    verbose_name = "Producción - Órdenes y Reportes"
