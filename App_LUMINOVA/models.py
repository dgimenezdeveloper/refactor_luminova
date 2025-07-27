# TP_LUMINOVA-main/App_LUMINOVA/models.py

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models


from django.utils import timezone  # Importar timezone



# --- CATEGORÍAS Y ENTIDADES BASE ---








# --- MODELOS DE GESTIÓN ---
class Cliente(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.nombre


class OrdenVenta(models.Model):
    ESTADO_CHOICES = [
        ("PENDIENTE", "Pendiente Confirmación"),
        ("CONFIRMADA", "Confirmada (Esperando Producción)"),
        ("INSUMOS_SOLICITADOS", "Insumos Solicitados"),
        ("PRODUCCION_INICIADA", "Producción Iniciada"),
        ("PRODUCCION_CON_PROBLEMAS", "Producción con Problemas"),
        ("LISTA_ENTREGA", "Lista para Entrega"),
        ("COMPLETADA", "Completada/Entregada"),
        ("CANCELADA", "Cancelada"),
    ]
    numero_ov = models.CharField(
        max_length=20, unique=True, verbose_name="N° Orden de Venta"
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="ordenes_venta"
    )
    fecha_creacion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(
        max_length=50, choices=ESTADO_CHOICES, default="PENDIENTE"
    )
    total_ov = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, verbose_name="Total OV"
    )
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"OV: {self.numero_ov} - {self.cliente.nombre}"

    def actualizar_total(self):
        nuevo_total = sum(item.subtotal for item in self.items_ov.all())
        if self.total_ov != nuevo_total:
            self.total_ov = nuevo_total
            self.save(update_fields=["total_ov"])


class ItemOrdenVenta(models.Model):
    orden_venta = models.ForeignKey(
        OrdenVenta, on_delete=models.CASCADE, related_name="items_ov"
    )
    producto_terminado = models.ForeignKey('productos.ProductoTerminado', on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario_venta = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Precio Unit. en Venta"
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario_venta
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto_terminado.descripcion} en OV {self.orden_venta.numero_ov}"




class Factura(models.Model):
    numero_factura = models.CharField(
        max_length=50, unique=True
    )  # Aumentado max_length
    orden_venta = models.OneToOneField(
        OrdenVenta, on_delete=models.PROTECT, related_name="factura_asociada"
    )
    fecha_emision = models.DateTimeField(
        default=timezone.now
    )  # Cambiado a DateTimeField
    total_facturado = models.DecimalField(
        max_digits=12, decimal_places=2
    )  # Aumentado max_digits

    def __str__(self):
        return f"Factura {self.numero_factura} para OV {self.orden_venta.numero_ov}"


class RolDescripcion(models.Model):
    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="descripcion_extendida"
    )
    descripcion = models.TextField("Descripción del rol", blank=True)

    def __str__(self):
        return f"Descripción para rol: {self.group.name}"


class AuditoriaAcceso(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=255)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    def __str__(self):
        user_display = (
            self.usuario.username if self.usuario else "Usuario Desconocido/Eliminado"
        )
        return f"{user_display} - {self.accion} @ {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"


class HistorialOV(models.Model):
    orden_venta = models.ForeignKey(
        OrdenVenta, on_delete=models.CASCADE, related_name="historial"
    )
    fecha_evento = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=255)
    tipo_evento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Ej: 'Estado Cambiado', 'Producción Iniciada', 'Facturado'",
    )
    realizado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-fecha_evento"]  # Ordenar del más reciente al más antiguo
        verbose_name = "Historial de Orden de Venta"
        verbose_name_plural = "Historiales de Órdenes de Venta"

    def __str__(self):
        return f"{self.fecha_evento.strftime('%d/%m/%Y %H:%M')} - {self.orden_venta.numero_ov}: {self.descripcion}"


class PasswordChangeRequired(models.Model):
    """
    Un modelo simple para marcar a los usuarios que deben cambiar
    su contraseña por defecto en el primer inicio de sesión.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="password_change_required"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"El usuario {self.user.username} debe cambiar su contraseña."
