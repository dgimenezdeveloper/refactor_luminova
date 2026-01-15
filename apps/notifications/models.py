"""
apps.notifications.models - Re-exportación de modelos de notificaciones

Este módulo re-exporta los modelos de notificaciones desde App_LUMINOVA
para facilitar la migración gradual.

Uso recomendado:
    from apps.notifications.models import NotificacionSistema
"""

from App_LUMINOVA.models import (
    NotificacionSistema,
)

__all__ = [
    'NotificacionSistema',
]
