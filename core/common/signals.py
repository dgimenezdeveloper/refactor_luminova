from django.db.models.signals import post_save
from django.dispatch import receiver
from App_LUMINOVA.models import HistorialOV, OrdenVenta
from productos.models import OrdenProduccion

@receiver(post_save, sender=OrdenVenta)
def registrar_creacion_ov(sender, instance, created, **kwargs):
    if created:
        HistorialOV.objects.create(
            orden_venta=instance,
            descripcion=f"Orden de Venta creada en estado '{instance.get_estado_display()}'.",
        )

@receiver(post_save, sender=OrdenProduccion)
def registrar_creacion_op(sender, instance, created, **kwargs):
    if created:
        HistorialOV.objects.create(
            orden_venta=instance.orden_venta_asociada,
            descripcion=f"Orden de Producción creada en estado '{instance.get_estado_display()}'.",
        )
