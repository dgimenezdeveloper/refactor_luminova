"""
apps.purchasing.models - Re-exportación de modelos de compras

Este módulo re-exporta los modelos relacionados con proveedores, ofertas
y órdenes de compra desde App_LUMINOVA para facilitar la migración gradual.

Uso recomendado:
    from apps.purchasing.models import Proveedor, Orden, OfertaProveedor
"""

from App_LUMINOVA.models import (
    # Proveedores
    Proveedor,
    OfertaProveedor,
    
    # Órdenes de Compra
    Orden,
)

__all__ = [
    'Proveedor',
    'OfertaProveedor',
    'Orden',
]
