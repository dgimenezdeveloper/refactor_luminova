from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class LoteProductoTerminado(models.Model):
    producto = models.ForeignKey(
        'ProductoTerminado', on_delete=models.PROTECT, related_name="lotes"
    )
    op_asociada = models.ForeignKey(
        'productos.OrdenProduccion', on_delete=models.PROTECT, related_name="lotes_pt"
    )
    cantidad = models.PositiveIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enviado = models.BooleanField(default=False)

    def __str__(self):
        return f"Lote de {self.producto.descripcion} - OP {self.op_asociada.numero_op} ({self.cantidad})"

class CategoriaProductoTerminado(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre Categoría PT")
    imagen = models.ImageField(upload_to="categorias_productos/", null=True, blank=True)

    class Meta:
        verbose_name = "Categoría de Producto Terminado"
        verbose_name_plural = "Categorías de Productos Terminados"

    def __str__(self):
        return self.nombre

class ProductoTerminado(models.Model):
    descripcion = models.CharField(max_length=255)
    categoria = models.ForeignKey(CategoriaProductoTerminado, on_delete=models.PROTECT, related_name="productos_terminados")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    potencia = models.IntegerField(blank=True, null=True)
    acabado = models.CharField(max_length=50, blank=True, null=True)
    color_luz = models.CharField(max_length=50, blank=True, null=True)
    material = models.CharField(max_length=50, blank=True, null=True)
    imagen = models.ImageField(null=True, blank=True, upload_to="productos_terminados/")

    def __str__(self):
        return f"{self.descripcion} (Modelo: {self.modelo or 'N/A'})"

    def get_stock_total(self):
        return sum(stock.cantidad for stock in self.stocks.all())

    def get_stock_en_deposito(self, deposito):
        stock = self.stocks.filter(deposito=deposito).first()
        return stock.cantidad if stock else 0

    def agregar_stock(self, cantidad, deposito):
        stock, created = self.stocks.get_or_create(deposito=deposito, defaults={"cantidad": 0})
        stock.cantidad += cantidad
        stock.save()
        return stock.cantidad

    def quitar_stock(self, cantidad, deposito):
        stock = self.stocks.filter(deposito=deposito).first()
        if stock and stock.cantidad >= cantidad:
            stock.cantidad -= cantidad
            stock.save()
            return True
        return False

class ComponenteProducto(models.Model):
    producto_terminado = models.ForeignKey(
        'productos.ProductoTerminado',
        on_delete=models.CASCADE,
        related_name="componentes_requeridos",
    )
    insumo = models.ForeignKey('insumos.Insumo', on_delete=models.PROTECT)
    cantidad_necesaria = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("producto_terminado", "insumo")
        verbose_name = "Componente de Producto (BOM)"
        verbose_name_plural = "Componentes de Productos (BOM)"

    def __str__(self):
        return f"{self.cantidad_necesaria} x {self.insumo.descripcion} para {self.producto_terminado.descripcion}"

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
        'App_LUMINOVA.OrdenVenta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_generadas",
    )
    producto_a_producir = models.ForeignKey(
        'productos.ProductoTerminado', on_delete=models.PROTECT, related_name="ordenes_produccion"
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
