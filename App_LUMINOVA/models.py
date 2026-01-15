"""
MÓDULO DE COMPATIBILIDAD - App_LUMINOVA/models.py

Este archivo ahora re-exporta todos los modelos desde las nuevas apps modulares
para mantener compatibilidad con el código existente (vistas, formularios, etc.)
que importa desde App_LUMINOVA.models.

NUEVA ESTRUCTURA:
- apps.core: Empresa, Domain, Deposito, UsuarioDeposito, EmpresaScopedModel, etc.
- apps.inventory: ProductoTerminado, Insumo, Stock*, Categorías, etc.
- apps.sales: Cliente, OrdenVenta, ItemOrdenVenta, Factura, HistorialOV
- apps.production: OrdenProduccion, EstadoOrden, SectorAsignado, Reportes, etc.
- apps.purchasing: Proveedor, Orden (OC), OfertaProveedor
- apps.notifications: NotificacionSistema

MIGRACIÓN GRADUAL:
Los imports existentes como `from App_LUMINOVA.models import X` seguirán funcionando.
Se recomienda actualizar gradualmente a `from apps.modulo.models import X`.

NOTA: Este archivo mantiene SOLO los modelos que NO han sido movidos a las nuevas apps
o que deben mantenerse aquí por razones de django-tenants.
"""

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils import timezone

# Django-tenants para multi-tenancy
from django_tenants.models import TenantMixin, DomainMixin

from .threadlocals import get_current_empresa


# =============================================================================
# MODELOS PROPIOS DE App_LUMINOVA (TENANT MODEL - DEBE ESTAR AQUÍ)
# =============================================================================

class Empresa(TenantMixin):
    """
    Modelo de Tenant para multi-tenancy con django-tenants.
    NOTA: Este modelo DEBE permanecer en App_LUMINOVA porque está definido como
    TENANT_MODEL en settings.py
    """
    nombre = models.CharField(max_length=150, unique=True)
    razon_social = models.CharField(max_length=255, blank=True)
    cuit = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    
    auto_create_schema = True
    auto_drop_schema = True

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.nombre


class Domain(DomainMixin):
    """
    Modelo de Domain para django-tenants.
    NOTA: Este modelo DEBE permanecer en App_LUMINOVA porque está definido como
    TENANT_DOMAIN_MODEL en settings.py
    """
    pass


# =============================================================================
# MODELO BASE ABSTRACTO - DEBE ESTAR AQUÍ PARA HERENCIA
# =============================================================================

class EmpresaScopedModel(models.Model):
    """Base abstracta para modelos aislados por empresa."""

    empresa = models.ForeignKey(
        'App_LUMINOVA.Empresa',
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s",
        null=True,
        blank=True,
    )

    EMPRESA_FALLBACK_FIELDS = ()

    class Meta:
        abstract = True

    def _infer_empresa_from_relations(self):
        for field_name in getattr(self, "EMPRESA_FALLBACK_FIELDS", ()):
            related_obj = getattr(self, field_name, None)
            if not related_obj:
                continue
            if hasattr(related_obj, "empresa") and related_obj.empresa_id:
                return related_obj.empresa
        return None

    def ensure_empresa(self):
        if self.empresa_id:
            return
        inferred = self._infer_empresa_from_relations()
        if inferred:
            self.empresa = inferred
            return
        current = get_current_empresa()
        if current:
            self.empresa = current

    def save(self, *args, **kwargs):
        self.ensure_empresa()
        super().save(*args, **kwargs)


# =============================================================================
# MODELOS DE USUARIOS Y ROLES
# =============================================================================

class RolEmpresa(models.Model):
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='roles_empresa')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='roles_empresa')
    nombre = models.CharField(max_length=150, blank=False, default="", help_text="Nombre lógico del rol visible en la UI")
    descripcion = models.TextField("Descripción del rol", blank=True)

    class Meta:
        unique_together = ("empresa", "nombre")
        verbose_name = "Rol de Empresa"
        verbose_name_plural = "Roles de Empresa"

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"


class PerfilUsuario(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name="usuarios")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.empresa.nombre})"


class RolDescripcion(models.Model):
    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="descripcion_extendida"
    )
    descripcion = models.TextField("Descripción del rol", blank=True)

    def __str__(self):
        return f"Descripción para rol: {self.group.name}"


class PasswordChangeRequired(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="password_change_required"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"El usuario {self.user.username} debe cambiar su contraseña."


# =============================================================================
# DEPÓSITO Y PERMISOS
# =============================================================================

class Deposito(models.Model):
    nombre = models.CharField(max_length=100)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="depositos")
    ubicacion = models.CharField(max_length=255, blank=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        unique_together = ("nombre", "empresa")

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"


class UsuarioDeposito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depositos_asignados')
    deposito = models.ForeignKey(Deposito, on_delete=models.CASCADE, related_name='usuarios_asignados')
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='usuarios_depositos',
        null=True,
        blank=True,
    )
    puede_transferir = models.BooleanField(default=True)
    puede_entradas = models.BooleanField(default=True)
    puede_salidas = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    EMPRESA_FALLBACK_FIELDS = ("deposito",)

    class Meta:
        unique_together = ('usuario', 'deposito')
        verbose_name = "Asignación Usuario-Depósito"
        verbose_name_plural = "Asignaciones Usuario-Depósito"

    def save(self, *args, **kwargs):
        if not self.empresa_id and self.deposito_id:
            self.empresa = self.deposito.empresa
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.deposito.nombre}"


# =============================================================================
# AUDITORÍA
# =============================================================================

class AuditoriaAcceso(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='auditorias_acceso')
    empresa = models.ForeignKey('Empresa', on_delete=models.SET_NULL, null=True, blank=True, related_name='auditorias')
    accion = models.CharField(max_length=255)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Auditoría de Acceso"
        verbose_name_plural = "Auditorías de Acceso"
        ordering = ['-fecha_hora']

    def __str__(self):
        user_display = self.usuario.username if self.usuario else "Usuario Desconocido"
        return f"{user_display} - {self.accion} @ {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"


# =============================================================================
# INVENTARIO - CATEGORÍAS Y PRODUCTOS
# =============================================================================

class CategoriaProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito",)
    nombre = models.CharField(max_length=100, verbose_name="Nombre Categoría PT")
    imagen = models.ImageField(upload_to="categorias_productos/", null=True, blank=True)
    deposito = models.ForeignKey(
        "Deposito", on_delete=models.CASCADE, related_name="categorias_producto_terminado",
        null=True, blank=True,
    )

    class Meta:
        verbose_name = "Categoría de Producto Terminado"
        verbose_name_plural = "Categorías de Productos Terminados"
        unique_together = ("nombre", "deposito")

    def __str__(self):
        return self.nombre


class CategoriaInsumo(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito",)
    nombre = models.CharField(max_length=100, verbose_name="Nombre Categoría Insumo")
    imagen = models.ImageField(upload_to="categorias_insumos/", null=True, blank=True)
    deposito = models.ForeignKey(
        "Deposito", on_delete=models.CASCADE, related_name="categorias_insumo",
        null=True, blank=True,
    )

    class Meta:
        verbose_name = "Categoría de Insumo"
        verbose_name_plural = "Categorías de Insumos"
        unique_together = ("nombre", "deposito")

    def __str__(self):
        return self.nombre


class Fabricante(EmpresaScopedModel):
    nombre = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    email = models.EmailField(blank=True, null=True)
    
    class Meta:
        unique_together = ('nombre', 'empresa')
        verbose_name = "Fabricante"
        verbose_name_plural = "Fabricantes"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito", "categoria")
    descripcion = models.CharField(max_length=255)
    categoria = models.ForeignKey(
        CategoriaProductoTerminado, on_delete=models.PROTECT, related_name="productos_terminados",
    )
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock_minimo = models.IntegerField(default=0, verbose_name="Stock Mínimo")
    stock_objetivo = models.IntegerField(default=0, verbose_name="Stock Objetivo")
    produccion_habilitada = models.BooleanField(default=True, verbose_name="Habilitado para Producción")
    modelo = models.CharField(max_length=50, blank=True, null=True)
    potencia = models.IntegerField(blank=True, null=True)
    acabado = models.CharField(max_length=50, blank=True, null=True)
    color_luz = models.CharField(max_length=50, blank=True, null=True)
    material = models.CharField(max_length=50, blank=True, null=True)
    imagen = models.ImageField(null=True, blank=True, upload_to="productos_terminados/")
    deposito = models.ForeignKey(
        "Deposito", on_delete=models.PROTECT, related_name="productos_terminados",
        null=True, blank=True,
    )

    class Meta:
        verbose_name = "Producto Terminado"
        verbose_name_plural = "Productos Terminados"
        ordering = ['descripcion']
        indexes = [
            models.Index(fields=['empresa', 'deposito']),
            models.Index(fields=['empresa', 'categoria']),
            models.Index(fields=['deposito', 'categoria']),
        ]

    def __str__(self):
        return f"{self.descripcion} (Modelo: {self.modelo or 'N/A'})"
    
    @property
    def stock(self) -> int:
        from django.db.models import Sum
        result = StockProductoTerminado.objects.filter(producto=self).aggregate(total=Sum('cantidad'))['total']
        return result if result is not None else 0
    
    def get_stock_by_deposito(self, deposito) -> int:
        try:
            return StockProductoTerminado.objects.get(producto=self, deposito=deposito).cantidad
        except StockProductoTerminado.DoesNotExist:
            return 0
    
    @property
    def necesita_reposicion(self):
        return self.stock <= self.stock_minimo
    
    @property
    def necesita_reposicion_stock(self):
        return self.stock <= self.stock_minimo and self.stock_minimo > 0
    
    @property
    def cantidad_reposicion_sugerida(self):
        if self.necesita_reposicion:
            return max(0, self.stock_objetivo - self.stock)
        return 0
    
    @property
    def porcentaje_stock(self):
        if self.stock_objetivo > 0:
            return (self.stock / self.stock_objetivo) * 100
        return 0
    
    def puede_producir_para_stock(self):
        return self.produccion_habilitada and self.stock_objetivo > 0


class Insumo(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito", "categoria")
    notificado_a_compras = models.BooleanField(default=False)
    descripcion = models.CharField(max_length=255)
    categoria = models.ForeignKey(CategoriaInsumo, on_delete=models.PROTECT, related_name="insumos")
    fabricante = models.ForeignKey(
        Fabricante, on_delete=models.SET_NULL, null=True, blank=True, related_name="insumos_fabricados",
    )
    imagen = models.ImageField(null=True, blank=True, upload_to="insumos/")
    cantidad_en_pedido = models.PositiveIntegerField(default=0, verbose_name="Cantidad en Pedido", blank=True, null=True)
    deposito = models.ForeignKey(
        "Deposito", on_delete=models.PROTECT, related_name="insumos", null=True, blank=True,
    )

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['descripcion']
        indexes = [
            models.Index(fields=['empresa', 'deposito']),
            models.Index(fields=['empresa', 'categoria']),
            models.Index(fields=['deposito', 'categoria']),
        ]

    def __str__(self):
        return self.descripcion
    
    @property
    def stock(self) -> int:
        from django.db.models import Sum
        result = StockInsumo.objects.filter(insumo=self).aggregate(total=Sum('cantidad'))['total']
        return result if result is not None else 0
    
    def get_stock_by_deposito(self, deposito) -> int:
        try:
            return StockInsumo.objects.get(insumo=self, deposito=deposito).cantidad
        except StockInsumo.DoesNotExist:
            return 0


class ComponenteProducto(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("producto_terminado", "insumo")
    producto_terminado = models.ForeignKey(
        ProductoTerminado, on_delete=models.CASCADE, related_name="componentes_requeridos",
    )
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad_necesaria = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("producto_terminado", "insumo")
        verbose_name = "Componente de Producto (BOM)"
        verbose_name_plural = "Componentes de Productos (BOM)"

    def __str__(self):
        return f"{self.cantidad_necesaria} x {self.insumo.descripcion} para {self.producto_terminado.descripcion}"


# =============================================================================
# STOCK
# =============================================================================

class StockInsumo(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("insumo", "deposito")
    insumo = models.ForeignKey('Insumo', on_delete=models.CASCADE)
    deposito = models.ForeignKey('Deposito', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('insumo', 'deposito')
        verbose_name = "Stock de Insumo"
        verbose_name_plural = "Stocks de Insumos"


class StockProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("producto", "deposito")
    producto = models.ForeignKey('ProductoTerminado', on_delete=models.CASCADE)
    deposito = models.ForeignKey('Deposito', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'deposito')
        verbose_name = "Stock de Producto Terminado"
        verbose_name_plural = "Stocks de Productos Terminados"


class MovimientoStock(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito_origen", "deposito_destino", "insumo", "producto")
    insumo = models.ForeignKey('Insumo', on_delete=models.CASCADE, null=True, blank=True)
    producto = models.ForeignKey('ProductoTerminado', on_delete=models.CASCADE, null=True, blank=True)
    deposito_origen = models.ForeignKey('Deposito', on_delete=models.CASCADE, related_name='movimientos_salida', null=True, blank=True)
    deposito_destino = models.ForeignKey('Deposito', on_delete=models.CASCADE, related_name='movimientos_entrada', null=True, blank=True)
    cantidad = models.IntegerField()
    tipo = models.CharField(max_length=20, choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('transferencia', 'Transferencia')])
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='movimientos_stock')
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha']


# =============================================================================
# COMPRAS - PROVEEDORES Y OFERTAS
# =============================================================================

class Proveedor(EmpresaScopedModel):
    nombre = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    email = models.EmailField(blank=True, null=True)
    
    class Meta:
        unique_together = ('nombre', 'empresa')
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class OfertaProveedor(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("insumo", "proveedor")
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name="ofertas_de_proveedores")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name="provee_insumos")
    precio_unitario_compra = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Compra Unitario")
    tiempo_entrega_estimado_dias = models.IntegerField(default=0, verbose_name="Tiempo de Entrega Estimado (días)")
    fecha_actualizacion_precio = models.DateTimeField(default=timezone.now, verbose_name="Última Actualización del Precio")

    class Meta:
        unique_together = ("insumo", "proveedor")
        verbose_name = "Oferta de Proveedor por Insumo"
        verbose_name_plural = "Ofertas de Proveedores por Insumos"
        ordering = ["insumo__descripcion", "proveedor__nombre"]

    def __str__(self):
        return f"{self.insumo.descripcion} - {self.proveedor.nombre} (${self.precio_unitario_compra})"


# =============================================================================
# VENTAS - CLIENTES Y ÓRDENES
# =============================================================================

class Cliente(EmpresaScopedModel):
    nombre = models.CharField(max_length=150)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    class Meta:
        unique_together = (('nombre', 'empresa'), ('email', 'empresa'),)
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class OrdenVenta(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("cliente",)
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
    numero_ov = models.CharField(max_length=20, unique=True, verbose_name="N° Orden de Venta")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordenes_venta")
    fecha_creacion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default="PENDIENTE")
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Orden de Venta"
        verbose_name_plural = "Órdenes de Venta"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['empresa', 'fecha_creacion']),
            models.Index(fields=['estado', 'fecha_creacion']),
        ]

    def __str__(self):
        return f"OV: {self.numero_ov} - {self.cliente.nombre}"

    @property
    def total_ov(self):
        from decimal import Decimal
        from django.db.models import Sum
        total = self.items_ov.aggregate(total=Sum('subtotal'))['total']
        return total or Decimal('0.00')

    def actualizar_estado_por_ops(self):
        from collections import Counter
        MAPEO_ESTADOS_OP_A_OV = {
            "Completada": "COMPLETADA",
            "En Proceso": "PRODUCCION_INICIADA", 
            "Producción Iniciada": "PRODUCCION_INICIADA",
            "Insumos Recibidos": "INSUMOS_SOLICITADOS",
            "Insumos Solicitados": "INSUMOS_SOLICITADOS",
            "Planificada": "CONFIRMADA",
            "Pendiente": "PENDIENTE",
            "Cancelada": "CANCELADA",
        }
        ESTADOS_PRIORIDAD = {
            "COMPLETADA": 6, "LISTA_ENTREGA": 5, "PRODUCCION_INICIADA": 4,
            "INSUMOS_SOLICITADOS": 3, "CONFIRMADA": 2, "PENDIENTE": 1, "CANCELADA": 0,
        }
        ops_asociadas = self.ops_generadas.all()
        if not ops_asociadas.exists():
            return
        estados_ops = []
        contador_estados = Counter()
        for op in ops_asociadas:
            if op.estado_op and op.estado_op.nombre:
                estado_op_nombre = op.estado_op.nombre
                estado_ov_mapeado = MAPEO_ESTADOS_OP_A_OV.get(estado_op_nombre)
                if estado_ov_mapeado:
                    estados_ops.append(estado_ov_mapeado)
                    contador_estados[estado_op_nombre] += 1
        if not estados_ops:
            return
        total_ops = len(estados_ops)
        ops_completadas = contador_estados.get("Completada", 0)
        ops_canceladas = contador_estados.get("Cancelada", 0)
        ops_activas = total_ops - ops_canceladas
        nuevo_estado = None
        if ops_canceladas == total_ops:
            nuevo_estado = "CANCELADA"
        elif ops_completadas == ops_activas and ops_activas > 0:
            nuevo_estado = "LISTA_ENTREGA"
        elif ops_completadas > 0 and ops_activas > ops_completadas:
            estados_no_completados = [e for e in estados_ops if e not in ["COMPLETADA", "CANCELADA"]]
            if estados_no_completados:
                estado_mas_avanzado_activo = max(estados_no_completados, key=lambda e: ESTADOS_PRIORIDAD.get(e, 0))
                if self.estado != "COMPLETADA":
                    nuevo_estado = estado_mas_avanzado_activo
            else:
                nuevo_estado = "PRODUCCION_INICIADA"
        else:
            nuevo_estado = max(estados_ops, key=lambda e: ESTADOS_PRIORIDAD.get(e, 0))
        if nuevo_estado and nuevo_estado != self.estado and ESTADOS_PRIORIDAD.get(nuevo_estado, 0) >= ESTADOS_PRIORIDAD.get(self.estado, 0):
            self.estado = nuevo_estado
            self.save(update_fields=["estado"])

    def get_resumen_estados_ops(self):
        from collections import Counter
        ops_asociadas = self.ops_generadas.all()
        if not ops_asociadas.exists():
            return "Sin OPs asociadas"
        contador = Counter()
        for op in ops_asociadas:
            if op.estado_op:
                contador[op.estado_op.nombre] += 1
        resumen_partes = [f"{cantidad} {estado}" for estado, cantidad in contador.most_common()]
        return " | ".join(resumen_partes)


class ItemOrdenVenta(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_venta", "producto_terminado")
    orden_venta = models.ForeignKey(OrdenVenta, on_delete=models.CASCADE, related_name="items_ov")
    producto_terminado = models.ForeignKey(ProductoTerminado, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario_venta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unit. en Venta")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        verbose_name = "Item de Orden de Venta"
        verbose_name_plural = "Items de Órdenes de Venta"

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario_venta
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto_terminado.descripcion} en OV {self.orden_venta.numero_ov}"


class Factura(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_venta",)
    numero_factura = models.CharField(max_length=50)
    orden_venta = models.OneToOneField(OrdenVenta, on_delete=models.PROTECT, related_name="factura_asociada")
    fecha_emision = models.DateTimeField(default=timezone.now)
    total_facturado = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        unique_together = ('numero_factura', 'empresa')
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"

    def __str__(self):
        return f"Factura {self.numero_factura} para OV {self.orden_venta.numero_ov}"


class HistorialOV(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_venta",)
    orden_venta = models.ForeignKey(OrdenVenta, on_delete=models.CASCADE, related_name="historial")
    fecha_evento = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=255)
    tipo_evento = models.CharField(max_length=50, blank=True, null=True)
    realizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='historial_ov_realizados')

    class Meta:
        ordering = ["-fecha_evento"]
        verbose_name = "Historial de Orden de Venta"
        verbose_name_plural = "Historiales de Órdenes de Venta"

    def __str__(self):
        return f"{self.fecha_evento.strftime('%d/%m/%Y %H:%M')} - {self.orden_venta.numero_ov}: {self.descripcion}"


# =============================================================================
# PRODUCCIÓN
# =============================================================================

class EstadoOrden(models.Model):
    nombre = models.CharField(max_length=50)
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='estados_orden', null=True, blank=True)

    class Meta:
        unique_together = ('nombre', 'empresa')
        verbose_name = "Estado de Orden"
        verbose_name_plural = "Estados de Orden"

    def __str__(self):
        return self.nombre


class SectorAsignado(models.Model):
    nombre = models.CharField(max_length=50)
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='sectores', null=True, blank=True)

    class Meta:
        unique_together = ('nombre', 'empresa')
        verbose_name = "Sector Asignado"
        verbose_name_plural = "Sectores Asignados"

    def __str__(self):
        return self.nombre


class OrdenProduccion(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("producto_a_producir", "orden_venta_origen")
    TIPO_OP_CHOICES = [
        ('MTO', 'Make to Order (Bajo Demanda)'),
        ('MTS', 'Make to Stock (Para Stock)'),
    ]
    numero_op = models.CharField(max_length=20, unique=True, verbose_name="N° Orden de Producción")
    tipo_orden = models.CharField(max_length=3, choices=TIPO_OP_CHOICES, default='MTO', verbose_name="Tipo de Orden")
    orden_venta_origen = models.ForeignKey(
        OrdenVenta, on_delete=models.SET_NULL, null=True, blank=True, related_name="ops_generadas",
    )
    producto_a_producir = models.ForeignKey(ProductoTerminado, on_delete=models.PROTECT, related_name="ordenes_produccion")
    cantidad_a_producir = models.PositiveIntegerField()
    estado_op = models.ForeignKey(EstadoOrden, on_delete=models.SET_NULL, null=True, blank=True, related_name="ops_estado")
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_inicio_planificada = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateTimeField(null=True, blank=True)
    fecha_fin_planificada = models.DateField(null=True, blank=True)
    sector_asignado_op = models.ForeignKey(SectorAsignado, on_delete=models.SET_NULL, null=True, blank=True, related_name="ops_sector")
    notas = models.TextField(null=True, blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Orden de Producción"
        verbose_name_plural = "Órdenes de Producción"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['empresa', 'estado_op']),
            models.Index(fields=['producto_a_producir', 'estado_op']),
            models.Index(fields=['orden_venta_origen']),
            models.Index(fields=['empresa', 'fecha_solicitud']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.tipo_orden == 'MTO' and not self.orden_venta_origen:
            raise ValidationError("Las órdenes MTO deben tener una Orden de Venta origen")

    def get_estado_op_display(self):
        return self.estado_op.nombre if self.estado_op else "Sin Estado Asignado"
    
    @property
    def es_para_stock(self):
        return self.tipo_orden == 'MTS'
    
    @property
    def es_bajo_demanda(self):
        return self.tipo_orden == 'MTO'

    def __str__(self):
        tipo_display = "STOCK" if self.es_para_stock else "DEMANDA"
        return f"OP: {self.numero_op} ({tipo_display}) - {self.cantidad_a_producir} x {self.producto_a_producir.descripcion}"


class Reportes(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_produccion_asociada",)
    orden_produccion_asociada = models.ForeignKey(
        OrdenProduccion, on_delete=models.SET_NULL, null=True, blank=True, related_name="reportes_incidencia",
    )
    n_reporte = models.CharField(max_length=20, unique=True)
    fecha = models.DateTimeField(default=timezone.now)
    tipo_problema = models.CharField(max_length=100)
    informe_reporte = models.TextField(blank=True, null=True)
    resuelto = models.BooleanField(default=False, verbose_name="¿Problema Resuelto?")
    fecha_resolucion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Resolución")
    reportado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reportes_creados")
    sector_reporta = models.ForeignKey(SectorAsignado, on_delete=models.SET_NULL, null=True, blank=True, related_name="reportes_originados_aqui")

    class Meta:
        verbose_name = "Reporte de Incidencia"
        verbose_name_plural = "Reportes de Incidencias"
        ordering = ['-fecha']

    def __str__(self):
        op_num = self.orden_produccion_asociada.numero_op if self.orden_produccion_asociada else "N/A"
        return f"Reporte {self.n_reporte} (OP: {op_num})"


class LoteProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("producto", "op_asociada", "deposito")
    producto = models.ForeignKey(ProductoTerminado, on_delete=models.PROTECT, related_name="lotes")
    op_asociada = models.ForeignKey(OrdenProduccion, on_delete=models.PROTECT, related_name="lotes_pt")
    cantidad = models.PositiveIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enviado = models.BooleanField(default=False)
    deposito = models.ForeignKey("Deposito", on_delete=models.PROTECT, related_name="lotes_productos_terminados", null=True, blank=True)

    class Meta:
        verbose_name = "Lote de Producto Terminado"
        verbose_name_plural = "Lotes de Productos Terminados"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Lote de {self.producto.descripcion} - OP {self.op_asociada.numero_op} ({self.cantidad})"


# =============================================================================
# ÓRDENES DE COMPRA
# =============================================================================

class Orden(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito", "insumo_principal")
    TIPO_ORDEN_CHOICES = [("compra", "Orden de Compra")]
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

    numero_orden = models.CharField(max_length=20, unique=True, verbose_name="N° Orden de Compra")
    tipo = models.CharField(max_length=20, choices=TIPO_ORDEN_CHOICES, default="compra")
    fecha_creacion = models.DateTimeField(default=timezone.now)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="ordenes_de_compra_a_proveedor")
    estado = models.CharField(max_length=30, choices=ESTADO_ORDEN_COMPRA_CHOICES, default="BORRADOR")
    insumo_principal = models.ForeignKey(Insumo, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Insumo Principal")
    cantidad_principal = models.PositiveIntegerField(null=True, blank=True, verbose_name="Cantidad Insumo Principal")
    precio_unitario_compra = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio Unit. Compra")
    deposito = models.ForeignKey('Deposito', on_delete=models.PROTECT, null=True, blank=True, related_name='ordenes_de_compra', verbose_name='Depósito que solicita')
    fecha_estimada_entrega = models.DateField(null=True, blank=True)
    numero_tracking = models.CharField(max_length=50, null=True, blank=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['empresa', 'deposito']),
            models.Index(fields=['estado', 'fecha_creacion']),
            models.Index(fields=['proveedor', 'estado']),
        ]

    def __str__(self):
        return f"OC: {self.numero_orden} - Proveedor: {self.proveedor.nombre}"

    def get_estado_display_custom(self):
        return dict(self.ESTADO_ORDEN_COMPRA_CHOICES).get(self.estado, self.estado)

    @property
    def total_orden_compra(self):
        from decimal import Decimal
        if self.insumo_principal and self.cantidad_principal and self.precio_unitario_compra is not None:
            return Decimal(self.cantidad_principal) * self.precio_unitario_compra
        return Decimal('0.00')

    @staticmethod
    def pedidos_por_deposito(deposito_id):
        return Orden.objects.filter(insumo_principal__deposito_id=deposito_id)
    
    @staticmethod
    def solicitudes_por_deposito(deposito_id):
        return OrdenProduccion.objects.filter(producto_a_producir__deposito_id=deposito_id)


# =============================================================================
# NOTIFICACIONES
# =============================================================================

class NotificacionSistema(EmpresaScopedModel):
    TIPOS_NOTIFICACION = [
        ('stock_bajo', 'Stock Bajo'),
        ('oc_creada', 'Orden de Compra Creada'),
        ('oc_enviada', 'Orden de Compra Enviada'),
        ('oc_recibida', 'Orden de Compra Recibida'),
        ('pedido_recibido', 'Pedido Recibido en Depósito'),
        ('transferencia_solicitada', 'Transferencia Solicitada'),
        ('produccion_completada', 'Producción Completada'),
        ('solicitud_insumos', 'Solicitud de Insumos'),
        ('general', 'Notificación General'),
    ]
    GRUPOS_DESTINO = [
        ('compras', 'Departamento de Compras'),
        ('ventas', 'Departamento de Ventas'),
        ('deposito', 'Depósito'),
        ('produccion', 'Producción'),
        ('control_calidad', 'Control de Calidad'),
        ('administrador', 'Administración'),
        ('todos', 'Todos los usuarios'),
    ]
    PRIORIDADES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    tipo = models.CharField(max_length=30, choices=TIPOS_NOTIFICACION, default='general')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones_enviadas')
    destinatario_grupo = models.CharField(max_length=20, choices=GRUPOS_DESTINO)
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default='media')
    datos_contexto = models.JSONField(blank=True, null=True)
    leida = models.BooleanField(default=False)
    atendida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    fecha_atencion = models.DateTimeField(null=True, blank=True)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Notificación del Sistema"
        verbose_name_plural = "Notificaciones del Sistema"

    def __str__(self):
        return f"{self.titulo} - {self.get_destinatario_grupo_display()}"
    
    def marcar_como_leida(self, usuario=None):
        self.leida = True
        self.fecha_lectura = timezone.now()
        self.save(update_fields=['leida', 'fecha_lectura'])
    
    def marcar_como_atendida(self, usuario=None):
        self.atendida = True
        self.fecha_atencion = timezone.now()
        if not self.leida:
            self.marcar_como_leida(usuario)
        else:
            self.save(update_fields=['atendida', 'fecha_atencion'])
    
    def esta_expirada(self):
        if self.fecha_expiracion:
            return timezone.now() > self.fecha_expiracion
        return False
    
    @property
    def css_prioridad(self):
        mapping = {'baja': 'text-muted', 'media': 'text-info', 'alta': 'text-warning', 'critica': 'text-danger'}
        return mapping.get(self.prioridad, 'text-info')
    
    @property
    def icono_tipo(self):
        mapping = {
            'stock_bajo': 'bi-exclamation-triangle-fill',
            'oc_creada': 'bi-cart-plus-fill',
            'oc_enviada': 'bi-truck',
            'oc_recibida': 'bi-check-circle-fill',
            'pedido_recibido': 'bi-box-seam-fill',
            'transferencia_solicitada': 'bi-arrow-left-right',
            'produccion_completada': 'bi-gear-fill',
            'solicitud_insumos': 'bi-clipboard-data',
            'general': 'bi-info-circle-fill'
        }
        return mapping.get(self.tipo, 'bi-bell-fill')


# =============================================================================
# HISTORIAL DE IMPORTACIONES
# =============================================================================

class HistorialImportacion(EmpresaScopedModel):
    TIPO_IMPORTACION_CHOICES = [
        ('insumos', 'Insumos'),
        ('productos', 'Productos Terminados'),
        ('clientes', 'Clientes'),
        ('proveedores', 'Proveedores'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='importaciones_realizadas')
    tipo_importacion = models.CharField(max_length=50, choices=TIPO_IMPORTACION_CHOICES, verbose_name="Tipo de Importación")
    nombre_archivo = models.CharField(max_length=255, verbose_name="Nombre del Archivo")
    fecha_importacion = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Importación")
    registros_importados = models.PositiveIntegerField(default=0, verbose_name="Registros Importados")
    registros_actualizados = models.PositiveIntegerField(default=0, verbose_name="Registros Actualizados")
    registros_con_error = models.PositiveIntegerField(default=0, verbose_name="Registros con Error")
    exitoso = models.BooleanField(default=False, verbose_name="Importación Exitosa")
    deposito = models.ForeignKey('Deposito', on_delete=models.SET_NULL, null=True, blank=True, related_name='importaciones')
    errores_detalle = models.JSONField(default=list, blank=True, verbose_name="Detalle de Errores")
    warnings_detalle = models.JSONField(default=list, blank=True, verbose_name="Detalle de Advertencias")
    
    class Meta:
        verbose_name = "Historial de Importación"
        verbose_name_plural = "Historial de Importaciones"
        ordering = ['-fecha_importacion']

    def __str__(self):
        return f"{self.get_tipo_importacion_display()} - {self.fecha_importacion.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def total_procesados(self):
        return self.registros_importados + self.registros_actualizados + self.registros_con_error
    
    @property
    def porcentaje_exito(self):
        total = self.total_procesados
        if total == 0:
            return 0
        return round((self.registros_importados + self.registros_actualizados) / total * 100, 1)
