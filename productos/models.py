
from django.db import models

class LoteProductoTerminado(models.Model):
    producto = models.ForeignKey(
        'ProductoTerminado', on_delete=models.PROTECT, related_name="lotes"
    )
    op_asociada = models.ForeignKey(
        'App_LUMINOVA.OrdenProduccion', on_delete=models.PROTECT, related_name="lotes_pt"
    )
    cantidad = models.PositiveIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enviado = models.BooleanField(default=False)

    def __str__(self):
        return f"Lote de {self.producto.descripcion} - OP {self.op_asociada.numero_op} ({self.cantidad})"

from django.db import models

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
