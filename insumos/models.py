from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class CategoriaInsumo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Proveedor(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Fabricante(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Insumo(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(CategoriaInsumo, on_delete=models.CASCADE)
    fabricante = models.ForeignKey(Fabricante, on_delete=models.SET_NULL, null=True, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=50)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    imagen = models.ImageField(upload_to="insumos/", null=True, blank=True)

    def __str__(self):
        return self.nombre

class OfertaProveedor(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_oferta = models.DateField()

    def __str__(self):
        return f"{self.proveedor} - {self.insumo} (${self.precio})"

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
        'insumos.Proveedor',
        on_delete=models.PROTECT,
        related_name="ordenes_de_compra_a_proveedor",
    )
    estado = models.CharField(
        max_length=30, choices=ESTADO_ORDEN_COMPRA_CHOICES, default="BORRADOR"
    )
    insumo_principal = models.ForeignKey(
        'insumos.Insumo',
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
