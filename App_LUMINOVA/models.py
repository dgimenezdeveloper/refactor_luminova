# TP_LUMINOVA-main/App_LUMINOVA/models.py

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone  # Importar timezone


# --- CATEGORÍAS Y ENTIDADES BASE ---
class CategoriaProductoTerminado(models.Model):
    nombre = models.CharField(
        max_length=100, verbose_name="Nombre Categoría PT"
    )  # Aumentado max_length
    imagen = models.ImageField(upload_to="categorias_productos/", null=True, blank=True)
    deposito = models.ForeignKey(
        "Deposito",
        on_delete=models.CASCADE,
        related_name="categorias_producto_terminado",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Categoría de Producto Terminado"
        verbose_name_plural = "Categorías de Productos Terminados"
        unique_together = ("nombre", "deposito")

    def __str__(self):
        return self.nombre


class ProductoTerminado(models.Model):
    descripcion = models.CharField(max_length=255)  # Aumentado max_length
    categoria = models.ForeignKey(
        CategoriaProductoTerminado,
        on_delete=models.PROTECT,
        related_name="productos_terminados",
    )
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.IntegerField(default=0)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    potencia = models.IntegerField(blank=True, null=True)
    acabado = models.CharField(max_length=50, blank=True, null=True)
    color_luz = models.CharField(max_length=50, blank=True, null=True)
    material = models.CharField(max_length=50, blank=True, null=True)
    imagen = models.ImageField(null=True, blank=True, upload_to="productos_terminados/")
    deposito = models.ForeignKey(
        "Deposito",
        on_delete=models.PROTECT,
        related_name="productos_terminados",
        null=True,
        blank=True,
        help_text="Depósito al que pertenece este producto terminado",
    )

    def __str__(self):
        return f"{self.descripcion} (Modelo: {self.modelo or 'N/A'})"


class CategoriaInsumo(models.Model):
    nombre = models.CharField(
        max_length=100, verbose_name="Nombre Categoría Insumo"
    )
    imagen = models.ImageField(upload_to="categorias_insumos/", null=True, blank=True)
    deposito = models.ForeignKey(
        "Deposito",
        on_delete=models.CASCADE,
        related_name="categorias_insumo",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Categoría de Insumo"
        verbose_name_plural = "Categorías de Insumos"
        unique_together = ("nombre", "deposito")

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Fabricante(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=25, blank=True)  # Aumentado max_length
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Insumo(models.Model):
    notificado_a_compras = models.BooleanField(default=False, help_text="¿Ya fue notificado a compras por stock bajo?")
    descripcion = models.CharField(max_length=255)
    categoria = models.ForeignKey(
        CategoriaInsumo, on_delete=models.PROTECT, related_name="insumos"
    )
    fabricante = models.ForeignKey(
        Fabricante,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insumos_fabricados",
    )
    imagen = models.ImageField(null=True, blank=True, upload_to="insumos/")
    stock = models.IntegerField(default=0)
    cantidad_en_pedido = models.PositiveIntegerField(
        default=0, verbose_name="Cantidad en Pedido", blank=True, null=True
    )
    deposito = models.ForeignKey(
        "Deposito",
        on_delete=models.PROTECT,
        related_name="insumos",
        null=True,
        blank=True,
        help_text="Depósito al que pertenece este insumo",
    )

    def __str__(self):
        return self.descripcion


# --- NUEVO MODELO INTERMEDIO ---
class OfertaProveedor(models.Model):
    insumo = models.ForeignKey(
        Insumo, on_delete=models.CASCADE, related_name="ofertas_de_proveedores"
    )
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.CASCADE, related_name="provee_insumos"
    )
    precio_unitario_compra = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Precio de Compra Unitario"
    )
    tiempo_entrega_estimado_dias = models.IntegerField(
        default=0, verbose_name="Tiempo de Entrega Estimado (días)"
    )
    fecha_actualizacion_precio = models.DateTimeField(
        default=timezone.now, verbose_name="Última Actualización del Precio"
    )

    class Meta:
        unique_together = (
            "insumo",
            "proveedor",
        )
        verbose_name = "Oferta de Proveedor por Insumo"
        verbose_name_plural = "Ofertas de Proveedores por Insumos"
        ordering = ["insumo__descripcion", "proveedor__nombre"]

    def __str__(self):
        return f"{self.insumo.descripcion} - {self.proveedor.nombre} (${self.precio_unitario_compra})"


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
    @staticmethod
    def pedidos_por_deposito(deposito_id):
        """
        Devuelve las órdenes de compra cuyo insumo principal pertenece al depósito indicado.
        """
        return Orden.objects.filter(insumo_principal__deposito_id=deposito_id)
    @staticmethod
    def solicitudes_por_deposito(deposito_id):
        """
        Devuelve las solicitudes de insumos (OPs) cuyo producto a producir pertenece al depósito indicado.
        """
        return OrdenProduccion.objects.filter(producto_a_producir__deposito_id=deposito_id)
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

    deposito = models.ForeignKey(
        'Deposito',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ordenes_de_compra',
        verbose_name='Depósito que solicita',
        help_text='Depósito que origina la solicitud de compra',
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


class LoteProductoTerminado(models.Model):
    producto = models.ForeignKey(
        ProductoTerminado, on_delete=models.PROTECT, related_name="lotes"
    )
    op_asociada = models.ForeignKey(
        OrdenProduccion, on_delete=models.PROTECT, related_name="lotes_pt"
    )
    cantidad = models.PositiveIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enviado = models.BooleanField(default=False)
    deposito = models.ForeignKey(
        "Deposito",
        on_delete=models.PROTECT,
        related_name="lotes_productos_terminados",
        null=True,
        blank=True,
        help_text="Depósito donde se encuentra el lote",
    )

    def __str__(self):
        return f"Lote de {self.producto.descripcion} - OP {self.op_asociada.numero_op} ({self.cantidad})"


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

# Modelo para los depósitos
class Deposito(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    ubicacion = models.CharField(max_length=255, blank=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


class UsuarioDeposito(models.Model):
    """Modelo para gestionar permisos de usuarios por depósito"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depositos_asignados')
    deposito = models.ForeignKey(Deposito, on_delete=models.CASCADE, related_name='usuarios_asignados')
    puede_transferir = models.BooleanField(default=True, help_text="Puede realizar transferencias desde/hacia este depósito")
    puede_entradas = models.BooleanField(default=True, help_text="Puede registrar entradas de stock")
    puede_salidas = models.BooleanField(default=True, help_text="Puede registrar salidas de stock")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'deposito')
        verbose_name = "Asignación Usuario-Depósito"
        verbose_name_plural = "Asignaciones Usuario-Depósito"

    def __str__(self):
        return f"{self.usuario.username} - {self.deposito.nombre}"

class StockInsumo(models.Model):
    insumo = models.ForeignKey('Insumo', on_delete=models.CASCADE)
    deposito = models.ForeignKey('Deposito', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('insumo', 'deposito')

class StockProductoTerminado(models.Model):
    producto = models.ForeignKey('ProductoTerminado', on_delete=models.CASCADE)
    deposito = models.ForeignKey('Deposito', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'deposito')

class MovimientoStock(models.Model):
    insumo = models.ForeignKey('Insumo', on_delete=models.CASCADE, null=True, blank=True)
    producto = models.ForeignKey('ProductoTerminado', on_delete=models.CASCADE, null=True, blank=True)
    deposito_origen = models.ForeignKey('Deposito', on_delete=models.CASCADE, related_name='movimientos_salida', null=True, blank=True)
    deposito_destino = models.ForeignKey('Deposito', on_delete=models.CASCADE, related_name='movimientos_entrada', null=True, blank=True)
    cantidad = models.IntegerField()
    tipo = models.CharField(max_length=20, choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('transferencia', 'Transferencia')])
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    motivo = models.CharField(max_length=255, blank=True)


class NotificacionSistema(models.Model):
    """Sistema de notificaciones entre módulos para mantener separación de responsabilidades"""
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
    
    # Datos adicionales en formato JSON para contexto específico
    datos_contexto = models.JSONField(blank=True, null=True, help_text="Datos adicionales en formato JSON")
    
    # Estado de la notificación
    leida = models.BooleanField(default=False)
    atendida = models.BooleanField(default=False, help_text="Indica si se tomó acción sobre la notificación")
    
    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    fecha_atencion = models.DateTimeField(null=True, blank=True)
    
    # Para notificaciones que expiran
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Notificación del Sistema"
        verbose_name_plural = "Notificaciones del Sistema"
        indexes = [
            models.Index(fields=['destinatario_grupo', 'leida']),
            models.Index(fields=['tipo', 'fecha_creacion']),
            models.Index(fields=['prioridad', 'fecha_creacion']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.get_destinatario_grupo_display()}"
    
    def marcar_como_leida(self, usuario=None):
        """Marca la notificación como leída"""
        self.leida = True
        self.fecha_lectura = timezone.now()
        self.save(update_fields=['leida', 'fecha_lectura'])
    
    def marcar_como_atendida(self, usuario=None):
        """Marca la notificación como atendida"""
        self.atendida = True
        self.fecha_atencion = timezone.now()
        if not self.leida:
            self.marcar_como_leida(usuario)
        else:
            self.save(update_fields=['atendida', 'fecha_atencion'])
    
    def esta_expirada(self):
        """Verifica si la notificación ha expirado"""
        if self.fecha_expiracion:
            return timezone.now() > self.fecha_expiracion
        return False
    
    @property
    def css_prioridad(self):
        """Retorna la clase CSS según la prioridad"""
        mapping = {
            'baja': 'text-muted',
            'media': 'text-info',
            'alta': 'text-warning',
            'critica': 'text-danger'
        }
        return mapping.get(self.prioridad, 'text-info')
    
    @property
    def icono_tipo(self):
        """Retorna el ícono Bootstrap según el tipo"""
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
