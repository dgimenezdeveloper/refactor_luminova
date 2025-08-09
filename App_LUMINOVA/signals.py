from .models import Insumo, ProductoTerminado, StockInsumo, StockProductoTerminado, OrdenProduccion
# Sincronizar StockInsumo al crear o actualizar un Insumo
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Insumo)
def sync_stock_insumo(sender, instance, **kwargs):
    if instance.deposito:
        StockInsumo.objects.update_or_create(
            insumo=instance,
            deposito=instance.deposito,
            defaults={"cantidad": instance.stock},
        )

# Sincronizar StockProductoTerminado al crear o actualizar un ProductoTerminado
# TEMPORALMENTE DESHABILITADO PARA DEBUGGING
# @receiver(post_save, sender=ProductoTerminado)
def sync_stock_producto_terminado_disabled(sender, instance, **kwargs):
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Signal sync_stock_producto_terminado ejecutándose para producto: {instance}")
    
    if instance.deposito:
        try:
            logger.debug(f"Sincronizando stock para producto {instance.id} en depósito {instance.deposito.id}")
            StockProductoTerminado.objects.update_or_create(
                producto=instance,
                deposito=instance.deposito,
                defaults={"cantidad": instance.stock},
            )
            logger.debug(f"Stock sincronizado exitosamente")
        except Exception as e:
            logger.error(f"Error en sync_stock_producto_terminado: {e}")
            logger.error(f"Tipo de excepción: {type(e).__name__}")
            if hasattr(e, 'args'):
                logger.error(f"Argumentos de la excepción: {e.args}")
            raise
# TP_LUMINOVA-main/App_LUMINOVA/signals.py

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AuditoriaAcceso, HistorialOV, OrdenProduccion, OrdenVenta, Reportes


def get_client_ip(request):
    """Obtiene la IP real del cliente, incluso si está detrás de un proxy."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


# @receiver(user_logged_in)
# def registrar_acceso(sender, user, request, **kwargs):
#     AuditoriaAcceso.objects.create(
#         usuario=user,
#         accion="Inicio de sesión"
#     )


# Signal to log the creation of an OV.
@receiver(post_save, sender=OrdenVenta)
def registrar_creacion_ov(sender, instance, created, **kwargs):
    if created:
        HistorialOV.objects.create(
            orden_venta=instance,
            descripcion=f"Orden de Venta creada en estado '{instance.get_estado_display()}'.",
        )


# Signal to log the creation of an OP and link it to the OV history.
@receiver(post_save, sender=OrdenProduccion)
def registrar_creacion_op(sender, instance, created, **kwargs):
    if created and instance.orden_venta_origen:
        HistorialOV.objects.create(
            orden_venta=instance.orden_venta_origen,
            descripcion=f"Se generó la Orden de Producción {instance.numero_op} para el producto '{instance.producto_a_producir.descripcion}'.",
        )


# NEW: Signal to log when a report is created for an OP.
@receiver(post_save, sender=Reportes)
def registrar_creacion_reporte_en_historial_ov(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo reporte para una OP, registra un evento en el historial de la OV asociada.
    """
    if (
        created
        and instance.orden_produccion_asociada
        and instance.orden_produccion_asociada.orden_venta_origen
    ):
        orden_venta = instance.orden_produccion_asociada.orden_venta_origen

        descripcion = f"Se creó el reporte N° {instance.n_reporte} por '{instance.tipo_problema}' en la OP {instance.orden_produccion_asociada.numero_op}."
        if instance.informe_reporte:
            descripcion += f' Detalle: "{instance.informe_reporte[:60]}..."'

        HistorialOV.objects.create(
            orden_venta=orden_venta,
            descripcion=descripcion,
            tipo_evento="Reporte de Incidencia",
            realizado_por=instance.reportado_por,
        )


# --- SEÑALES PARA SINCRONIZACIÓN DE ESTADOS OV-OP ---
@receiver(post_save, sender=OrdenProduccion)
def actualizar_estado_ov_por_cambio_op(sender, instance, **kwargs):
    """
    Actualiza automáticamente el estado de la OV cuando cambia el estado de una OP asociada.
    """
    if instance.orden_venta_origen:
        try:
            # Usar transaction para evitar problemas de concurrencia
            with transaction.atomic():
                instance.orden_venta_origen.actualizar_estado_por_ops()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error actualizando estado OV {instance.orden_venta_origen.numero_ov} "
                        f"por cambio en OP {instance.numero_op}: {e}")


def get_client_ip(request):
    """
    Obtiene la IP del cliente desde el request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
