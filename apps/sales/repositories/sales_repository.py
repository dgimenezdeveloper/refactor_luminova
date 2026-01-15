"""
Repositorios para el módulo de ventas.

Proporcionan una capa de abstracción para órdenes de venta, clientes y facturación.
"""

from typing import List, Optional
from django.db.models import QuerySet, Sum, Q
from django.db import transaction
from datetime import datetime, timedelta

from apps.core.base import BaseRepository

# Importamos modelos desde las nuevas apps modulares
from apps.sales.models import (
    OrdenVenta,
    ItemOrdenVenta,
    Cliente,
    Factura,
    HistorialOV,
)


class ClienteRepository(BaseRepository[Cliente]):
    """Repositorio para operaciones con clientes."""
    
    model = Cliente
    
    def get_by_email(self, email: str) -> Optional[Cliente]:
        """Obtiene un cliente por email."""
        try:
            return self._get_base_queryset().get(email=email)
        except Cliente.DoesNotExist:
            return None
    
    def search(self, query: str) -> QuerySet[Cliente]:
        """Busca clientes por nombre, email o teléfono."""
        return self._get_base_queryset().filter(
            Q(nombre__icontains=query) |
            Q(email__icontains=query) |
            Q(telefono__icontains=query)
        )
    
    def get_con_ordenes_pendientes(self) -> QuerySet[Cliente]:
        """Obtiene clientes con órdenes pendientes."""
        estados_pendientes = ['PENDIENTE', 'CONFIRMADA', 'INSUMOS_SOLICITADOS', 'PRODUCCION_INICIADA']
        return self._get_base_queryset().filter(
            ordenes_venta_sales__estado__in=estados_pendientes
        ).distinct()
    
    def get_top_clientes(self, limit: int = 10) -> QuerySet:
        """Obtiene los mejores clientes por volumen de compras."""
        from django.db.models import Count
        return self._get_base_queryset().annotate(
            total_ordenes=Count('ordenes_venta_sales')
        ).order_by('-total_ordenes')[:limit]


class OrdenVentaRepository(BaseRepository[OrdenVenta]):
    """Repositorio para órdenes de venta."""
    
    model = OrdenVenta
    
    def get_by_numero(self, numero_ov: str) -> Optional[OrdenVenta]:
        """Obtiene una orden por su número."""
        try:
            return self._get_base_queryset().get(numero_ov=numero_ov)
        except OrdenVenta.DoesNotExist:
            return None
    
    def get_by_cliente(self, cliente_id: int) -> QuerySet[OrdenVenta]:
        """Obtiene órdenes de un cliente."""
        return self._get_base_queryset().filter(cliente_id=cliente_id)
    
    def get_by_estado(self, estado: str) -> QuerySet[OrdenVenta]:
        """Obtiene órdenes por estado."""
        return self._get_base_queryset().filter(estado=estado)
    
    def get_pendientes(self) -> QuerySet[OrdenVenta]:
        """Obtiene órdenes pendientes de procesar."""
        estados_pendientes = ['PENDIENTE', 'CONFIRMADA']
        return self._get_base_queryset().filter(estado__in=estados_pendientes)
    
    def get_en_produccion(self) -> QuerySet[OrdenVenta]:
        """Obtiene órdenes en producción."""
        estados_produccion = ['INSUMOS_SOLICITADOS', 'PRODUCCION_INICIADA', 'PRODUCCION_CON_PROBLEMAS']
        return self._get_base_queryset().filter(estado__in=estados_produccion)
    
    def get_listas_entrega(self) -> QuerySet[OrdenVenta]:
        """Obtiene órdenes listas para entrega."""
        return self._get_base_queryset().filter(estado='LISTA_ENTREGA')
    
    def get_by_fecha_rango(self, fecha_inicio: datetime, fecha_fin: datetime) -> QuerySet[OrdenVenta]:
        """Obtiene órdenes en un rango de fechas."""
        return self._get_base_queryset().filter(
            fecha_creacion__gte=fecha_inicio,
            fecha_creacion__lte=fecha_fin
        )
    
    def get_recientes(self, dias: int = 30) -> QuerySet[OrdenVenta]:
        """Obtiene órdenes de los últimos N días."""
        fecha_limite = datetime.now() - timedelta(days=dias)
        return self._get_base_queryset().filter(fecha_creacion__gte=fecha_limite)
    
    def get_with_items(self, orden_id: int) -> Optional[OrdenVenta]:
        """Obtiene una orden con sus items precargados."""
        try:
            return self._get_base_queryset().prefetch_related(
                'items_ov_sales__producto_terminado'
            ).get(pk=orden_id)
        except OrdenVenta.DoesNotExist:
            return None
    
    def generar_numero_ov(self) -> str:
        """Genera un nuevo número de orden de venta."""
        from django.utils import timezone
        year = timezone.now().year
        prefix = f"OV-{year}-"
        
        # Obtener el último número del año
        ultima = self.model.objects.filter(
            numero_ov__startswith=prefix
        ).order_by('-numero_ov').first()
        
        if ultima:
            try:
                ultimo_num = int(ultima.numero_ov.replace(prefix, ''))
                nuevo_num = ultimo_num + 1
            except ValueError:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"{prefix}{nuevo_num:05d}"


class ItemOrdenVentaRepository(BaseRepository[ItemOrdenVenta]):
    """Repositorio para items de órdenes de venta."""
    
    model = ItemOrdenVenta
    
    def get_by_orden(self, orden_id: int) -> QuerySet[ItemOrdenVenta]:
        """Obtiene items de una orden."""
        return self._get_base_queryset().filter(orden_venta_id=orden_id)
    
    def get_by_producto(self, producto_id: int) -> QuerySet[ItemOrdenVenta]:
        """Obtiene items que contienen un producto específico."""
        return self._get_base_queryset().filter(producto_terminado_id=producto_id)
    
    def get_cantidad_vendida(self, producto_id: int, dias: int = 30) -> int:
        """Calcula la cantidad vendida de un producto en los últimos N días."""
        fecha_limite = datetime.now() - timedelta(days=dias)
        result = self._get_base_queryset().filter(
            producto_terminado_id=producto_id,
            orden_venta__fecha_creacion__gte=fecha_limite,
            orden_venta__estado__in=['COMPLETADA', 'LISTA_ENTREGA']
        ).aggregate(total=Sum('cantidad'))
        return result['total'] or 0


class FacturaRepository(BaseRepository[Factura]):
    """Repositorio para facturas."""
    
    model = Factura
    
    def get_by_numero(self, numero: str) -> Optional[Factura]:
        """Obtiene una factura por número."""
        try:
            return self._get_base_queryset().get(numero_factura=numero)
        except Factura.DoesNotExist:
            return None
    
    def get_by_orden_venta(self, orden_id: int) -> Optional[Factura]:
        """Obtiene la factura asociada a una orden de venta."""
        try:
            return self._get_base_queryset().get(orden_venta_id=orden_id)
        except Factura.DoesNotExist:
            return None
    
    def get_by_fecha_rango(self, fecha_inicio: datetime, fecha_fin: datetime) -> QuerySet[Factura]:
        """Obtiene facturas en un rango de fechas."""
        return self._get_base_queryset().filter(
            fecha_emision__gte=fecha_inicio,
            fecha_emision__lte=fecha_fin
        )
    
    def get_total_facturado(self, fecha_inicio: datetime = None, fecha_fin: datetime = None) -> dict:
        """Calcula el total facturado en un período."""
        qs = self._get_base_queryset()
        if fecha_inicio:
            qs = qs.filter(fecha_emision__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_emision__lte=fecha_fin)
        
        result = qs.aggregate(
            total=Sum('total_facturado'),
            cantidad=Count('id')
        )
        return {
            'total_facturado': result['total'] or 0,
            'cantidad_facturas': result['cantidad'] or 0
        }


class HistorialOVRepository(BaseRepository[HistorialOV]):
    """Repositorio para historial de órdenes de venta."""
    
    model = HistorialOV
    
    def get_by_orden(self, orden_id: int) -> QuerySet[HistorialOV]:
        """Obtiene el historial de una orden."""
        return self._get_base_queryset().filter(orden_venta_id=orden_id).order_by('-fecha_evento')
    
    def registrar_evento(
        self,
        orden_venta,
        descripcion: str,
        tipo_evento: str = None,
        usuario=None
    ) -> HistorialOV:
        """Registra un evento en el historial de una orden."""
        return self.create(
            orden_venta=orden_venta,
            descripcion=descripcion,
            tipo_evento=tipo_evento,
            realizado_por=usuario
        )


# Importar Count si no está importado
from django.db.models import Count
