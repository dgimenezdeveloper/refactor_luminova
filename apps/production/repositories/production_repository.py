"""
Repositorios para el módulo de producción.

Proporcionan una capa de abstracción para órdenes de producción,
estados, sectores y reportes de incidencias.
"""

from typing import List, Optional
from django.db.models import QuerySet, Sum, Q, Count
from datetime import datetime, timedelta

from apps.core.base import BaseRepository

# Importamos modelos desde las nuevas apps modulares
from apps.production.models import (
    OrdenProduccion,
    EstadoOrden,
    SectorAsignado,
    Reportes,
    LoteProductoTerminado,
)


class EstadoOrdenRepository(BaseRepository[EstadoOrden]):
    """Repositorio para estados de órdenes de producción."""
    
    model = EstadoOrden
    
    def get_by_nombre(self, nombre: str) -> Optional[EstadoOrden]:
        """Obtiene un estado por nombre."""
        try:
            qs = self._get_base_queryset()
            # También incluir estados compartidos (empresa=null)
            return self.model.objects.filter(
                Q(empresa=self.empresa) | Q(empresa__isnull=True),
                nombre=nombre
            ).first()
        except EstadoOrden.DoesNotExist:
            return None
    
    def get_or_create_estado(self, nombre: str) -> EstadoOrden:
        """Obtiene o crea un estado."""
        estado = self.get_by_nombre(nombre)
        if not estado:
            estado = self.create(nombre=nombre)
        return estado


class SectorAsignadoRepository(BaseRepository[SectorAsignado]):
    """Repositorio para sectores de producción."""
    
    model = SectorAsignado
    
    def get_by_nombre(self, nombre: str) -> Optional[SectorAsignado]:
        """Obtiene un sector por nombre."""
        try:
            return self.model.objects.filter(
                Q(empresa=self.empresa) | Q(empresa__isnull=True),
                nombre=nombre
            ).first()
        except SectorAsignado.DoesNotExist:
            return None
    
    def get_con_ops_activas(self) -> QuerySet:
        """Obtiene sectores con órdenes de producción activas."""
        return self._get_base_queryset().annotate(
            ops_activas=Count('ops_sector', filter=Q(
                ops_sector__estado_op__nombre__in=['Pendiente', 'En Proceso', 'Planificada']
            ))
        ).filter(ops_activas__gt=0)


class OrdenProduccionRepository(BaseRepository[OrdenProduccion]):
    """Repositorio para órdenes de producción."""
    
    model = OrdenProduccion
    
    def get_by_numero(self, numero_op: str) -> Optional[OrdenProduccion]:
        """Obtiene una orden por su número."""
        try:
            return self._get_base_queryset().get(numero_op=numero_op)
        except OrdenProduccion.DoesNotExist:
            return None
    
    def get_by_producto(self, producto_id: int) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes para un producto específico."""
        return self._get_base_queryset().filter(producto_a_producir_id=producto_id)
    
    def get_by_estado(self, estado_nombre: str) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes por nombre de estado."""
        return self._get_base_queryset().filter(estado_op__nombre=estado_nombre)
    
    def get_by_orden_venta(self, orden_venta_id: int) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes de producción generadas desde una orden de venta."""
        return self._get_base_queryset().filter(orden_venta_origen_id=orden_venta_id)
    
    def get_by_sector(self, sector_id: int) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes asignadas a un sector."""
        return self._get_base_queryset().filter(sector_asignado_op_id=sector_id)
    
    def get_pendientes(self) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes pendientes de procesar."""
        return self._get_base_queryset().filter(
            estado_op__nombre__in=['Pendiente', 'Planificada']
        )
    
    def get_en_proceso(self) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes en proceso de producción."""
        return self._get_base_queryset().filter(
            estado_op__nombre__in=['En Proceso', 'Producción Iniciada', 'Insumos Recibidos']
        )
    
    def get_completadas(self) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes completadas."""
        return self._get_base_queryset().filter(estado_op__nombre='Completada')
    
    def get_para_stock(self) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes de producción para stock (MTS)."""
        return self._get_base_queryset().filter(tipo_orden='MTS')
    
    def get_bajo_demanda(self) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes bajo demanda (MTO)."""
        return self._get_base_queryset().filter(tipo_orden='MTO')
    
    def get_by_fecha_rango(self, fecha_inicio: datetime, fecha_fin: datetime) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes en un rango de fechas."""
        return self._get_base_queryset().filter(
            fecha_solicitud__gte=fecha_inicio,
            fecha_solicitud__lte=fecha_fin
        )
    
    def get_vencidas(self) -> QuerySet[OrdenProduccion]:
        """Obtiene órdenes con fecha de fin planificada vencida."""
        from django.utils import timezone
        hoy = timezone.now().date()
        return self._get_base_queryset().filter(
            fecha_fin_planificada__lt=hoy,
            estado_op__nombre__in=['Pendiente', 'En Proceso', 'Planificada']
        )
    
    def get_with_reportes(self, orden_id: int) -> Optional[OrdenProduccion]:
        """Obtiene una orden con sus reportes precargados."""
        try:
            return self._get_base_queryset().prefetch_related(
                'reportes_incidencia'
            ).get(pk=orden_id)
        except OrdenProduccion.DoesNotExist:
            return None
    
    def generar_numero_op(self) -> str:
        """Genera un nuevo número de orden de producción."""
        from django.utils import timezone
        year = timezone.now().year
        prefix = f"OP-{year}-"
        
        ultima = self.model.objects.filter(
            numero_op__startswith=prefix
        ).order_by('-numero_op').first()
        
        if ultima:
            try:
                ultimo_num = int(ultima.numero_op.replace(prefix, ''))
                nuevo_num = ultimo_num + 1
            except ValueError:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"{prefix}{nuevo_num:05d}"


class ReportesRepository(BaseRepository[Reportes]):
    """Repositorio para reportes de incidencias."""
    
    model = Reportes
    
    def get_by_numero(self, n_reporte: str) -> Optional[Reportes]:
        """Obtiene un reporte por número."""
        try:
            return self._get_base_queryset().get(n_reporte=n_reporte)
        except Reportes.DoesNotExist:
            return None
    
    def get_by_orden_produccion(self, orden_id: int) -> QuerySet[Reportes]:
        """Obtiene reportes de una orden de producción."""
        return self._get_base_queryset().filter(orden_produccion_asociada_id=orden_id)
    
    def get_pendientes(self) -> QuerySet[Reportes]:
        """Obtiene reportes no resueltos."""
        return self._get_base_queryset().filter(resuelto=False)
    
    def get_resueltos(self) -> QuerySet[Reportes]:
        """Obtiene reportes resueltos."""
        return self._get_base_queryset().filter(resuelto=True)
    
    def get_by_sector(self, sector_id: int) -> QuerySet[Reportes]:
        """Obtiene reportes originados en un sector."""
        return self._get_base_queryset().filter(sector_reporta_id=sector_id)
    
    def get_by_tipo_problema(self, tipo: str) -> QuerySet[Reportes]:
        """Obtiene reportes por tipo de problema."""
        return self._get_base_queryset().filter(tipo_problema__icontains=tipo)
    
    def generar_numero_reporte(self) -> str:
        """Genera un nuevo número de reporte."""
        from django.utils import timezone
        year = timezone.now().year
        prefix = f"REP-{year}-"
        
        ultimo = self.model.objects.filter(
            n_reporte__startswith=prefix
        ).order_by('-n_reporte').first()
        
        if ultimo:
            try:
                ultimo_num = int(ultimo.n_reporte.replace(prefix, ''))
                nuevo_num = ultimo_num + 1
            except ValueError:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"{prefix}{nuevo_num:05d}"


class LoteProductoRepository(BaseRepository[LoteProductoTerminado]):
    """Repositorio para lotes de productos terminados."""
    
    model = LoteProductoTerminado
    
    def get_by_orden_produccion(self, orden_id: int) -> QuerySet[LoteProductoTerminado]:
        """Obtiene lotes generados por una orden de producción."""
        return self._get_base_queryset().filter(op_asociada_id=orden_id)
    
    def get_by_producto(self, producto_id: int) -> QuerySet[LoteProductoTerminado]:
        """Obtiene lotes de un producto específico."""
        return self._get_base_queryset().filter(producto_id=producto_id)
    
    def get_pendientes_envio(self) -> QuerySet[LoteProductoTerminado]:
        """Obtiene lotes pendientes de envío."""
        return self._get_base_queryset().filter(enviado=False)
    
    def get_by_deposito(self, deposito_id: int) -> QuerySet[LoteProductoTerminado]:
        """Obtiene lotes en un depósito."""
        return self._get_base_queryset().filter(deposito_id=deposito_id)
