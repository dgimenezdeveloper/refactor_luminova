"""
Serializadores para la API REST de LUMINOVA.

Este módulo define los serializadores que convierten los modelos Django
a formato JSON y viceversa, con soporte para multi-tenancy.
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from App_LUMINOVA.models import (
    Empresa,
    Deposito,
    CategoriaProductoTerminado,
    CategoriaInsumo,
    ProductoTerminado,
    Insumo,
    Proveedor,
    Fabricante,
    OfertaProveedor,
    ComponenteProducto,
    Cliente,
    OrdenVenta,
    ItemOrdenVenta,
    EstadoOrden,
    SectorAsignado,
    OrdenProduccion,
    Reportes,
    Factura,
    Orden,
    LoteProductoTerminado,
    HistorialOV,
    UsuarioDeposito,
    StockInsumo,
    StockProductoTerminado,
    MovimientoStock,
    NotificacionSistema,
    AuditoriaAcceso,
    PerfilUsuario,
    RolEmpresa,
)


# =============================================================================
# SERIALIZADORES BASE
# =============================================================================

class EmpresaSerializer(serializers.ModelSerializer):
    """Serializador para el modelo Empresa."""
    
    class Meta:
        model = Empresa
        fields = [
            'id', 'nombre', 'razon_social', 'cuit', 'direccion',
            'telefono', 'email', 'fecha_creacion', 'activa'
        ]
        read_only_fields = ['id', 'fecha_creacion']


class DepositoSerializer(serializers.ModelSerializer):
    """Serializador para el modelo Deposito."""
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    
    class Meta:
        model = Deposito
        fields = [
            'id', 'nombre', 'empresa', 'empresa_nombre',
            'ubicacion', 'descripcion'
        ]
        read_only_fields = ['id']


class UserSimpleSerializer(serializers.ModelSerializer):
    """Serializador simplificado de usuarios para referencias."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = fields


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    """Serializador para perfil de usuario."""
    user = UserSimpleSerializer(read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    
    class Meta:
        model = PerfilUsuario
        fields = ['id', 'user', 'empresa', 'empresa_nombre', 'fecha_asignacion']
        read_only_fields = ['id', 'fecha_asignacion']


# =============================================================================
# SERIALIZADORES DE CATÁLOGOS
# =============================================================================

class CategoriaProductoTerminadoSerializer(serializers.ModelSerializer):
    """Serializador para categorías de productos terminados."""
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    
    class Meta:
        model = CategoriaProductoTerminado
        fields = [
            'id', 'nombre', 'imagen', 'deposito', 'deposito_nombre', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class CategoriaInsumoSerializer(serializers.ModelSerializer):
    """Serializador para categorías de insumos."""
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    
    class Meta:
        model = CategoriaInsumo
        fields = [
            'id', 'nombre', 'imagen', 'deposito', 'deposito_nombre', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class ProveedorSerializer(serializers.ModelSerializer):
    """Serializador para proveedores."""
    
    class Meta:
        model = Proveedor
        fields = [
            'id', 'nombre', 'contacto', 'telefono', 'email', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class FabricanteSerializer(serializers.ModelSerializer):
    """Serializador para fabricantes."""
    
    class Meta:
        model = Fabricante
        fields = [
            'id', 'nombre', 'contacto', 'telefono', 'email', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class ClienteSerializer(serializers.ModelSerializer):
    """Serializador para clientes."""
    
    class Meta:
        model = Cliente
        fields = [
            'id', 'nombre', 'direccion', 'telefono', 'email', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class EstadoOrdenSerializer(serializers.ModelSerializer):
    """Serializador para estados de orden de producción."""
    
    class Meta:
        model = EstadoOrden
        fields = ['id', 'nombre', 'empresa']
        read_only_fields = ['id', 'empresa']


class SectorAsignadoSerializer(serializers.ModelSerializer):
    """Serializador para sectores de producción."""
    
    class Meta:
        model = SectorAsignado
        fields = ['id', 'nombre', 'empresa']
        read_only_fields = ['id', 'empresa']


# =============================================================================
# SERIALIZADORES DE INVENTARIO
# =============================================================================

class ProductoTerminadoSerializer(serializers.ModelSerializer):
    """Serializador para productos terminados."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    stock = serializers.IntegerField(read_only=True)
    necesita_reposicion = serializers.BooleanField(read_only=True)
    porcentaje_stock = serializers.FloatField(read_only=True)
    cantidad_reposicion_sugerida = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ProductoTerminado
        fields = [
            'id', 'descripcion', 'categoria', 'categoria_nombre',
            'precio_unitario', 'stock', 'stock_minimo', 'stock_objetivo',
            'produccion_habilitada', 'modelo', 'potencia', 'acabado',
            'color_luz', 'material', 'imagen', 'deposito', 'deposito_nombre',
            'necesita_reposicion', 'porcentaje_stock', 'cantidad_reposicion_sugerida',
            'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'stock', 'necesita_reposicion', 
                          'porcentaje_stock', 'cantidad_reposicion_sugerida']


class ProductoTerminadoListSerializer(serializers.ModelSerializer):
    """Serializador simplificado para listados de productos."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    stock = serializers.IntegerField(read_only=True)
    necesita_reposicion = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ProductoTerminado
        fields = [
            'id', 'descripcion', 'categoria', 'categoria_nombre',
            'precio_unitario', 'stock', 'stock_minimo', 'deposito',
            'deposito_nombre', 'necesita_reposicion', 'imagen'
        ]


class InsumoSerializer(serializers.ModelSerializer):
    """Serializador para insumos."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    fabricante_nombre = serializers.CharField(source='fabricante.nombre', read_only=True, allow_null=True)
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    stock = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Insumo
        fields = [
            'id', 'descripcion', 'categoria', 'categoria_nombre',
            'fabricante', 'fabricante_nombre', 'imagen',
            'cantidad_en_pedido', 'deposito', 'deposito_nombre',
            'stock', 'notificado_a_compras', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'stock']


class OfertaProveedorSerializer(serializers.ModelSerializer):
    """Serializador para ofertas de proveedor."""
    insumo_descripcion = serializers.CharField(source='insumo.descripcion', read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    
    class Meta:
        model = OfertaProveedor
        fields = [
            'id', 'insumo', 'insumo_descripcion', 'proveedor', 'proveedor_nombre',
            'precio_unitario_compra', 'tiempo_entrega_estimado_dias',
            'fecha_actualizacion_precio', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class ComponenteProductoSerializer(serializers.ModelSerializer):
    """Serializador para componentes de producto (BOM)."""
    insumo_descripcion = serializers.CharField(source='insumo.descripcion', read_only=True)
    producto_descripcion = serializers.CharField(source='producto_terminado.descripcion', read_only=True)
    
    class Meta:
        model = ComponenteProducto
        fields = [
            'id', 'producto_terminado', 'producto_descripcion',
            'insumo', 'insumo_descripcion', 'cantidad_necesaria', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class StockInsumoSerializer(serializers.ModelSerializer):
    """Serializador para stock de insumos por depósito."""
    insumo_descripcion = serializers.CharField(source='insumo.descripcion', read_only=True)
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    
    class Meta:
        model = StockInsumo
        fields = [
            'id', 'insumo', 'insumo_descripcion', 'deposito',
            'deposito_nombre', 'cantidad', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class StockProductoTerminadoSerializer(serializers.ModelSerializer):
    """Serializador para stock de productos terminados por depósito."""
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    
    class Meta:
        model = StockProductoTerminado
        fields = [
            'id', 'producto', 'producto_descripcion', 'deposito',
            'deposito_nombre', 'cantidad', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class MovimientoStockSerializer(serializers.ModelSerializer):
    """Serializador para movimientos de stock."""
    insumo_descripcion = serializers.CharField(source='insumo.descripcion', read_only=True, allow_null=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True, allow_null=True)
    deposito_origen_nombre = serializers.CharField(source='deposito_origen.nombre', read_only=True, allow_null=True)
    deposito_destino_nombre = serializers.CharField(source='deposito_destino.nombre', read_only=True, allow_null=True)
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True, allow_null=True)
    
    class Meta:
        model = MovimientoStock
        fields = [
            'id', 'insumo', 'insumo_descripcion', 'producto', 'producto_descripcion',
            'deposito_origen', 'deposito_origen_nombre',
            'deposito_destino', 'deposito_destino_nombre',
            'cantidad', 'tipo', 'fecha', 'usuario', 'usuario_nombre', 'motivo', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'fecha', 'usuario']


# =============================================================================
# SERIALIZADORES DE VENTAS
# =============================================================================

class ItemOrdenVentaSerializer(serializers.ModelSerializer):
    """Serializador para items de orden de venta."""
    producto_descripcion = serializers.CharField(source='producto_terminado.descripcion', read_only=True)
    
    class Meta:
        model = ItemOrdenVenta
        fields = [
            'id', 'orden_venta', 'producto_terminado', 'producto_descripcion',
            'cantidad', 'precio_unitario_venta', 'subtotal', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'subtotal']


class OrdenVentaListSerializer(serializers.ModelSerializer):
    """Serializador simplificado para listados de órdenes de venta."""
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cantidad_items = serializers.SerializerMethodField()
    # FASE 2: total_ov es @property, se define como SerializerMethodField
    total_ov = serializers.SerializerMethodField()
    
    class Meta:
        model = OrdenVenta
        fields = [
            'id', 'numero_ov', 'cliente', 'cliente_nombre',
            'fecha_creacion', 'estado', 'total_ov', 'cantidad_items'
        ]
    
    def get_cantidad_items(self, obj) -> int:
        """Retorna la cantidad de items en la orden de venta."""
        return obj.items_ov.count()
    
    def get_total_ov(self, obj) -> str:
        """Retorna el total calculado de la orden de venta."""
        return str(obj.total_ov)


class OrdenVentaSerializer(serializers.ModelSerializer):
    """Serializador completo para órdenes de venta."""
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    items = ItemOrdenVentaSerializer(source='items_ov', many=True, read_only=True)
    resumen_estados_ops = serializers.CharField(source='get_resumen_estados_ops', read_only=True)
    # FASE 2: total_ov es @property, se define como SerializerMethodField
    total_ov = serializers.SerializerMethodField()
    
    class Meta:
        model = OrdenVenta
        fields = [
            'id', 'numero_ov', 'cliente', 'cliente_nombre',
            'fecha_creacion', 'estado', 'total_ov', 'notas',
            'items', 'resumen_estados_ops', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'numero_ov', 'total_ov']
    
    def get_total_ov(self, obj) -> str:
        """Retorna el total calculado de la orden de venta."""
        return str(obj.total_ov)


class OrdenVentaCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear órdenes de venta."""
    
    class Meta:
        model = OrdenVenta
        fields = ['cliente', 'notas']
    
    def create(self, validated_data):
        # Generar número de OV automáticamente
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        validated_data['numero_ov'] = f"OV-{timestamp}"
        return super().create(validated_data)


class FacturaSerializer(serializers.ModelSerializer):
    """Serializador para facturas."""
    orden_venta_numero = serializers.CharField(source='orden_venta.numero_ov', read_only=True)
    
    class Meta:
        model = Factura
        fields = [
            'id', 'numero_factura', 'orden_venta', 'orden_venta_numero',
            'fecha_emision', 'total_facturado', 'empresa'
        ]
        read_only_fields = ['id', 'empresa']


class HistorialOVSerializer(serializers.ModelSerializer):
    """Serializador para historial de órdenes de venta."""
    realizado_por_nombre = serializers.CharField(source='realizado_por.username', read_only=True, allow_null=True)
    
    class Meta:
        model = HistorialOV
        fields = [
            'id', 'orden_venta', 'fecha_evento', 'descripcion',
            'tipo_evento', 'realizado_por', 'realizado_por_nombre'
        ]
        read_only_fields = ['id', 'fecha_evento']


# =============================================================================
# SERIALIZADORES DE PRODUCCIÓN
# =============================================================================

class OrdenProduccionListSerializer(serializers.ModelSerializer):
    """Serializador simplificado para listados de órdenes de producción."""
    producto_descripcion = serializers.CharField(source='producto_a_producir.descripcion', read_only=True)
    estado_nombre = serializers.CharField(source='estado_op.nombre', read_only=True, allow_null=True)
    sector_nombre = serializers.CharField(source='sector_asignado_op.nombre', read_only=True, allow_null=True)
    orden_venta_numero = serializers.CharField(source='orden_venta_origen.numero_ov', read_only=True, allow_null=True)
    
    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'numero_op', 'tipo_orden', 'producto_a_producir',
            'producto_descripcion', 'cantidad_a_producir', 'estado_op',
            'estado_nombre', 'sector_asignado_op', 'sector_nombre',
            'orden_venta_origen', 'orden_venta_numero', 'fecha_solicitud'
        ]


class OrdenProduccionSerializer(serializers.ModelSerializer):
    """Serializador completo para órdenes de producción."""
    producto_descripcion = serializers.CharField(source='producto_a_producir.descripcion', read_only=True)
    estado_nombre = serializers.CharField(source='estado_op.nombre', read_only=True, allow_null=True)
    sector_nombre = serializers.CharField(source='sector_asignado_op.nombre', read_only=True, allow_null=True)
    orden_venta_numero = serializers.CharField(source='orden_venta_origen.numero_ov', read_only=True, allow_null=True)
    es_para_stock = serializers.BooleanField(read_only=True)
    es_bajo_demanda = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'numero_op', 'tipo_orden', 'orden_venta_origen', 'orden_venta_numero',
            'producto_a_producir', 'producto_descripcion', 'cantidad_a_producir',
            'estado_op', 'estado_nombre', 'fecha_solicitud',
            'fecha_inicio_real', 'fecha_inicio_planificada',
            'fecha_fin_real', 'fecha_fin_planificada',
            'sector_asignado_op', 'sector_nombre', 'notas',
            'es_para_stock', 'es_bajo_demanda', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'numero_op', 'es_para_stock', 'es_bajo_demanda']


class OrdenProduccionCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear órdenes de producción."""
    
    class Meta:
        model = OrdenProduccion
        fields = [
            'tipo_orden', 'orden_venta_origen', 'producto_a_producir',
            'cantidad_a_producir', 'estado_op', 'fecha_inicio_planificada',
            'fecha_fin_planificada', 'sector_asignado_op', 'notas'
        ]
    
    def create(self, validated_data):
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        validated_data['numero_op'] = f"OP-{timestamp}"
        return super().create(validated_data)


class ReportesSerializer(serializers.ModelSerializer):
    """Serializador para reportes de incidencias."""
    orden_produccion_numero = serializers.CharField(
        source='orden_produccion_asociada.numero_op', read_only=True, allow_null=True
    )
    reportado_por_nombre = serializers.CharField(
        source='reportado_por.username', read_only=True, allow_null=True
    )
    sector_nombre = serializers.CharField(
        source='sector_reporta.nombre', read_only=True, allow_null=True
    )
    
    class Meta:
        model = Reportes
        fields = [
            'id', 'n_reporte', 'orden_produccion_asociada', 'orden_produccion_numero',
            'fecha', 'tipo_problema', 'informe_reporte', 'resuelto',
            'fecha_resolucion', 'reportado_por', 'reportado_por_nombre',
            'sector_reporta', 'sector_nombre', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'n_reporte', 'fecha']


class LoteProductoTerminadoSerializer(serializers.ModelSerializer):
    """Serializador para lotes de productos terminados."""
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    op_numero = serializers.CharField(source='op_asociada.numero_op', read_only=True)
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True, allow_null=True)
    
    class Meta:
        model = LoteProductoTerminado
        fields = [
            'id', 'producto', 'producto_descripcion', 'op_asociada', 'op_numero',
            'cantidad', 'fecha_creacion', 'enviado', 'deposito', 'deposito_nombre',
            'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'fecha_creacion']


# =============================================================================
# SERIALIZADORES DE COMPRAS
# =============================================================================

class OrdenCompraListSerializer(serializers.ModelSerializer):
    """Serializador simplificado para listados de órdenes de compra."""
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    insumo_descripcion = serializers.CharField(
        source='insumo_principal.descripcion', read_only=True, allow_null=True
    )
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True, allow_null=True)
    estado_display = serializers.CharField(source='get_estado_display_custom', read_only=True)
    # FASE 2: total_orden_compra es @property, se define como SerializerMethodField
    total_orden_compra = serializers.SerializerMethodField()
    
    class Meta:
        model = Orden
        fields = [
            'id', 'numero_orden', 'tipo', 'fecha_creacion', 'proveedor',
            'proveedor_nombre', 'estado', 'estado_display', 'insumo_principal',
            'insumo_descripcion', 'cantidad_principal', 'total_orden_compra',
            'deposito', 'deposito_nombre'
        ]
    
    def get_total_orden_compra(self, obj) -> str:
        """Retorna el total calculado de la orden de compra."""
        return str(obj.total_orden_compra)


class OrdenCompraSerializer(serializers.ModelSerializer):
    """Serializador completo para órdenes de compra."""
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    insumo_descripcion = serializers.CharField(
        source='insumo_principal.descripcion', read_only=True, allow_null=True
    )
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True, allow_null=True)
    estado_display = serializers.CharField(source='get_estado_display_custom', read_only=True)
    # FASE 2: total_orden_compra es @property, se define como SerializerMethodField
    total_orden_compra = serializers.SerializerMethodField()
    
    class Meta:
        model = Orden
        fields = [
            'id', 'numero_orden', 'tipo', 'fecha_creacion', 'proveedor',
            'proveedor_nombre', 'estado', 'estado_display', 'insumo_principal',
            'insumo_descripcion', 'cantidad_principal', 'precio_unitario_compra',
            'deposito', 'deposito_nombre', 'total_orden_compra',
            'fecha_estimada_entrega', 'numero_tracking', 'notas', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'numero_orden', 'total_orden_compra']
    
    def get_total_orden_compra(self, obj) -> str:
        """Retorna el total calculado de la orden de compra."""
        return str(obj.total_orden_compra)


# =============================================================================
# SERIALIZADORES DE SISTEMA
# =============================================================================

class UsuarioDepositoSerializer(serializers.ModelSerializer):
    """Serializador para asignaciones usuario-depósito."""
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    deposito_nombre = serializers.CharField(source='deposito.nombre', read_only=True)
    
    class Meta:
        model = UsuarioDeposito
        fields = [
            'id', 'usuario', 'usuario_nombre', 'deposito', 'deposito_nombre',
            'puede_transferir', 'puede_entradas', 'puede_salidas',
            'fecha_asignacion', 'empresa'
        ]
        read_only_fields = ['id', 'empresa', 'fecha_asignacion']


class NotificacionSistemaSerializer(serializers.ModelSerializer):
    """Serializador para notificaciones del sistema."""
    remitente_nombre = serializers.CharField(source='remitente.username', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    destinatario_display = serializers.CharField(source='get_destinatario_grupo_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    esta_expirada = serializers.BooleanField(read_only=True)
    css_prioridad = serializers.CharField(read_only=True)
    icono_tipo = serializers.CharField(read_only=True)
    
    class Meta:
        model = NotificacionSistema
        fields = [
            'id', 'tipo', 'tipo_display', 'titulo', 'mensaje',
            'remitente', 'remitente_nombre', 'destinatario_grupo', 'destinatario_display',
            'prioridad', 'prioridad_display', 'datos_contexto',
            'leida', 'atendida', 'fecha_creacion', 'fecha_lectura',
            'fecha_atencion', 'fecha_expiracion', 'esta_expirada',
            'css_prioridad', 'icono_tipo', 'empresa'
        ]
        read_only_fields = [
            'id', 'empresa', 'fecha_creacion', 'fecha_lectura', 'fecha_atencion',
            'esta_expirada', 'css_prioridad', 'icono_tipo'
        ]


class NotificacionSistemaCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear notificaciones."""
    
    class Meta:
        model = NotificacionSistema
        fields = [
            'tipo', 'titulo', 'mensaje', 'destinatario_grupo',
            'prioridad', 'datos_contexto', 'fecha_expiracion'
        ]


class AuditoriaAccesoSerializer(serializers.ModelSerializer):
    """Serializador para auditorías de acceso (solo lectura)."""
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True, allow_null=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True, allow_null=True)
    # GenericIPAddressField se define explícitamente como CharField para evitar problemas de serialización
    ip_address = serializers.CharField(read_only=True, allow_null=True)
    
    class Meta:
        model = AuditoriaAcceso
        fields = [
            'id', 'usuario', 'usuario_nombre', 'empresa', 'empresa_nombre',
            'accion', 'fecha_hora', 'ip_address', 'user_agent'
        ]
        read_only_fields = fields


class RolEmpresaSerializer(serializers.ModelSerializer):
    """Serializador para roles de empresa."""
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    class Meta:
        model = RolEmpresa
        fields = ['id', 'empresa', 'group', 'group_name', 'nombre', 'descripcion']
        read_only_fields = ['id']


# =============================================================================
# SERIALIZADORES DE AUTENTICACIÓN
# =============================================================================

class UserDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado del usuario actual."""
    perfil = PerfilUsuarioSerializer(read_only=True)
    depositos_asignados = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'date_joined', 'last_login',
            'perfil', 'depositos_asignados'
        ]
        read_only_fields = fields
    
    def get_depositos_asignados(self, obj):
        asignaciones = obj.depositos_asignados.all()
        return UsuarioDepositoSerializer(asignaciones, many=True).data
