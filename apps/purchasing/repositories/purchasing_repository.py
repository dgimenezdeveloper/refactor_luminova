"""
Repositorios para el módulo de compras.

Proporcionan una capa de abstracción para órdenes de compra,
proveedores, fabricantes y ofertas.
"""

from typing import List, Optional
from django.db.models import QuerySet, Sum, Q, Count
from datetime import datetime, timedelta

from apps.core.base import BaseRepository

# Importamos modelos desde las nuevas apps modulares
from apps.purchasing.models import (
    Orden,
    Proveedor,
    OfertaProveedor,
)
from apps.inventory.models import Fabricante


class ProveedorRepository(BaseRepository[Proveedor]):
    """Repositorio para proveedores."""
    
    model = Proveedor
    
    def get_by_nombre(self, nombre: str) -> Optional[Proveedor]:
        """Obtiene un proveedor por nombre."""
        try:
            return self._get_base_queryset().get(nombre=nombre)
        except Proveedor.DoesNotExist:
            return None
    
    def search(self, query: str) -> QuerySet[Proveedor]:
        """Busca proveedores por nombre, contacto o email."""
        return self._get_base_queryset().filter(
            Q(nombre__icontains=query) |
            Q(contacto__icontains=query) |
            Q(email__icontains=query)
        )
    
    def get_con_ordenes_activas(self) -> QuerySet[Proveedor]:
        """Obtiene proveedores con órdenes de compra activas."""
        estados_activos = ['APROBADA', 'ENVIADA_PROVEEDOR', 'CONFIRMADA_PROVEEDOR', 'EN_TRANSITO']
        return self._get_base_queryset().filter(
            ordenes_de_compra_a_proveedor_purch__estado__in=estados_activos
        ).distinct()
    
    def get_top_proveedores(self, limit: int = 10) -> QuerySet:
        """Obtiene los proveedores con más órdenes."""
        return self._get_base_queryset().annotate(
            total_ordenes=Count('ordenes_de_compra_a_proveedor_purch')
        ).order_by('-total_ordenes')[:limit]


class FabricanteRepository(BaseRepository[Fabricante]):
    """Repositorio para fabricantes."""
    
    model = Fabricante
    
    def get_by_nombre(self, nombre: str) -> Optional[Fabricante]:
        """Obtiene un fabricante por nombre."""
        try:
            return self._get_base_queryset().get(nombre=nombre)
        except Fabricante.DoesNotExist:
            return None
    
    def search(self, query: str) -> QuerySet[Fabricante]:
        """Busca fabricantes."""
        return self._get_base_queryset().filter(
            Q(nombre__icontains=query) |
            Q(contacto__icontains=query)
        )
    
    def get_con_insumos(self) -> QuerySet:
        """Obtiene fabricantes con conteo de insumos."""
        return self._get_base_queryset().annotate(
            total_insumos=Count('insumos_fabricados_inv')
        ).filter(total_insumos__gt=0)


class OfertaProveedorRepository(BaseRepository[OfertaProveedor]):
    """Repositorio para ofertas de proveedores por insumo."""
    
    model = OfertaProveedor
    
    def get_by_insumo(self, insumo_id: int) -> QuerySet[OfertaProveedor]:
        """Obtiene ofertas para un insumo específico."""
        return self._get_base_queryset().filter(insumo_id=insumo_id)
    
    def get_by_proveedor(self, proveedor_id: int) -> QuerySet[OfertaProveedor]:
        """Obtiene ofertas de un proveedor."""
        return self._get_base_queryset().filter(proveedor_id=proveedor_id)
    
    def get_mejor_oferta(self, insumo_id: int) -> Optional[OfertaProveedor]:
        """Obtiene la mejor oferta (menor precio) para un insumo."""
        return self._get_base_queryset().filter(
            insumo_id=insumo_id
        ).order_by('precio_unitario_compra').first()
    
    def get_ofertas_ordenadas_precio(self, insumo_id: int) -> QuerySet[OfertaProveedor]:
        """Obtiene ofertas de un insumo ordenadas por precio."""
        return self._get_base_queryset().filter(
            insumo_id=insumo_id
        ).order_by('precio_unitario_compra')


class OrdenCompraRepository(BaseRepository[Orden]):
    """Repositorio para órdenes de compra."""
    
    model = Orden
    
    def get_by_numero(self, numero: str) -> Optional[Orden]:
        """Obtiene una orden por número."""
        try:
            return self._get_base_queryset().get(numero_orden=numero)
        except Orden.DoesNotExist:
            return None
    
    def get_by_proveedor(self, proveedor_id: int) -> QuerySet[Orden]:
        """Obtiene órdenes de un proveedor."""
        return self._get_base_queryset().filter(proveedor_id=proveedor_id)
    
    def get_by_estado(self, estado: str) -> QuerySet[Orden]:
        """Obtiene órdenes por estado."""
        return self._get_base_queryset().filter(estado=estado)
    
    def get_by_deposito(self, deposito_id: int) -> QuerySet[Orden]:
        """Obtiene órdenes de un depósito."""
        return self._get_base_queryset().filter(deposito_id=deposito_id)
    
    def get_borradores(self) -> QuerySet[Orden]:
        """Obtiene órdenes en estado borrador."""
        return self._get_base_queryset().filter(estado='BORRADOR')
    
    def get_aprobadas(self) -> QuerySet[Orden]:
        """Obtiene órdenes aprobadas."""
        return self._get_base_queryset().filter(estado='APROBADA')
    
    def get_pendientes_recepcion(self) -> QuerySet[Orden]:
        """Obtiene órdenes pendientes de recepción."""
        estados = ['ENVIADA_PROVEEDOR', 'CONFIRMADA_PROVEEDOR', 'EN_TRANSITO']
        return self._get_base_queryset().filter(estado__in=estados)
    
    def get_completadas(self) -> QuerySet[Orden]:
        """Obtiene órdenes completadas."""
        return self._get_base_queryset().filter(estado='COMPLETADA')
    
    def get_by_fecha_rango(self, fecha_inicio: datetime, fecha_fin: datetime) -> QuerySet[Orden]:
        """Obtiene órdenes en un rango de fechas."""
        return self._get_base_queryset().filter(
            fecha_creacion__gte=fecha_inicio,
            fecha_creacion__lte=fecha_fin
        )
    
    def get_recientes(self, dias: int = 30) -> QuerySet[Orden]:
        """Obtiene órdenes de los últimos N días."""
        fecha_limite = datetime.now() - timedelta(days=dias)
        return self._get_base_queryset().filter(fecha_creacion__gte=fecha_limite)
    
    def get_vencidas(self) -> QuerySet[Orden]:
        """Obtiene órdenes con fecha de entrega estimada vencida."""
        from django.utils import timezone
        hoy = timezone.now().date()
        estados_pendientes = ['APROBADA', 'ENVIADA_PROVEEDOR', 'CONFIRMADA_PROVEEDOR', 'EN_TRANSITO']
        return self._get_base_queryset().filter(
            fecha_estimada_entrega__lt=hoy,
            estado__in=estados_pendientes
        )
    
    def get_by_insumo(self, insumo_id: int) -> QuerySet[Orden]:
        """Obtiene órdenes que incluyen un insumo específico."""
        return self._get_base_queryset().filter(insumo_principal_id=insumo_id)
    
    def generar_numero_orden(self) -> str:
        """Genera un nuevo número de orden de compra."""
        from django.utils import timezone
        year = timezone.now().year
        prefix = f"OC-{year}-"
        
        ultima = self.model.objects.filter(
            numero_orden__startswith=prefix
        ).order_by('-numero_orden').first()
        
        if ultima:
            try:
                ultimo_num = int(ultima.numero_orden.replace(prefix, ''))
                nuevo_num = ultimo_num + 1
            except ValueError:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"{prefix}{nuevo_num:05d}"
    
    def get_total_compras(self, fecha_inicio: datetime = None, fecha_fin: datetime = None) -> dict:
        """Calcula el total de compras en un período."""
        qs = self._get_base_queryset().filter(estado='COMPLETADA')
        
        if fecha_inicio:
            qs = qs.filter(fecha_creacion__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_creacion__lte=fecha_fin)
        
        # Calcular total manualmente ya que es una property
        total = sum(orden.total_orden_compra for orden in qs)
        
        return {
            'total_compras': float(total),
            'cantidad_ordenes': qs.count()
        }
