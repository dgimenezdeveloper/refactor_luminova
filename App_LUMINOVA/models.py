from productos.models import ProductoTerminado
# TP_LUMINOVA-main/App_LUMINOVA/models.py

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models


from django.utils import timezone  # Importar timezone
from insumos.models import Insumo, Proveedor



# --- CATEGORÍAS Y ENTIDADES BASE ---






class ComponenteProducto(models.Model):
    producto_terminado = models.ForeignKey(
        ProductoTerminado,
        on_delete=models.CASCADE,
        related_name="componentes_requeridos",
    )
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad_necesaria = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("producto_terminado", "insumo")
        verbose_name = "Componente de Producto (BOM)"
        verbose_name_plural = "Componentes de Productos (BOM)"

    def __str__(self):
        return f"{self.cantidad_necesaria} x {self.insumo.descripcion} para {self.producto_terminado.descripcion}"


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
    producto_terminado = models.ForeignKey(ProductoTerminado, on_delete=models.PROTECT)
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


class EstadoOrden(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class SectorAsignado(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class OrdenProduccion(models.Model):
    numero_op = models.CharField(
        max_length=20, unique=True, verbose_name="N° Orden de Producción"
    )
    orden_venta_origen = models.ForeignKey(
        OrdenVenta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_generadas",
    )

    producto_a_producir = models.ForeignKey(
        ProductoTerminado, on_delete=models.PROTECT, related_name="ordenes_produccion"
    )
    cantidad_a_producir = models.PositiveIntegerField()
    estado_op = models.ForeignKey(
        EstadoOrden,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_estado",
    )

    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_inicio_planificada = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateTimeField(null=True, blank=True)
    fecha_fin_planificada = models.DateField(null=True, blank=True)
    sector_asignado_op = models.ForeignKey(
        SectorAsignado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_sector",
    )
    notas = models.TextField(null=True, blank=True, verbose_name="Notas")

    def get_estado_op_display(self):
        if self.estado_op:
            return self.estado_op.nombre
        return "Sin Estado Asignado"

    def __str__(self):
        return f"OP: {self.numero_op} - {self.cantidad_a_producir} x {self.producto_a_producir.descripcion}"


class Reportes(models.Model):
    orden_produccion_asociada = models.ForeignKey(
        OrdenProduccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_incidencia",
    )
    n_reporte = models.CharField(max_length=20, unique=True)
    fecha = models.DateTimeField(default=timezone.now)
    tipo_problema = models.CharField(max_length=100)
    informe_reporte = models.TextField(blank=True, null=True)
    resuelto = models.BooleanField(default=False, verbose_name="¿Problema Resuelto?")
    fecha_resolucion = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de Resolución"
    )

    # ESTOS SON LOS CAMPOS EN CUESTIÓN:
    reportado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_creados",
    )
    sector_reporta = models.ForeignKey(
        SectorAsignado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_originados_aqui",
    )

    def __str__(self):
        op_num = (
            self.orden_produccion_asociada.numero_op
            if self.orden_produccion_asociada
            else "N/A"
        )
        return f"Reporte {self.n_reporte} (OP: {op_num})"


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


class Orden(models.Model):
    TIPO_ORDEN_CHOICES = [
        ("compra", "Orden de Compra"),
    ]
    ESTADO_ORDEN_COMPRA_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("APROBADA", "Aprobada"),
        ("ENVIADA_PROVEEDOR", "Enviada al Proveedor"),
        ("CONFIRMADA_PROVEEDOR", "Confirmada por Proveedor"),
        ("EN_TRANSITO", "En Tránsito"),
        ("RECIBIDA_PARCIAL", "Recibida Parcialmente"),
        ("RECIBIDA_TOTAL", "Recibida Totalmente"),
        ("COMPLETADA", "Completada"),
        ("CANCELADA", "Cancelada"),
    ]

    numero_orden = models.CharField(
        max_length=20, unique=True, verbose_name="N° Orden de Compra"
    )
    tipo = models.CharField(max_length=20, choices=TIPO_ORDEN_CHOICES, default="compra")
    fecha_creacion = models.DateTimeField(default=timezone.now)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="ordenes_de_compra_a_proveedor",
    )
    estado = models.CharField(
        max_length=30, choices=ESTADO_ORDEN_COMPRA_CHOICES, default="BORRADOR"
    )
    insumo_principal = models.ForeignKey(
        Insumo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Insumo Principal",
    )
    cantidad_principal = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Cantidad Insumo Principal"
    )
    precio_unitario_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio Unit. Compra (de la oferta)",
    )

    total_orden_compra = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )

    fecha_estimada_entrega = models.DateField(null=True, blank=True)
    numero_tracking = models.CharField(max_length=50, null=True, blank=True)
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"OC: {self.numero_orden} - Proveedor: {self.proveedor.nombre}"

    def get_estado_display_custom(self):
        return dict(self.ESTADO_ORDEN_COMPRA_CHOICES).get(self.estado, self.estado)

    def save(self, *args, **kwargs):
        if (
            self.insumo_principal
            and self.cantidad_principal
            and self.precio_unitario_compra is not None
        ):
            self.total_orden_compra = (
                self.cantidad_principal * self.precio_unitario_compra
            )
        super().save(*args, **kwargs)




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
