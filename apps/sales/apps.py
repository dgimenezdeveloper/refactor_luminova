from django.apps import AppConfig


class SalesConfig(AppConfig):
    """Aplicación de ventas: órdenes de venta, clientes, facturación."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sales"
    label = "sales"
    verbose_name = "Ventas - Órdenes y Clientes"
