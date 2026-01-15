"""
apps.sales.models - Re-exportación de modelos de ventas

Este módulo re-exporta los modelos relacionados con clientes y órdenes de venta
desde App_LUMINOVA para facilitar la migración gradual.

Uso recomendado:
    from apps.sales.models import Cliente, OrdenVenta, ItemOrdenVenta
"""

from App_LUMINOVA.models import (
    # Clientes
    Cliente,
    
    # Órdenes de Venta
    OrdenVenta,
    ItemOrdenVenta,
    HistorialOV,
    
    # Facturación
    Factura,
)

__all__ = [
    'Cliente',
    'OrdenVenta',
    'ItemOrdenVenta',
    'HistorialOV',
    'Factura',
]
