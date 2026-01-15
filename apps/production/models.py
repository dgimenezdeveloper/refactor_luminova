"""
apps.production.models - Re-exportación de modelos de producción

Este módulo re-exporta los modelos relacionados con órdenes de producción
y control desde App_LUMINOVA para facilitar la migración gradual.

Uso recomendado:
    from apps.production.models import OrdenProduccion, EstadoOrden, Reportes
"""

from App_LUMINOVA.models import (
    # Estados y Sectores
    EstadoOrden,
    SectorAsignado,
    
    # Órdenes de Producción
    OrdenProduccion,
    
    # Reportes
    Reportes,
    
    # Lotes
    LoteProductoTerminado,
)

__all__ = [
    'EstadoOrden',
    'SectorAsignado',
    'OrdenProduccion',
    'Reportes',
    'LoteProductoTerminado',
]
