

from django.conf import settings

from django.contrib.auth.models import Group, User

# Asegurar import de models antes de definir modelos personalizados
from django.db import models
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
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum, F
from django.utils import timezone  # Importar timezone

from .threadlocals import get_current_empresa

# Perfil extendido para asociar usuario a empresa
class PerfilUsuario(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name="usuarios")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.empresa.nombre})"


class EmpresaScopedModel(models.Model):
    """Base abstracta para modelos aislados por empresa."""

    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s",
        null=True,
        blank=True,
    )

    # Campos relacionados desde los cuales podemos inferir la empresa.
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
# TP_LUMINOVA-main/App_LUMINOVA/models.py

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone  # Importar timezone


# --- CATEGORÍAS Y ENTIDADES BASE ---
class CategoriaProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito",)
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


class ProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito", "categoria")
    descripcion = models.CharField(max_length=255)  # Aumentado max_length
    categoria = models.ForeignKey(
        CategoriaProductoTerminado,
        on_delete=models.PROTECT,
        related_name="productos_terminados",
    )
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # NOTA: stock se calcula desde StockProductoTerminado (campo eliminado en migration)
    # Campos para gestión de stock
    stock_minimo = models.IntegerField(
        default=0, 
        verbose_name="Stock Mínimo",
        help_text="Nivel mínimo de stock que debe mantenerse (punto de reorden)"
    )
    stock_objetivo = models.IntegerField(
        default=0,
        verbose_name="Stock Objetivo", 
        help_text="Nivel deseado de stock después de reabastecer"
    )
    produccion_habilitada = models.BooleanField(
        default=True,
        verbose_name="Habilitado para Producción",
        help_text="Indica si este producto puede ser producido para stock"
    )
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
        """Stock total del producto en todos sus depósitos (desde StockProductoTerminado)"""
        # IMPORTANTE: Esta es una property, NO un campo de BD
        result = StockProductoTerminado.objects.filter(
            producto=self
        ).aggregate(total=Sum('cantidad'))['total']
        return result if result is not None else 0
    
    def get_stock_by_deposito(self, deposito: 'Deposito') -> int:
        """Stock del producto en un depósito específico"""
        try:
            stock_record = StockProductoTerminado.objects.get(
                producto=self,
                deposito=deposito
            )
            return stock_record.cantidad
        except StockProductoTerminado.DoesNotExist:
            return 0
    
    @property
    def necesita_reposicion(self):
        """Indica si el producto necesita reposición de stock"""
        return self.stock <= self.stock_minimo
    
    @property
    def necesita_reposicion_stock(self):
        """Indica si el producto necesita reposición urgente (alias para compatibilidad)"""
        return self.stock <= self.stock_minimo and self.stock_minimo > 0
    
    @property
    def cantidad_reposicion_sugerida(self):
        """Calcula la cantidad sugerida para reposición"""
        if self.necesita_reposicion:
            return max(0, self.stock_objetivo - self.stock)
        return 0
    
    @property
    def porcentaje_stock(self):
        """Calcula el porcentaje de stock actual respecto al objetivo"""
        if self.stock_objetivo > 0:
            return (self.stock / self.stock_objetivo) * 100
        return 0
    
    def puede_producir_para_stock(self):
        """Verifica si el producto puede ser producido para stock"""
        return self.produccion_habilitada and self.stock_objetivo > 0


class CategoriaInsumo(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito",)
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


class Proveedor(EmpresaScopedModel):
    nombre = models.CharField(max_length=100)  # ❌ Quitado unique=True (multi-tenant fix)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    email = models.EmailField(blank=True, null=True)
    
    class Meta:
        unique_together = ('nombre', 'empresa')
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['empresa', 'nombre']),
        ]

    def __str__(self):
        return self.nombre

    def _infer_empresa_from_relations(self):
        empresa = super()._infer_empresa_from_relations()
        if empresa:
            return empresa
        orden = self.ordenes_de_compra_a_proveedor.filter(empresa__isnull=False).first()
        return orden.empresa if orden else None


class Fabricante(EmpresaScopedModel):
    nombre = models.CharField(max_length=100)  # ❌ Quitado unique=True (multi-tenant fix)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=25, blank=True)  # Aumentado max_length
    email = models.EmailField(blank=True, null=True)
    
    class Meta:
        unique_together = ('nombre', 'empresa')
        verbose_name = "Fabricante"
        verbose_name_plural = "Fabricantes"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['empresa', 'nombre']),
        ]

    def __str__(self):
        return self.nombre

    def _infer_empresa_from_relations(self):
        empresa = super()._infer_empresa_from_relations()
        if empresa:
            return empresa
        insumo = self.insumos_fabricados.filter(empresa__isnull=False).first()
        return insumo.empresa if insumo else None


class Insumo(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito", "categoria")
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
    # NOTA: stock se calcula desde StockInsumo (campo eliminado en migration)
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
        """Stock total del insumo en todos sus depósitos (desde StockInsumo)"""
        # IMPORTANTE: Esta es una property, NO un campo de BD
        result = StockInsumo.objects.filter(
            insumo=self
        ).aggregate(total=Sum('cantidad'))['total']
        return result if result is not None else 0
    
    def get_stock_by_deposito(self, deposito: 'Deposito') -> int:
        """Stock del insumo en un depósito específico"""
        try:
            stock_record = StockInsumo.objects.get(
                insumo=self,
                deposito=deposito
            )
            return stock_record.cantidad
        except StockInsumo.DoesNotExist:
            return 0


# --- NUEVO MODELO INTERMEDIO ---
class OfertaProveedor(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("insumo", "proveedor")
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
        indexes = [
            models.Index(fields=['empresa']),
            models.Index(fields=['insumo']),
            models.Index(fields=['proveedor']),
        ]

    def __str__(self):
        return f"{self.insumo.descripcion} - {self.proveedor.nombre} (${self.precio_unitario_compra})"


class ComponenteProducto(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("producto_terminado", "insumo")
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
        indexes = [
            models.Index(fields=['producto_terminado']),
            models.Index(fields=['empresa']),
        ]

    def __str__(self):
        return f"{self.cantidad_necesaria} x {self.insumo.descripcion} para {self.producto_terminado.descripcion}"


# --- MODELOS DE GESTIÓN ---
class Cliente(EmpresaScopedModel):
    nombre = models.CharField(max_length=150)  # ❌ Quitado unique=True (multi-tenant fix)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=25, blank=True)
    email = models.EmailField(null=True, blank=True)  # ❌ Quitado unique=True (multi-tenant fix)
    
    class Meta:
        unique_together = (
            ('nombre', 'empresa'),
            ('email', 'empresa'),
        )
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['empresa', 'nombre']),
        ]

    def __str__(self):
        return self.nombre

    def _infer_empresa_from_relations(self):
        empresa = super()._infer_empresa_from_relations()
        if empresa:
            return empresa
        ov = self.ordenes_venta.filter(empresa__isnull=False).first()
        return ov.empresa if ov else None


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
    # FASE 2: total_ov ahora es @property calculada (eliminado campo DecimalField)
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
        """Total calculado dinámicamente desde items de la orden de venta."""
        from decimal import Decimal
        from django.db.models import Sum
        total = self.items_ov.aggregate(total=Sum('subtotal'))['total']
        return total or Decimal('0.00')

    def _infer_empresa_from_relations(self):
        empresa = super()._infer_empresa_from_relations()
        if empresa:
            return empresa
        item = self.items_ov.select_related("producto_terminado__deposito").first()
        if item and item.producto_terminado:
            producto = item.producto_terminado
            if producto.empresa_id:
                return producto.empresa
            if producto.deposito and producto.deposito.empresa_id:
                return producto.deposito.empresa
        return None

    # FASE 2: actualizar_total() ya no es necesario - total_ov es @property

    def actualizar_estado_por_ops(self):
        """
        Actualiza el estado de una OV basado en el estado más avanzado de sus OPs asociadas.
        
        Lógica para estados mixtos:
        - Si todas las OPs están completadas -> COMPLETADA
        - Si hay OPs completadas y otras pendientes/en proceso -> Según el estado más avanzado
        - Si hay OPs canceladas, se consideran en la evaluación pero no bloquean el progreso
        - Si todas las OPs están canceladas -> CANCELADA
        """
        from collections import Counter
        
        # Mapeo de estados de OP a estados de OV y su prioridad
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
            "COMPLETADA": 6,
            "LISTA_ENTREGA": 5,
            "PRODUCCION_INICIADA": 4,
            "INSUMOS_SOLICITADOS": 3,
            "CONFIRMADA": 2,
            "PENDIENTE": 1,
            "CANCELADA": 0,
        }

        ops_asociadas = self.ops_generadas.all()
        if not ops_asociadas.exists():
            return  # No hay OPs asociadas, no se actualiza el estado

        # Obtener todos los estados de las OPs y mapearlos a estados de OV
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
            return  # No hay estados válidos para mapear

        total_ops = len(estados_ops)
        ops_completadas = contador_estados.get("Completada", 0)
        ops_canceladas = contador_estados.get("Cancelada", 0)
        ops_activas = total_ops - ops_canceladas  # OPs que no están canceladas

        # Lógica especial para estados mixtos
        nuevo_estado = None
        
        # Caso 1: Todas las OPs están canceladas
        if ops_canceladas == total_ops:
            nuevo_estado = "CANCELADA"
        
        # Caso 2: Todas las OPs activas están completadas
        elif ops_completadas == ops_activas and ops_activas > 0:
            nuevo_estado = "LISTA_ENTREGA"  # Listo para entrega
        
        # Caso 3: Hay OPs completadas y otras en proceso (estado mixto)
        elif ops_completadas > 0 and ops_activas > ops_completadas:
            # En estados mixtos, NO permitir COMPLETADA hasta que todas estén listas
            # Obtener el estado más avanzado de las OPs no completadas
            estados_no_completados = [
                estado for estado in estados_ops 
                if estado not in ["COMPLETADA", "CANCELADA"]
            ]
            if estados_no_completados:
                estado_mas_avanzado_activo = max(
                    estados_no_completados,
                    key=lambda estado: ESTADOS_PRIORIDAD.get(estado, 0),
                )
                # En estado mixto, usar el estado más avanzado pero NO permitir degradación
                # Si ya está en COMPLETADA y hay OPs pendientes, mantener COMPLETADA pero registrar inconsistencia
                if self.estado == "COMPLETADA":
                    print(f"⚠️  INCONSISTENCIA: OV {self.numero_ov} está COMPLETADA pero tiene OPs pendientes")
                    nuevo_estado = None  # No cambiar estado para evitar degradación
                else:
                    nuevo_estado = estado_mas_avanzado_activo
            else:
                nuevo_estado = "PRODUCCION_INICIADA"  # Fallback
        
        # Caso 4: Ninguna OP completada, usar el estado más avanzado
        else:
            nuevo_estado = max(
                estados_ops,
                key=lambda estado: ESTADOS_PRIORIDAD.get(estado, 0),
            )

        # Solo actualizar si el estado cambió y no degrada el progreso
        if (nuevo_estado and 
            nuevo_estado != self.estado and 
            ESTADOS_PRIORIDAD.get(nuevo_estado, 0) >= ESTADOS_PRIORIDAD.get(self.estado, 0)):
            
            self.estado = nuevo_estado
            self.save(update_fields=["estado"])
            
            # Log para debug
            print(f"OV {self.numero_ov}: Estado actualizado de {self.estado} a {nuevo_estado}")
            print(f"  - OPs completadas: {ops_completadas}/{ops_activas}")
            print(f"  - OPs canceladas: {ops_canceladas}")

    def get_resumen_estados_ops(self):
        """
        Retorna un resumen del estado de las OPs asociadas para mostrar en la interfaz.
        """
        from collections import Counter
        
        ops_asociadas = self.ops_generadas.all()
        if not ops_asociadas.exists():
            return "Sin OPs asociadas"
        
        contador = Counter()
        for op in ops_asociadas:
            if op.estado_op:
                contador[op.estado_op.nombre] += 1
        
        resumen_partes = []
        for estado, cantidad in contador.most_common():
            resumen_partes.append(f"{cantidad} {estado}")
        
        return " | ".join(resumen_partes)


class ItemOrdenVenta(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_venta", "producto_terminado")
    orden_venta = models.ForeignKey(
        OrdenVenta, on_delete=models.CASCADE, related_name="items_ov"
    )
    producto_terminado = models.ForeignKey(ProductoTerminado, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario_venta = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Precio Unit. en Venta"
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        verbose_name = "Item de Orden de Venta"
        verbose_name_plural = "Items de Órdenes de Venta"
        indexes = [
            models.Index(fields=['orden_venta']),
            models.Index(fields=['empresa']),
        ]

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario_venta
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto_terminado.descripcion} en OV {self.orden_venta.numero_ov}"


class EstadoOrden(models.Model):
    """Catálogo de estados para órdenes de producción (multi-tenant)"""
    nombre = models.CharField(max_length=50)
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='estados_orden',
        null=True,
        blank=True,
        help_text='Empresa a la que pertenece este estado (null = compartido)'
    )

    class Meta:
        unique_together = ('nombre', 'empresa')
        verbose_name = "Estado de Orden"
        verbose_name_plural = "Estados de Orden"

    def __str__(self):
        return self.nombre


class SectorAsignado(models.Model):
    """Catálogo de sectores de producción (multi-tenant)"""
    nombre = models.CharField(max_length=50)
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='sectores',
        null=True,
        blank=True,
        help_text='Empresa a la que pertenece este sector (null = compartido)'
    )

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
    
    numero_op = models.CharField(
        max_length=20, unique=True, verbose_name="N° Orden de Producción"
    )
    tipo_orden = models.CharField(
        max_length=3,
        choices=TIPO_OP_CHOICES,
        default='MTO',
        verbose_name="Tipo de Orden",
        help_text="MTO: Producción bajo demanda vinculada a una OV, MTS: Producción para stock"
    )
    orden_venta_origen = models.ForeignKey(
        OrdenVenta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_generadas",
        help_text="Solo para órdenes MTO (Make to Order)"
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
        """Validaciones personalizadas del modelo"""
        super().clean()
        if self.tipo_orden == 'MTO' and not self.orden_venta_origen:
            raise ValidationError("Las órdenes MTO (Make to Order) deben tener una Orden de Venta origen")
        

    def get_estado_op_display(self):
        if self.estado_op:
            return self.estado_op.nombre
        return "Sin Estado Asignado"
    
    @property
    def es_para_stock(self):
        """Indica si esta orden es para producción de stock"""
        return self.tipo_orden == 'MTS'
    
    @property
    def es_bajo_demanda(self):
        """Indica si esta orden es bajo demanda"""
        return self.tipo_orden == 'MTO'

    def __str__(self):
        tipo_display = "STOCK" if self.es_para_stock else "DEMANDA"
        return f"OP: {self.numero_op} ({tipo_display}) - {self.cantidad_a_producir} x {self.producto_a_producir.descripcion}"


class Reportes(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_produccion_asociada",)
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

    class Meta:
        verbose_name = "Reporte de Incidencia"
        verbose_name_plural = "Reportes de Incidencias"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa', 'resuelto']),
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['orden_produccion_asociada']),
        ]

    def __str__(self):
        op_num = (
            self.orden_produccion_asociada.numero_op
            if self.orden_produccion_asociada
            else "N/A"
        )
        return f"Reporte {self.n_reporte} (OP: {op_num})"


class Factura(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_venta",)
    numero_factura = models.CharField(
        max_length=50  # ❌ Quitado unique=True (multi-tenant fix)
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
    
    class Meta:
        unique_together = ('numero_factura', 'empresa')
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"

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
    """Registro de auditoría de accesos al sistema (multi-tenant)"""
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias',
        help_text='Empresa donde se realizó la acción auditada'
    )
    accion = models.CharField(max_length=255)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Auditoría de Acceso"
        verbose_name_plural = "Auditorías de Acceso"
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['empresa', 'fecha_hora']),
        ]

    def __str__(self):
        user_display = (
            self.usuario.username if self.usuario else "Usuario Desconocido/Eliminado"
        )
        return f"{user_display} - {self.accion} @ {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"


class Orden(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("deposito", "insumo_principal")
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

    # FASE 2: total_orden_compra ahora es @property calculada (eliminado campo DecimalField)

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
        """Total calculado dinámicamente desde cantidad y precio unitario."""
        from decimal import Decimal
        if (self.insumo_principal and self.cantidad_principal 
            and self.precio_unitario_compra is not None):
            return Decimal(self.cantidad_principal) * self.precio_unitario_compra
        return Decimal('0.00')

    # FASE 2: save() ya no necesita calcular total_orden_compra


class LoteProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("producto", "op_asociada", "deposito")
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

    class Meta:
        verbose_name = "Lote de Producto Terminado"
        verbose_name_plural = "Lotes de Productos Terminados"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['empresa', 'op_asociada']),
            models.Index(fields=['empresa', 'producto']),
            models.Index(fields=['enviado']),
        ]

    def __str__(self):
        return f"Lote de {self.producto.descripcion} - OP {self.op_asociada.numero_op} ({self.cantidad})"


class HistorialOV(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("orden_venta",)
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
        indexes = [
            models.Index(fields=['orden_venta', 'fecha_evento']),
            models.Index(fields=['empresa']),
        ]

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


# Modelo para empresas (multi-tenancy lógico)
class Empresa(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    razon_social = models.CharField(max_length=255, blank=True)
    cuit = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.nombre

# Modelo para los depósitos
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
    """Modelo para gestionar permisos de usuarios por depósito (multi-tenant)"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depositos_asignados')
    deposito = models.ForeignKey(Deposito, on_delete=models.CASCADE, related_name='usuarios_asignados')
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='usuarios_depositos',
        null=True,
        blank=True,
        help_text='Empresa a la que pertenece esta asignación'
    )
    puede_transferir = models.BooleanField(default=True, help_text="Puede realizar transferencias desde/hacia este depósito")
    puede_entradas = models.BooleanField(default=True, help_text="Puede registrar entradas de stock")
    puede_salidas = models.BooleanField(default=True, help_text="Puede registrar salidas de stock")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    EMPRESA_FALLBACK_FIELDS = ("deposito",)

    class Meta:
        unique_together = ('usuario', 'deposito')
        verbose_name = "Asignación Usuario-Depósito"
        verbose_name_plural = "Asignaciones Usuario-Depósito"
        indexes = [
            models.Index(fields=['empresa']),
        ]

    def save(self, *args, **kwargs):
        # Auto-asignar empresa desde el depósito si no está establecida
        if not self.empresa_id and self.deposito_id:
            self.empresa = self.deposito.empresa
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.deposito.nombre}"

class StockInsumo(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("insumo", "deposito")
    insumo = models.ForeignKey('Insumo', on_delete=models.CASCADE)
    deposito = models.ForeignKey('Deposito', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('insumo', 'deposito')
        verbose_name = "Stock de Insumo"
        verbose_name_plural = "Stocks de Insumos"
        indexes = [
            models.Index(fields=['empresa']),
            models.Index(fields=['insumo']),
        ]

class StockProductoTerminado(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("producto", "deposito")
    producto = models.ForeignKey('ProductoTerminado', on_delete=models.CASCADE)
    deposito = models.ForeignKey('Deposito', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'deposito')
        verbose_name = "Stock de Producto Terminado"
        verbose_name_plural = "Stocks de Productos Terminados"
        indexes = [
            models.Index(fields=['empresa']),
            models.Index(fields=['producto']),
        ]

class MovimientoStock(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = (
        "deposito_origen",
        "deposito_destino",
        "insumo",
        "producto",
    )
    insumo = models.ForeignKey('Insumo', on_delete=models.CASCADE, null=True, blank=True)
    producto = models.ForeignKey('ProductoTerminado', on_delete=models.CASCADE, null=True, blank=True)
    deposito_origen = models.ForeignKey('Deposito', on_delete=models.CASCADE, related_name='movimientos_salida', null=True, blank=True)
    deposito_destino = models.ForeignKey('Deposito', on_delete=models.CASCADE, related_name='movimientos_entrada', null=True, blank=True)
    cantidad = models.IntegerField()
    tipo = models.CharField(max_length=20, choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('transferencia', 'Transferencia')])
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['empresa', 'tipo']),
            models.Index(fields=['deposito_origen', 'fecha']),
            models.Index(fields=['deposito_destino', 'fecha']),
        ]


class NotificacionSistema(EmpresaScopedModel):
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
