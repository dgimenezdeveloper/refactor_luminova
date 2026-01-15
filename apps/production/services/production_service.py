"""
Servicios para el módulo de producción.

Contienen la lógica de negocio para gestión de órdenes de producción,
reportes de incidencias y control de lotes.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.base import BaseService, ServiceResult
from apps.production.repositories.production_repository import (
    OrdenProduccionRepository,
    EstadoOrdenRepository,
    SectorAsignadoRepository,
    ReportesRepository,
    LoteProductoRepository,
)


class ProductionService(BaseService):
    """
    Servicio principal de producción.
    
    Coordina operaciones de órdenes de producción, reportes y lotes.
    """
    
    def __init__(self, empresa=None):
        super().__init__(empresa)
        self.orden_repo = OrdenProduccionRepository(empresa)
        self.estado_repo = EstadoOrdenRepository(empresa)
        self.sector_repo = SectorAsignadoRepository(empresa)
        self.reporte_repo = ReportesRepository(empresa)
        self.lote_repo = LoteProductoRepository(empresa)
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para operaciones de producción."""
        errors = []
        
        if 'cantidad_a_producir' in data:
            if data['cantidad_a_producir'] <= 0:
                errors.append("La cantidad a producir debe ser positiva")
        
        if 'tipo_orden' in data:
            if data['tipo_orden'] not in ['MTO', 'MTS']:
                errors.append("Tipo de orden inválido. Use 'MTO' o 'MTS'")
        
        if errors:
            raise ValidationError(errors)
        
        return data
    
    # ==================== ÓRDENES DE PRODUCCIÓN ====================
    
    def get_ordenes(self, estado: str = None) -> ServiceResult:
        """Obtiene órdenes de producción, opcionalmente filtradas por estado."""
        try:
            if estado:
                ordenes = self.orden_repo.get_by_estado(estado)
            else:
                ordenes = self.orden_repo.get_all()
            
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_orden(self, orden_id: int) -> ServiceResult:
        """Obtiene una orden de producción con sus reportes."""
        orden = self.orden_repo.get_with_reportes(orden_id)
        if not orden:
            return ServiceResult.fail(message="Orden de producción no encontrada")
        return ServiceResult.ok(data=orden)
    
    def get_orden_by_numero(self, numero_op: str) -> ServiceResult:
        """Obtiene una orden por su número."""
        orden = self.orden_repo.get_by_numero(numero_op)
        if not orden:
            return ServiceResult.fail(message="Orden de producción no encontrada")
        return ServiceResult.ok(data=orden)
    
    @transaction.atomic
    def crear_orden_produccion(
        self,
        producto_id: int,
        cantidad: int,
        tipo_orden: str = 'MTO',
        orden_venta_id: int = None,
        sector_id: int = None,
        fecha_inicio_planificada=None,
        fecha_fin_planificada=None,
        notas: str = None,
        usuario=None
    ) -> ServiceResult:
        """
        Crea una nueva orden de producción.
        
        Args:
            producto_id: ID del producto a producir
            cantidad: Cantidad a producir
            tipo_orden: 'MTO' (Make to Order) o 'MTS' (Make to Stock)
            orden_venta_id: ID de la orden de venta origen (requerido para MTO)
            sector_id: ID del sector asignado
            fecha_inicio_planificada: Fecha de inicio planificada
            fecha_fin_planificada: Fecha de fin planificada
            notas: Notas adicionales
            usuario: Usuario que crea la orden
        """
        try:
            # Validaciones
            if tipo_orden == 'MTO' and not orden_venta_id:
                return ServiceResult.fail(
                    message="Las órdenes MTO requieren una orden de venta origen"
                )
            
            if cantidad <= 0:
                return ServiceResult.fail(message="La cantidad debe ser positiva")
            
            # Verificar producto
            from App_LUMINOVA.models import ProductoTerminado
            try:
                producto = ProductoTerminado.objects.get(pk=producto_id)
            except ProductoTerminado.DoesNotExist:
                return ServiceResult.fail(message="Producto no encontrado")
            
            # Obtener o crear estado inicial
            estado_inicial = self.estado_repo.get_or_create_estado('Pendiente')
            
            # Generar número de orden
            numero_op = self.orden_repo.generar_numero_op()
            
            # Preparar datos
            datos_orden = {
                'numero_op': numero_op,
                'producto_a_producir': producto,
                'cantidad_a_producir': cantidad,
                'tipo_orden': tipo_orden,
                'estado_op': estado_inicial,
                'notas': notas or ''
            }
            
            if orden_venta_id:
                from App_LUMINOVA.models import OrdenVenta
                datos_orden['orden_venta_origen'] = OrdenVenta.objects.get(pk=orden_venta_id)
            
            if sector_id:
                sector = self.sector_repo.get_by_id(sector_id)
                datos_orden['sector_asignado_op'] = sector
            
            if fecha_inicio_planificada:
                datos_orden['fecha_inicio_planificada'] = fecha_inicio_planificada
            
            if fecha_fin_planificada:
                datos_orden['fecha_fin_planificada'] = fecha_fin_planificada
            
            # Crear orden
            orden = self.orden_repo.create(**datos_orden)
            
            return ServiceResult.ok(
                data=orden,
                message=f"Orden de producción {numero_op} creada correctamente"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)], message="Error al crear orden de producción")
    
    @transaction.atomic
    def cambiar_estado_orden(
        self,
        orden_id: int,
        nuevo_estado: str,
        usuario=None,
        notas: str = None
    ) -> ServiceResult:
        """
        Cambia el estado de una orden de producción.
        """
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden no encontrada")
            
            # Obtener o crear estado
            estado = self.estado_repo.get_or_create_estado(nuevo_estado)
            
            estado_anterior = orden.estado_op.nombre if orden.estado_op else 'Sin Estado'
            
            # Actualizar
            self.orden_repo.update(orden, estado_op=estado)
            
            # Si se completa, registrar fecha de fin
            if nuevo_estado == 'Completada' and not orden.fecha_fin_real:
                self.orden_repo.update(orden, fecha_fin_real=timezone.now())
            
            # Si inicia, registrar fecha de inicio
            if nuevo_estado in ['En Proceso', 'Producción Iniciada'] and not orden.fecha_inicio_real:
                self.orden_repo.update(orden, fecha_inicio_real=timezone.now())
            
            # Actualizar estado de la OV si es MTO
            if orden.orden_venta_origen:
                orden.orden_venta_origen.actualizar_estado_por_ops()
            
            return ServiceResult.ok(
                data=orden,
                message=f"Estado actualizado de '{estado_anterior}' a '{nuevo_estado}'"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def iniciar_produccion(self, orden_id: int, usuario=None) -> ServiceResult:
        """Inicia la producción de una orden."""
        return self.cambiar_estado_orden(orden_id, 'En Proceso', usuario)
    
    def completar_produccion(self, orden_id: int, usuario=None) -> ServiceResult:
        """Marca una orden como completada."""
        return self.cambiar_estado_orden(orden_id, 'Completada', usuario)
    
    def cancelar_orden(self, orden_id: int, usuario=None, motivo: str = None) -> ServiceResult:
        """Cancela una orden de producción."""
        return self.cambiar_estado_orden(orden_id, 'Cancelada', usuario, motivo)
    
    def asignar_sector(self, orden_id: int, sector_id: int) -> ServiceResult:
        """Asigna un sector a una orden de producción."""
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden no encontrada")
            
            sector = self.sector_repo.get_by_id(sector_id)
            if not sector:
                return ServiceResult.fail(message="Sector no encontrado")
            
            self.orden_repo.update(orden, sector_asignado_op=sector)
            
            return ServiceResult.ok(
                data=orden,
                message=f"Sector '{sector.nombre}' asignado a la orden"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_ordenes_pendientes(self) -> ServiceResult:
        """Obtiene órdenes pendientes de procesar."""
        try:
            ordenes = self.orden_repo.get_pendientes()
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_ordenes_en_proceso(self) -> ServiceResult:
        """Obtiene órdenes en proceso de producción."""
        try:
            ordenes = self.orden_repo.get_en_proceso()
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_ordenes_vencidas(self) -> ServiceResult:
        """Obtiene órdenes con fecha de entrega vencida."""
        try:
            ordenes = self.orden_repo.get_vencidas()
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== REPORTES DE INCIDENCIAS ====================
    
    @transaction.atomic
    def crear_reporte(
        self,
        orden_id: int,
        tipo_problema: str,
        informe: str,
        sector_id: int = None,
        usuario=None
    ) -> ServiceResult:
        """
        Crea un reporte de incidencia para una orden de producción.
        """
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden de producción no encontrada")
            
            # Generar número de reporte
            numero_reporte = self.reporte_repo.generar_numero_reporte()
            
            datos_reporte = {
                'n_reporte': numero_reporte,
                'orden_produccion_asociada': orden,
                'tipo_problema': tipo_problema,
                'informe_reporte': informe,
                'reportado_por': usuario,
            }
            
            if sector_id:
                sector = self.sector_repo.get_by_id(sector_id)
                datos_reporte['sector_reporta'] = sector
            
            reporte = self.reporte_repo.create(**datos_reporte)
            
            # Cambiar estado de la orden si no tiene problemas ya registrados
            if orden.estado_op and orden.estado_op.nombre not in ['Cancelada', 'Completada']:
                # Opcionalmente cambiar estado a "Con Problemas"
                pass
            
            return ServiceResult.ok(
                data=reporte,
                message=f"Reporte {numero_reporte} creado correctamente"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    @transaction.atomic
    def resolver_reporte(
        self,
        reporte_id: int,
        usuario=None
    ) -> ServiceResult:
        """Marca un reporte como resuelto."""
        try:
            reporte = self.reporte_repo.get_by_id(reporte_id)
            if not reporte:
                return ServiceResult.fail(message="Reporte no encontrado")
            
            if reporte.resuelto:
                return ServiceResult.fail(message="El reporte ya está resuelto")
            
            self.reporte_repo.update(
                reporte,
                resuelto=True,
                fecha_resolucion=timezone.now()
            )
            
            return ServiceResult.ok(
                data=reporte,
                message="Reporte marcado como resuelto"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_reportes_pendientes(self) -> ServiceResult:
        """Obtiene reportes sin resolver."""
        try:
            reportes = self.reporte_repo.get_pendientes()
            return ServiceResult.ok(data=list(reportes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_reportes_orden(self, orden_id: int) -> ServiceResult:
        """Obtiene los reportes de una orden específica."""
        try:
            reportes = self.reporte_repo.get_by_orden_produccion(orden_id)
            return ServiceResult.ok(data=list(reportes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== LOTES ====================
    
    @transaction.atomic
    def registrar_lote_producido(
        self,
        orden_id: int,
        cantidad: int,
        deposito_id: int = None
    ) -> ServiceResult:
        """
        Registra un lote producido de una orden de producción.
        """
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden de producción no encontrada")
            
            # Usar depósito del producto si no se especifica
            if not deposito_id and orden.producto_a_producir.deposito:
                deposito_id = orden.producto_a_producir.deposito_id
            
            lote = self.lote_repo.create(
                producto=orden.producto_a_producir,
                op_asociada=orden,
                cantidad=cantidad,
                deposito_id=deposito_id
            )
            
            return ServiceResult.ok(
                data=lote,
                message=f"Lote de {cantidad} unidades registrado"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_lotes_orden(self, orden_id: int) -> ServiceResult:
        """Obtiene lotes generados por una orden."""
        try:
            lotes = self.lote_repo.get_by_orden_produccion(orden_id)
            return ServiceResult.ok(data=list(lotes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== REPORTES ====================
    
    def get_resumen_produccion(self, dias: int = 30) -> ServiceResult:
        """
        Genera un resumen de producción del período.
        """
        try:
            from datetime import datetime, timedelta
            fecha_limite = datetime.now() - timedelta(days=dias)
            
            ordenes = self.orden_repo.get_by_fecha_rango(
                fecha_limite, datetime.now()
            )
            
            resumen = {
                'total_ordenes': ordenes.count(),
                'ordenes_pendientes': self.orden_repo.get_pendientes().count(),
                'ordenes_en_proceso': self.orden_repo.get_en_proceso().count(),
                'ordenes_completadas': self.orden_repo.get_completadas().filter(
                    fecha_solicitud__gte=fecha_limite
                ).count(),
                'ordenes_vencidas': self.orden_repo.get_vencidas().count(),
                'reportes_pendientes': self.reporte_repo.get_pendientes().count(),
                'ordenes_mto': ordenes.filter(tipo_orden='MTO').count(),
                'ordenes_mts': ordenes.filter(tipo_orden='MTS').count(),
            }
            
            return ServiceResult.ok(data=resumen)
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_sectores_con_carga(self) -> ServiceResult:
        """Obtiene sectores con su carga de trabajo actual."""
        try:
            sectores = self.sector_repo.get_con_ops_activas()
            return ServiceResult.ok(data=list(sectores))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
