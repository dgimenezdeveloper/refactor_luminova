"""
Servicios para el módulo de compras.

Contienen la lógica de negocio para gestión de órdenes de compra,
proveedores y evaluación de ofertas.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.base import BaseService, ServiceResult
from apps.purchasing.repositories.purchasing_repository import (
    OrdenCompraRepository,
    ProveedorRepository,
    FabricanteRepository,
    OfertaProveedorRepository,
)


class PurchasingService(BaseService):
    """
    Servicio principal de compras.
    
    Coordina operaciones de órdenes de compra, proveedores y ofertas.
    """
    
    def __init__(self, empresa=None):
        super().__init__(empresa)
        self.orden_repo = OrdenCompraRepository(empresa)
        self.proveedor_repo = ProveedorRepository(empresa)
        self.fabricante_repo = FabricanteRepository(empresa)
        self.oferta_repo = OfertaProveedorRepository(empresa)
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para operaciones de compras."""
        errors = []
        
        if 'cantidad' in data:
            if data['cantidad'] <= 0:
                errors.append("La cantidad debe ser positiva")
        
        if 'precio_unitario' in data:
            if data['precio_unitario'] < 0:
                errors.append("El precio no puede ser negativo")
        
        if errors:
            raise ValidationError(errors)
        
        return data
    
    # ==================== PROVEEDORES ====================
    
    def get_proveedores(self) -> ServiceResult:
        """Obtiene todos los proveedores."""
        try:
            proveedores = self.proveedor_repo.get_all()
            return ServiceResult.ok(data=list(proveedores))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_proveedor(self, proveedor_id: int) -> ServiceResult:
        """Obtiene un proveedor por ID."""
        proveedor = self.proveedor_repo.get_by_id(proveedor_id)
        if not proveedor:
            return ServiceResult.fail(message="Proveedor no encontrado")
        return ServiceResult.ok(data=proveedor)
    
    def crear_proveedor(
        self,
        nombre: str,
        contacto: str = None,
        telefono: str = None,
        email: str = None
    ) -> ServiceResult:
        """Crea un nuevo proveedor."""
        try:
            # Verificar si ya existe
            if self.proveedor_repo.get_by_nombre(nombre):
                return ServiceResult.fail(message="Ya existe un proveedor con ese nombre")
            
            proveedor = self.proveedor_repo.create(
                nombre=nombre,
                contacto=contacto or '',
                telefono=telefono or '',
                email=email or ''
            )
            
            return ServiceResult.ok(data=proveedor, message="Proveedor creado correctamente")
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def search_proveedores(self, query: str) -> ServiceResult:
        """Busca proveedores."""
        try:
            proveedores = self.proveedor_repo.search(query)
            return ServiceResult.ok(data=list(proveedores))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== FABRICANTES ====================
    
    def get_fabricantes(self) -> ServiceResult:
        """Obtiene todos los fabricantes."""
        try:
            fabricantes = self.fabricante_repo.get_all()
            return ServiceResult.ok(data=list(fabricantes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_fabricante(self, fabricante_id: int) -> ServiceResult:
        """Obtiene un fabricante por ID."""
        fabricante = self.fabricante_repo.get_by_id(fabricante_id)
        if not fabricante:
            return ServiceResult.fail(message="Fabricante no encontrado")
        return ServiceResult.ok(data=fabricante)
    
    # ==================== OFERTAS ====================
    
    def get_ofertas_insumo(self, insumo_id: int) -> ServiceResult:
        """Obtiene todas las ofertas para un insumo."""
        try:
            ofertas = self.oferta_repo.get_ofertas_ordenadas_precio(insumo_id)
            return ServiceResult.ok(data=list(ofertas))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_mejor_oferta(self, insumo_id: int) -> ServiceResult:
        """Obtiene la mejor oferta (menor precio) para un insumo."""
        try:
            oferta = self.oferta_repo.get_mejor_oferta(insumo_id)
            if not oferta:
                return ServiceResult.fail(message="No hay ofertas para este insumo")
            return ServiceResult.ok(data=oferta)
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    @transaction.atomic
    def registrar_oferta(
        self,
        insumo_id: int,
        proveedor_id: int,
        precio_unitario: Decimal,
        tiempo_entrega_dias: int = 0
    ) -> ServiceResult:
        """
        Registra o actualiza una oferta de proveedor para un insumo.
        """
        try:
            from App_LUMINOVA.models import Insumo, OfertaProveedor
            
            # Verificar insumo y proveedor
            try:
                insumo = Insumo.objects.get(pk=insumo_id)
            except Insumo.DoesNotExist:
                return ServiceResult.fail(message="Insumo no encontrado")
            
            proveedor = self.proveedor_repo.get_by_id(proveedor_id)
            if not proveedor:
                return ServiceResult.fail(message="Proveedor no encontrado")
            
            # Crear o actualizar oferta
            oferta, created = OfertaProveedor.objects.update_or_create(
                insumo=insumo,
                proveedor=proveedor,
                defaults={
                    'precio_unitario_compra': precio_unitario,
                    'tiempo_entrega_estimado_dias': tiempo_entrega_dias,
                    'fecha_actualizacion_precio': timezone.now(),
                    'empresa': self.empresa
                }
            )
            
            action = "registrada" if created else "actualizada"
            return ServiceResult.ok(
                data=oferta,
                message=f"Oferta {action} correctamente"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== ÓRDENES DE COMPRA ====================
    
    def get_ordenes(self, estado: str = None) -> ServiceResult:
        """Obtiene órdenes de compra, opcionalmente filtradas por estado."""
        try:
            if estado:
                ordenes = self.orden_repo.get_by_estado(estado)
            else:
                ordenes = self.orden_repo.get_all()
            
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_orden(self, orden_id: int) -> ServiceResult:
        """Obtiene una orden de compra por ID."""
        orden = self.orden_repo.get_by_id(orden_id)
        if not orden:
            return ServiceResult.fail(message="Orden de compra no encontrada")
        return ServiceResult.ok(data=orden)
    
    def get_orden_by_numero(self, numero: str) -> ServiceResult:
        """Obtiene una orden por su número."""
        orden = self.orden_repo.get_by_numero(numero)
        if not orden:
            return ServiceResult.fail(message="Orden de compra no encontrada")
        return ServiceResult.ok(data=orden)
    
    @transaction.atomic
    def crear_orden_compra(
        self,
        proveedor_id: int,
        insumo_id: int,
        cantidad: int,
        precio_unitario: Decimal = None,
        deposito_id: int = None,
        fecha_estimada_entrega=None,
        notas: str = None
    ) -> ServiceResult:
        """
        Crea una nueva orden de compra.
        
        Args:
            proveedor_id: ID del proveedor
            insumo_id: ID del insumo principal
            cantidad: Cantidad a comprar
            precio_unitario: Precio unitario (si no se especifica, usa la oferta del proveedor)
            deposito_id: ID del depósito que solicita
            fecha_estimada_entrega: Fecha estimada de entrega
            notas: Notas adicionales
        """
        try:
            # Verificar proveedor
            proveedor = self.proveedor_repo.get_by_id(proveedor_id)
            if not proveedor:
                return ServiceResult.fail(message="Proveedor no encontrado")
            
            # Verificar insumo
            from App_LUMINOVA.models import Insumo
            try:
                insumo = Insumo.objects.get(pk=insumo_id)
            except Insumo.DoesNotExist:
                return ServiceResult.fail(message="Insumo no encontrado")
            
            # Obtener precio de la oferta si no se especifica
            if precio_unitario is None:
                oferta = self.oferta_repo.get_by_insumo(insumo_id).filter(
                    proveedor_id=proveedor_id
                ).first()
                if oferta:
                    precio_unitario = oferta.precio_unitario_compra
                else:
                    return ServiceResult.fail(
                        message="No hay oferta registrada para este proveedor e insumo. Especifique el precio."
                    )
            
            # Generar número de orden
            numero_orden = self.orden_repo.generar_numero_orden()
            
            # Crear orden
            datos_orden = {
                'numero_orden': numero_orden,
                'proveedor': proveedor,
                'insumo_principal': insumo,
                'cantidad_principal': cantidad,
                'precio_unitario_compra': precio_unitario,
                'estado': 'BORRADOR',
                'notas': notas or ''
            }
            
            if deposito_id:
                from App_LUMINOVA.models import Deposito
                datos_orden['deposito'] = Deposito.objects.get(pk=deposito_id)
            
            if fecha_estimada_entrega:
                datos_orden['fecha_estimada_entrega'] = fecha_estimada_entrega
            
            orden = self.orden_repo.create(**datos_orden)
            
            return ServiceResult.ok(
                data=orden,
                message=f"Orden de compra {numero_orden} creada correctamente"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)], message="Error al crear orden de compra")
    
    @transaction.atomic
    def cambiar_estado_orden(
        self,
        orden_id: int,
        nuevo_estado: str,
        usuario=None,
        notas: str = None
    ) -> ServiceResult:
        """
        Cambia el estado de una orden de compra.
        """
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden no encontrada")
            
            # Validar estado
            estados_validos = dict(orden.ESTADO_ORDEN_COMPRA_CHOICES).keys()
            if nuevo_estado not in estados_validos:
                return ServiceResult.fail(message=f"Estado '{nuevo_estado}' no válido")
            
            estado_anterior = orden.estado
            
            # Actualizar estado
            self.orden_repo.update(orden, estado=nuevo_estado)
            
            if notas:
                notas_actualizadas = f"{orden.notas}\n[{timezone.now().strftime('%d/%m/%Y %H:%M')}] Estado: {nuevo_estado}. {notas}"
                self.orden_repo.update(orden, notas=notas_actualizadas)
            
            return ServiceResult.ok(
                data=orden,
                message=f"Estado actualizado de '{estado_anterior}' a '{nuevo_estado}'"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def aprobar_orden(self, orden_id: int, usuario=None) -> ServiceResult:
        """Aprueba una orden de compra."""
        return self.cambiar_estado_orden(orden_id, 'APROBADA', usuario)
    
    def enviar_a_proveedor(self, orden_id: int, usuario=None) -> ServiceResult:
        """Marca la orden como enviada al proveedor."""
        return self.cambiar_estado_orden(orden_id, 'ENVIADA_PROVEEDOR', usuario)
    
    def confirmar_proveedor(self, orden_id: int, usuario=None) -> ServiceResult:
        """Marca la orden como confirmada por el proveedor."""
        return self.cambiar_estado_orden(orden_id, 'CONFIRMADA_PROVEEDOR', usuario)
    
    def marcar_en_transito(self, orden_id: int, numero_tracking: str = None, usuario=None) -> ServiceResult:
        """Marca la orden como en tránsito."""
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden no encontrada")
            
            if numero_tracking:
                self.orden_repo.update(orden, numero_tracking=numero_tracking)
            
            return self.cambiar_estado_orden(orden_id, 'EN_TRANSITO', usuario)
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    @transaction.atomic
    def recibir_orden(
        self,
        orden_id: int,
        cantidad_recibida: int = None,
        usuario=None
    ) -> ServiceResult:
        """
        Registra la recepción de una orden de compra.
        
        Args:
            orden_id: ID de la orden
            cantidad_recibida: Cantidad efectivamente recibida (si es parcial)
            usuario: Usuario que recibe
        """
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden no encontrada")
            
            cantidad_esperada = orden.cantidad_principal
            cantidad_recibida = cantidad_recibida or cantidad_esperada
            
            # Determinar estado
            if cantidad_recibida >= cantidad_esperada:
                nuevo_estado = 'RECIBIDA_TOTAL'
            else:
                nuevo_estado = 'RECIBIDA_PARCIAL'
            
            # Actualizar stock del insumo
            if orden.insumo_principal and orden.deposito:
                from apps.inventory.services.inventory_service import InventoryService
                inv_service = InventoryService(self.empresa)
                
                result = inv_service.ajustar_stock_insumo(
                    insumo_id=orden.insumo_principal_id,
                    deposito_id=orden.deposito_id,
                    cantidad=cantidad_recibida,
                    tipo='entrada',
                    usuario=usuario,
                    motivo=f"Recepción OC {orden.numero_orden}"
                )
                
                if not result.success:
                    return result
            
            # Cambiar estado
            return self.cambiar_estado_orden(
                orden_id, 
                nuevo_estado, 
                usuario,
                f"Recibidas {cantidad_recibida} de {cantidad_esperada} unidades"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def completar_orden(self, orden_id: int, usuario=None) -> ServiceResult:
        """Marca la orden como completada."""
        return self.cambiar_estado_orden(orden_id, 'COMPLETADA', usuario)
    
    def cancelar_orden(self, orden_id: int, usuario=None, motivo: str = None) -> ServiceResult:
        """Cancela una orden de compra."""
        return self.cambiar_estado_orden(orden_id, 'CANCELADA', usuario, motivo)
    
    def get_ordenes_pendientes(self) -> ServiceResult:
        """Obtiene órdenes pendientes de aprobar."""
        try:
            ordenes = self.orden_repo.get_borradores()
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_ordenes_pendientes_recepcion(self) -> ServiceResult:
        """Obtiene órdenes pendientes de recibir."""
        try:
            ordenes = self.orden_repo.get_pendientes_recepcion()
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
    
    # ==================== REPORTES ====================
    
    def get_resumen_compras(self, dias: int = 30) -> ServiceResult:
        """
        Genera un resumen de compras del período.
        """
        try:
            ordenes = self.orden_repo.get_recientes(dias)
            
            resumen = {
                'total_ordenes': ordenes.count(),
                'ordenes_borrador': ordenes.filter(estado='BORRADOR').count(),
                'ordenes_aprobadas': ordenes.filter(estado='APROBADA').count(),
                'ordenes_en_transito': ordenes.filter(estado='EN_TRANSITO').count(),
                'ordenes_recibidas': ordenes.filter(estado__in=['RECIBIDA_TOTAL', 'RECIBIDA_PARCIAL']).count(),
                'ordenes_completadas': ordenes.filter(estado='COMPLETADA').count(),
                'ordenes_vencidas': self.orden_repo.get_vencidas().count(),
            }
            
            # Calcular totales
            from datetime import datetime, timedelta
            fecha_limite = datetime.now() - timedelta(days=dias)
            totales = self.orden_repo.get_total_compras(fecha_limite)
            resumen.update(totales)
            
            return ServiceResult.ok(data=resumen)
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_insumos_mas_comprados(self, limit: int = 10, dias: int = 30) -> ServiceResult:
        """Obtiene los insumos más comprados en el período."""
        try:
            from django.db.models import Sum, Count
            from datetime import datetime, timedelta
            from App_LUMINOVA.models import Orden
            
            fecha_limite = datetime.now() - timedelta(days=dias)
            
            insumos = Orden.objects.filter(
                fecha_creacion__gte=fecha_limite,
                estado='COMPLETADA',
                insumo_principal__isnull=False
            )
            
            if self.empresa:
                insumos = insumos.filter(empresa=self.empresa)
            
            insumos = insumos.values(
                'insumo_principal__id',
                'insumo_principal__descripcion'
            ).annotate(
                total_cantidad=Sum('cantidad_principal'),
                veces_comprado=Count('id')
            ).order_by('-total_cantidad')[:limit]
            
            return ServiceResult.ok(data=list(insumos))
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
