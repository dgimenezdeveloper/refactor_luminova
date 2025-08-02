"""
Servicio de notificaciones para mantener separación de responsabilidades entre módulos.
Este servicio permite que cada módulo notifique a otros sin acceso directo a sus funcionalidades.
"""

from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.db.models import Q
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio para gestionar notificaciones entre módulos del sistema"""
    
    @staticmethod
    def crear_notificacion(
        tipo: str,
        titulo: str,
        mensaje: str,
        remitente: User,
        destinatario_grupo: str,
        prioridad: str = 'media',
        datos_contexto: Optional[Dict[str, Any]] = None,
        fecha_expiracion: Optional[timezone.datetime] = None
    ) -> 'NotificacionSistema':
        """
        Crea una nueva notificación en el sistema
        
        Args:
            tipo: Tipo de notificación (stock_bajo, oc_creada, etc.)
            titulo: Título breve de la notificación
            mensaje: Mensaje detallado
            remitente: Usuario que envía la notificación
            destinatario_grupo: Grupo destinatario (compras, deposito, etc.)
            prioridad: Prioridad de la notificación (baja, media, alta, critica)
            datos_contexto: Datos adicionales en formato dict
            fecha_expiracion: Fecha de expiración opcional
        
        Returns:
            NotificacionSistema: La notificación creada
        """
        from ..models import NotificacionSistema
        
        notificacion = NotificacionSistema.objects.create(
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            remitente=remitente,
            destinatario_grupo=destinatario_grupo,
            prioridad=prioridad,
            datos_contexto=datos_contexto or {},
            fecha_expiracion=fecha_expiracion
        )
        
        logger.info(
            f"Notificación creada: {tipo} de {remitente.username} para {destinatario_grupo} - {titulo}"
        )
        
        return notificacion
    
    @staticmethod
    def notificar_stock_bajo(insumo, deposito, usuario_remitente, umbral_critico: int = 10) -> 'NotificacionSistema':
        """Notifica al departamento de compras sobre stock bajo"""
        titulo = f"Stock crítico: {insumo.descripcion}"
        mensaje = (
            f"El insumo '{insumo.descripcion}' en el depósito '{deposito.nombre}' "
            f"tiene stock crítico ({insumo.stock} unidades). "
            f"Se recomienda generar una orden de compra."
        )
        
        datos_contexto = {
            'insumo_id': insumo.id,
            'insumo_descripcion': insumo.descripcion,
            'deposito_id': deposito.id,
            'deposito_nombre': deposito.nombre,
            'stock_actual': insumo.stock,
            'umbral_critico': umbral_critico,
            'accion_sugerida': 'crear_oc'
        }
        
        prioridad = 'critica' if insumo.stock <= 5 else 'alta'
        
        return NotificationService.crear_notificacion(
            tipo='stock_bajo',
            titulo=titulo,
            mensaje=mensaje,
            remitente=usuario_remitente,
            destinatario_grupo='compras',
            prioridad=prioridad,
            datos_contexto=datos_contexto
        )
    
    @staticmethod
    def notificar_oc_creada(oc, usuario_remitente) -> 'NotificacionSistema':
        """Notifica al depósito que se creó una OC"""
        titulo = f"OC #{oc.numero_orden} creada"
        mensaje = (
            f"Se ha creado la orden de compra #{oc.numero_orden} "
            f"para el proveedor {oc.proveedor.nombre}. "
            f"Total: ${oc.total_orden:.2f}"
        )
        
        datos_contexto = {
            'oc_id': oc.id,
            'numero_orden': oc.numero_orden,
            'proveedor_id': oc.proveedor.id,
            'proveedor_nombre': oc.proveedor.nombre,
            'total_orden': str(oc.total_orden),
            'estado': oc.estado,
            'accion_sugerida': 'seguimiento_entrega'
        }
        
        return NotificationService.crear_notificacion(
            tipo='oc_creada',
            titulo=titulo,
            mensaje=mensaje,
            remitente=usuario_remitente,
            destinatario_grupo='deposito',
            prioridad='media',
            datos_contexto=datos_contexto
        )
    
    @staticmethod
    def notificar_oc_enviada(oc, usuario_remitente) -> 'NotificacionSistema':
        """Notifica al depósito que una OC fue enviada al proveedor"""
        titulo = f"OC #{oc.numero_orden} enviada"
        mensaje = (
            f"La orden de compra #{oc.numero_orden} ha sido enviada "
            f"al proveedor {oc.proveedor.nombre}. "
            f"Fecha estimada de entrega: {oc.fecha_entrega_estimada or 'Por confirmar'}"
        )
        
        datos_contexto = {
            'oc_id': oc.id,
            'numero_orden': oc.numero_orden,
            'proveedor_nombre': oc.proveedor.nombre,
            'fecha_envio': timezone.now().isoformat(),
            'fecha_entrega_estimada': oc.fecha_entrega_estimada.isoformat() if oc.fecha_entrega_estimada else None,
            'accion_sugerida': 'preparar_recepcion'
        }
        
        return NotificationService.crear_notificacion(
            tipo='oc_enviada',
            titulo=titulo,
            mensaje=mensaje,
            remitente=usuario_remitente,
            destinatario_grupo='deposito',
            prioridad='media',
            datos_contexto=datos_contexto
        )
    
    @staticmethod
    def notificar_pedido_recibido(oc, usuario_remitente, items_recibidos: List[Dict]) -> 'NotificacionSistema':
        """Notifica a compras que se recibió un pedido en depósito"""
        titulo = f"Pedido OC #{oc.numero_orden} recibido"
        mensaje = (
            f"Se ha recibido el pedido de la orden de compra #{oc.numero_orden} "
            f"del proveedor {oc.proveedor.nombre}. "
            f"Elementos recibidos: {len(items_recibidos)}"
        )
        
        datos_contexto = {
            'oc_id': oc.id,
            'numero_orden': oc.numero_orden,
            'proveedor_nombre': oc.proveedor.nombre,
            'items_recibidos': items_recibidos,
            'fecha_recepcion': timezone.now().isoformat(),
            'accion_sugerida': 'verificar_facturacion'
        }
        
        return NotificationService.crear_notificacion(
            tipo='pedido_recibido',
            titulo=titulo,
            mensaje=mensaje,
            remitente=usuario_remitente,
            destinatario_grupo='compras',
            prioridad='media',
            datos_contexto=datos_contexto
        )
    
    @staticmethod
    def notificar_solicitud_insumos_produccion(op, usuario_remitente, insumos_requeridos: List[Dict]) -> 'NotificacionSistema':
        """Notifica al depósito que producción solicita insumos"""
        titulo = f"Solicitud insumos OP #{op.numero_op}"
        mensaje = (
            f"La orden de producción #{op.numero_op} solicita insumos "
            f"para producir {op.cantidad_a_producir} unidades de {op.producto_a_producir.descripcion}. "
            f"Insumos requeridos: {len(insumos_requeridos)}"
        )
        
        datos_contexto = {
            'op_id': op.id,
            'numero_op': op.numero_op,
            'producto': op.producto_a_producir.descripcion,
            'cantidad_producir': op.cantidad_a_producir,
            'insumos_requeridos': insumos_requeridos,
            'fecha_solicitud': timezone.now().isoformat(),
            'accion_sugerida': 'preparar_insumos'
        }
        
        return NotificationService.crear_notificacion(
            tipo='solicitud_insumos',
            titulo=titulo,
            mensaje=mensaje,
            remitente=usuario_remitente,
            destinatario_grupo='deposito',
            prioridad='alta',
            datos_contexto=datos_contexto
        )
    
    @staticmethod
    def obtener_notificaciones_usuario(usuario: User, solo_no_leidas: bool = True) -> List['NotificacionSistema']:
        """Obtiene las notificaciones para un usuario según sus grupos"""
        from ..models import NotificacionSistema
        
        # Obtener grupos del usuario
        grupos_usuario = list(usuario.groups.values_list('name', flat=True))
        
        # Mapeo de grupos Django a grupos de notificación
        mapeo_grupos = {
            'administrador': 'administrador',
            'Depósito': 'deposito',
            'Compras': 'compras',
            'Ventas': 'ventas',
            'Producción': 'produccion',
            'Control de Calidad': 'control_calidad'
        }
        
        grupos_notificacion = []
        for grupo in grupos_usuario:
            if grupo in mapeo_grupos:
                grupos_notificacion.append(mapeo_grupos[grupo])
        
        # Si es administrador, puede ver todas las notificaciones
        if usuario.is_superuser or 'administrador' in grupos_notificacion:
            grupos_notificacion.append('todos')
        
        if not grupos_notificacion:
            return []
        
        # Filtrar notificaciones
        filtros = Q(destinatario_grupo__in=grupos_notificacion)
        
        if solo_no_leidas:
            filtros &= Q(leida=False)
        
        # Excluir notificaciones expiradas
        filtros &= Q(Q(fecha_expiracion__isnull=True) | Q(fecha_expiracion__gt=timezone.now()))
        
        return NotificacionSistema.objects.filter(filtros).order_by('-fecha_creacion')
    
    @staticmethod
    def marcar_notificaciones_como_leidas(usuario: User, notificacion_ids: List[int] = None):
        """Marca notificaciones como leídas"""
        notificaciones = NotificationService.obtener_notificaciones_usuario(usuario, solo_no_leidas=True)
        
        if notificacion_ids:
            notificaciones = notificaciones.filter(id__in=notificacion_ids)
        
        for notificacion in notificaciones:
            notificacion.marcar_como_leida(usuario)
        
        logger.info(f"Usuario {usuario.username} marcó {notificaciones.count()} notificaciones como leídas")
    
    @staticmethod
    def limpiar_notificaciones_expiradas():
        """Limpia notificaciones expiradas (para ejecutar periódicamente)"""
        from ..models import NotificacionSistema
        
        notificaciones_expiradas = NotificacionSistema.objects.filter(
            fecha_expiracion__lt=timezone.now()
        )
        
        count = notificaciones_expiradas.count()
        notificaciones_expiradas.delete()
        
        logger.info(f"Eliminadas {count} notificaciones expiradas")
        return count
