from django.apps import AppConfig


class PurchasingConfig(AppConfig):
    """Aplicación de compras: órdenes de compra, proveedores, fabricantes."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.purchasing"
    label = "purchasing"
    verbose_name = "Compras - Órdenes y Proveedores"
