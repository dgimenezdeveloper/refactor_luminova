from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """Aplicación de inventario: productos, insumos, categorías, stock."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"
    label = "inventory"
    verbose_name = "Inventario - Productos e Insumos"
