"""
Filtros personalizados para la API REST de LUMINOVA.

Este módulo define filtros para búsquedas avanzadas y filtrado
de datos en los endpoints de la API.
"""

import django_filters
from django_filters import rest_framework as filters

from App_LUMINOVA.models import (
    ProductoTerminado,
    Insumo,
    OrdenVenta,
    OrdenProduccion,
    Orden,
    NotificacionSistema,
    MovimientoStock,
    StockInsumo,
    StockProductoTerminado,
    Cliente,
    Proveedor,
)


class ProductoTerminadoFilter(filters.FilterSet):
    """Filtro para productos terminados."""
    
    descripcion = filters.CharFilter(lookup_expr='icontains')
    precio_min = filters.NumberFilter(field_name='precio_unitario', lookup_expr='gte')
    precio_max = filters.NumberFilter(field_name='precio_unitario', lookup_expr='lte')
    stock_min = filters.NumberFilter(method='filter_stock_min')
    stock_max = filters.NumberFilter(method='filter_stock_max')
    necesita_reposicion = filters.BooleanFilter(method='filter_necesita_reposicion')
    produccion_habilitada = filters.BooleanFilter()
    modelo = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = ProductoTerminado
        fields = [
            'categoria', 'deposito', 'descripcion', 'modelo',
            'produccion_habilitada', 'material', 'color_luz'
        ]
    
    def filter_stock_min(self, queryset, name, value):
        """Filtrar productos con stock mínimo."""
        # Esto requiere anotación ya que stock es una property
        return queryset.filter(
            id__in=[p.id for p in queryset if p.stock >= value]
        )
    
    def filter_stock_max(self, queryset, name, value):
        """Filtrar productos con stock máximo."""
        return queryset.filter(
            id__in=[p.id for p in queryset if p.stock <= value]
        )
    
    def filter_necesita_reposicion(self, queryset, name, value):
        """Filtrar productos que necesitan reposición."""
        if value:
            return queryset.filter(
                id__in=[p.id for p in queryset if p.necesita_reposicion]
            )
        return queryset.filter(
            id__in=[p.id for p in queryset if not p.necesita_reposicion]
        )


class InsumoFilter(filters.FilterSet):
    """Filtro para insumos."""
    
    descripcion = filters.CharFilter(lookup_expr='icontains')
    stock_min = filters.NumberFilter(method='filter_stock_min')
    stock_max = filters.NumberFilter(method='filter_stock_max')
    notificado_a_compras = filters.BooleanFilter()
    
    class Meta:
        model = Insumo
        fields = ['categoria', 'deposito', 'fabricante', 'notificado_a_compras']
    
    def filter_stock_min(self, queryset, name, value):
        return queryset.filter(
            id__in=[i.id for i in queryset if i.stock >= value]
        )
    
    def filter_stock_max(self, queryset, name, value):
        return queryset.filter(
            id__in=[i.id for i in queryset if i.stock <= value]
        )


class OrdenVentaFilter(filters.FilterSet):
    """Filtro para órdenes de venta."""
    
    numero_ov = filters.CharFilter(lookup_expr='icontains')
    fecha_desde = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='gte')
    fecha_hasta = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='lte')
    total_min = filters.NumberFilter(field_name='total_ov', lookup_expr='gte')
    total_max = filters.NumberFilter(field_name='total_ov', lookup_expr='lte')
    cliente_nombre = filters.CharFilter(field_name='cliente__nombre', lookup_expr='icontains')
    
    class Meta:
        model = OrdenVenta
        fields = ['cliente', 'estado', 'numero_ov']


class OrdenProduccionFilter(filters.FilterSet):
    """Filtro para órdenes de producción."""
    
    numero_op = filters.CharFilter(lookup_expr='icontains')
    fecha_desde = filters.DateTimeFilter(field_name='fecha_solicitud', lookup_expr='gte')
    fecha_hasta = filters.DateTimeFilter(field_name='fecha_solicitud', lookup_expr='lte')
    producto_descripcion = filters.CharFilter(
        field_name='producto_a_producir__descripcion', lookup_expr='icontains'
    )
    
    class Meta:
        model = OrdenProduccion
        fields = [
            'tipo_orden', 'estado_op', 'sector_asignado_op',
            'producto_a_producir', 'orden_venta_origen'
        ]


class OrdenCompraFilter(filters.FilterSet):
    """Filtro para órdenes de compra."""
    
    numero_orden = filters.CharFilter(lookup_expr='icontains')
    fecha_desde = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='gte')
    fecha_hasta = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='lte')
    proveedor_nombre = filters.CharFilter(
        field_name='proveedor__nombre', lookup_expr='icontains'
    )
    insumo_descripcion = filters.CharFilter(
        field_name='insumo_principal__descripcion', lookup_expr='icontains'
    )
    
    class Meta:
        model = Orden
        fields = ['proveedor', 'estado', 'deposito', 'insumo_principal']


class NotificacionFilter(filters.FilterSet):
    """Filtro para notificaciones del sistema."""
    
    fecha_desde = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='gte')
    fecha_hasta = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='lte')
    titulo = filters.CharFilter(lookup_expr='icontains')
    no_leidas = filters.BooleanFilter(field_name='leida', exclude=True)
    no_atendidas = filters.BooleanFilter(field_name='atendida', exclude=True)
    
    class Meta:
        model = NotificacionSistema
        fields = ['tipo', 'destinatario_grupo', 'prioridad', 'leida', 'atendida']


class MovimientoStockFilter(filters.FilterSet):
    """Filtro para movimientos de stock."""
    
    fecha_desde = filters.DateTimeFilter(field_name='fecha', lookup_expr='gte')
    fecha_hasta = filters.DateTimeFilter(field_name='fecha', lookup_expr='lte')
    
    class Meta:
        model = MovimientoStock
        fields = [
            'insumo', 'producto', 'deposito_origen', 'deposito_destino',
            'tipo', 'usuario'
        ]


class StockInsumoFilter(filters.FilterSet):
    """Filtro para stock de insumos."""
    
    cantidad_min = filters.NumberFilter(field_name='cantidad', lookup_expr='gte')
    cantidad_max = filters.NumberFilter(field_name='cantidad', lookup_expr='lte')
    insumo_descripcion = filters.CharFilter(
        field_name='insumo__descripcion', lookup_expr='icontains'
    )
    
    class Meta:
        model = StockInsumo
        fields = ['insumo', 'deposito']


class StockProductoTerminadoFilter(filters.FilterSet):
    """Filtro para stock de productos terminados."""
    
    cantidad_min = filters.NumberFilter(field_name='cantidad', lookup_expr='gte')
    cantidad_max = filters.NumberFilter(field_name='cantidad', lookup_expr='lte')
    producto_descripcion = filters.CharFilter(
        field_name='producto__descripcion', lookup_expr='icontains'
    )
    
    class Meta:
        model = StockProductoTerminado
        fields = ['producto', 'deposito']


class ClienteFilter(filters.FilterSet):
    """Filtro para clientes."""
    
    nombre = filters.CharFilter(lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    telefono = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = Cliente
        fields = ['nombre', 'email']


class ProveedorFilter(filters.FilterSet):
    """Filtro para proveedores."""
    
    nombre = filters.CharFilter(lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    contacto = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = Proveedor
        fields = ['nombre', 'email']
