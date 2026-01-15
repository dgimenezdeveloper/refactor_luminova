"""
apps.inventory.models - Re-exportación de modelos de inventario

Este módulo re-exporta los modelos relacionados con inventario, stock,
productos e insumos desde App_LUMINOVA para facilitar la migración gradual.

Uso recomendado:
    from apps.inventory.models import ProductoTerminado, Insumo, StockInsumo
"""

from App_LUMINOVA.models import (
    # Categorías
    CategoriaProductoTerminado,
    CategoriaInsumo,
    
    # Fabricantes
    Fabricante,
    
    # Productos e Insumos
    ProductoTerminado,
    Insumo,
    ComponenteProducto,
    
    # Stock
    StockInsumo,
    StockProductoTerminado,
    MovimientoStock,
)

__all__ = [
    'CategoriaProductoTerminado',
    'CategoriaInsumo',
    'Fabricante',
    'ProductoTerminado',
    'Insumo',
    'ComponenteProducto',
    'StockInsumo',
    'StockProductoTerminado',
    'MovimientoStock',
]
