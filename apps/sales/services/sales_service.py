"""
Servicios para el módulo de ventas.

Contienen la lógica de negocio para gestión de órdenes de venta,
clientes y facturación.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.base import BaseService, ServiceResult
from apps.sales.repositories.sales_repository import (
    ClienteRepository,
    OrdenVentaRepository,
    ItemOrdenVentaRepository,
    FacturaRepository,
    HistorialOVRepository,
)


class SalesService(BaseService):
    """
    Servicio principal de ventas.
    
    Coordina operaciones de órdenes de venta, clientes y facturación.
    """
    
    def __init__(self, empresa=None):
        super().__init__(empresa)
        self.cliente_repo = ClienteRepository(empresa)
        self.orden_repo = OrdenVentaRepository(empresa)
        self.item_repo = ItemOrdenVentaRepository(empresa)
        self.factura_repo = FacturaRepository(empresa)
        self.historial_repo = HistorialOVRepository(empresa)
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para operaciones de ventas."""
        errors = []
        
        if 'items' in data:
            if not data['items']:
                errors.append("La orden debe tener al menos un item")
            
            for item in data['items']:
                if item.get('cantidad', 0) <= 0:
                    errors.append("La cantidad de cada item debe ser positiva")
                if item.get('precio_unitario', 0) < 0:
                    errors.append("El precio no puede ser negativo")
        
        if errors:
            raise ValidationError(errors)
        
        return data
    
    # ==================== CLIENTES ====================
    
    def get_clientes(self) -> ServiceResult:
        """Obtiene todos los clientes."""
        try:
            clientes = self.cliente_repo.get_all()
            return ServiceResult.ok(data=list(clientes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_cliente(self, cliente_id: int) -> ServiceResult:
        """Obtiene un cliente por ID."""
        cliente = self.cliente_repo.get_by_id(cliente_id)
        if not cliente:
            return ServiceResult.fail(message="Cliente no encontrado")
        return ServiceResult.ok(data=cliente)
    
    def crear_cliente(self, nombre: str, email: str = None, telefono: str = None, direccion: str = None) -> ServiceResult:
        """Crea un nuevo cliente."""
        try:
            # Verificar si ya existe
            if email and self.cliente_repo.get_by_email(email):
                return ServiceResult.fail(message="Ya existe un cliente con ese email")
            
            cliente = self.cliente_repo.create(
                nombre=nombre,
                email=email or '',
                telefono=telefono or '',
                direccion=direccion or ''
            )
            
            return ServiceResult.ok(data=cliente, message="Cliente creado correctamente")
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def search_clientes(self, query: str) -> ServiceResult:
        """Busca clientes."""
        try:
            clientes = self.cliente_repo.search(query)
            return ServiceResult.ok(data=list(clientes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== ÓRDENES DE VENTA ====================
    
    def get_ordenes(self, estado: str = None) -> ServiceResult:
        """Obtiene órdenes de venta, opcionalmente filtradas por estado."""
        try:
            if estado:
                ordenes = self.orden_repo.get_by_estado(estado)
            else:
                ordenes = self.orden_repo.get_all()
            
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_orden(self, orden_id: int) -> ServiceResult:
        """Obtiene una orden de venta con sus items."""
        orden = self.orden_repo.get_with_items(orden_id)
        if not orden:
            return ServiceResult.fail(message="Orden de venta no encontrada")
        return ServiceResult.ok(data=orden)
    
    def get_orden_by_numero(self, numero_ov: str) -> ServiceResult:
        """Obtiene una orden por su número."""
        orden = self.orden_repo.get_by_numero(numero_ov)
        if not orden:
            return ServiceResult.fail(message="Orden de venta no encontrada")
        return ServiceResult.ok(data=orden)
    
    @transaction.atomic
    def crear_orden_venta(
        self,
        cliente_id: int,
        items: List[Dict[str, Any]],
        notas: str = None,
        usuario=None
    ) -> ServiceResult:
        """
        Crea una nueva orden de venta.
        
        Args:
            cliente_id: ID del cliente
            items: Lista de items [{producto_terminado_id, cantidad, precio_unitario}]
            notas: Notas adicionales
            usuario: Usuario que crea la orden
        """
        try:
            # Validar cliente
            cliente = self.cliente_repo.get_by_id(cliente_id)
            if not cliente:
                return ServiceResult.fail(message="Cliente no encontrado")
            
            # Validar items
            if not items:
                return ServiceResult.fail(message="La orden debe tener al menos un item")
            
            # Generar número de orden
            numero_ov = self.orden_repo.generar_numero_ov()
            
            # Crear orden
            orden = self.orden_repo.create(
                numero_ov=numero_ov,
                cliente=cliente,
                estado='PENDIENTE',
                notas=notas or ''
            )
            
            # Crear items
            from App_LUMINOVA.models import ItemOrdenVenta, ProductoTerminado
            
            for item_data in items:
                producto = ProductoTerminado.objects.get(pk=item_data['producto_terminado_id'])
                
                ItemOrdenVenta.objects.create(
                    orden_venta=orden,
                    producto_terminado=producto,
                    cantidad=item_data['cantidad'],
                    precio_unitario_venta=Decimal(str(item_data.get('precio_unitario', producto.precio_unitario))),
                    empresa=self.empresa
                )
            
            # Registrar en historial
            self.historial_repo.registrar_evento(
                orden_venta=orden,
                descripcion=f"Orden de venta creada",
                tipo_evento="Creación",
                usuario=usuario
            )
            
            return ServiceResult.ok(
                data=orden,
                message=f"Orden {numero_ov} creada correctamente"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)], message="Error al crear orden de venta")
    
    @transaction.atomic
    def cambiar_estado_orden(
        self,
        orden_id: int,
        nuevo_estado: str,
        usuario=None,
        notas: str = None
    ) -> ServiceResult:
        """
        Cambia el estado de una orden de venta.
        
        Args:
            orden_id: ID de la orden
            nuevo_estado: Nuevo estado a asignar
            usuario: Usuario que realiza el cambio
            notas: Notas adicionales sobre el cambio
        """
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden no encontrada")
            
            # Validar transición de estado
            estados_validos = dict(orden.ESTADO_CHOICES).keys()
            if nuevo_estado not in estados_validos:
                return ServiceResult.fail(message=f"Estado '{nuevo_estado}' no válido")
            
            estado_anterior = orden.estado
            
            # Actualizar estado
            self.orden_repo.update(orden, estado=nuevo_estado)
            
            # Registrar en historial
            descripcion = f"Estado cambiado de '{estado_anterior}' a '{nuevo_estado}'"
            if notas:
                descripcion += f". {notas}"
            
            self.historial_repo.registrar_evento(
                orden_venta=orden,
                descripcion=descripcion,
                tipo_evento="Estado Cambiado",
                usuario=usuario
            )
            
            return ServiceResult.ok(
                data=orden,
                message=f"Estado actualizado a {nuevo_estado}"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def confirmar_orden(self, orden_id: int, usuario=None) -> ServiceResult:
        """Confirma una orden pendiente."""
        return self.cambiar_estado_orden(orden_id, 'CONFIRMADA', usuario)
    
    def cancelar_orden(self, orden_id: int, usuario=None, motivo: str = None) -> ServiceResult:
        """Cancela una orden de venta."""
        return self.cambiar_estado_orden(orden_id, 'CANCELADA', usuario, motivo)
    
    def marcar_lista_entrega(self, orden_id: int, usuario=None) -> ServiceResult:
        """Marca una orden como lista para entrega."""
        return self.cambiar_estado_orden(orden_id, 'LISTA_ENTREGA', usuario)
    
    def completar_orden(self, orden_id: int, usuario=None) -> ServiceResult:
        """Marca una orden como completada/entregada."""
        return self.cambiar_estado_orden(orden_id, 'COMPLETADA', usuario)
    
    def get_ordenes_pendientes(self) -> ServiceResult:
        """Obtiene órdenes pendientes de procesar."""
        try:
            ordenes = self.orden_repo.get_pendientes()
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_ordenes_en_produccion(self) -> ServiceResult:
        """Obtiene órdenes en producción."""
        try:
            ordenes = self.orden_repo.get_en_produccion()
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_ordenes_listas_entrega(self) -> ServiceResult:
        """Obtiene órdenes listas para entrega."""
        try:
            ordenes = self.orden_repo.get_listas_entrega()
            return ServiceResult.ok(data=list(ordenes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== FACTURACIÓN ====================
    
    @transaction.atomic
    def crear_factura(
        self,
        orden_id: int,
        numero_factura: str = None,
        usuario=None
    ) -> ServiceResult:
        """
        Crea una factura para una orden de venta.
        
        Args:
            orden_id: ID de la orden de venta
            numero_factura: Número de factura (se genera automáticamente si no se proporciona)
            usuario: Usuario que crea la factura
        """
        try:
            orden = self.orden_repo.get_by_id(orden_id)
            if not orden:
                return ServiceResult.fail(message="Orden no encontrada")
            
            # Verificar que no exista factura
            factura_existente = self.factura_repo.get_by_orden_venta(orden_id)
            if factura_existente:
                return ServiceResult.fail(message="La orden ya tiene una factura asociada")
            
            # Generar número si no se proporciona
            if not numero_factura:
                year = timezone.now().year
                count = self.factura_repo.count() + 1
                numero_factura = f"FAC-{year}-{count:05d}"
            
            # Crear factura
            factura = self.factura_repo.create(
                numero_factura=numero_factura,
                orden_venta=orden,
                total_facturado=orden.total_ov
            )
            
            # Registrar en historial
            self.historial_repo.registrar_evento(
                orden_venta=orden,
                descripcion=f"Factura {numero_factura} generada por ${orden.total_ov}",
                tipo_evento="Facturado",
                usuario=usuario
            )
            
            return ServiceResult.ok(
                data=factura,
                message=f"Factura {numero_factura} creada correctamente"
            )
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_factura(self, factura_id: int) -> ServiceResult:
        """Obtiene una factura por ID."""
        factura = self.factura_repo.get_by_id(factura_id)
        if not factura:
            return ServiceResult.fail(message="Factura no encontrada")
        return ServiceResult.ok(data=factura)
    
    # ==================== HISTORIAL ====================
    
    def get_historial_orden(self, orden_id: int) -> ServiceResult:
        """Obtiene el historial de una orden de venta."""
        try:
            historial = self.historial_repo.get_by_orden(orden_id)
            return ServiceResult.ok(data=list(historial))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== REPORTES ====================
    
    def get_resumen_ventas(self, dias: int = 30) -> ServiceResult:
        """
        Genera un resumen de ventas del período.
        
        Args:
            dias: Número de días a considerar
        """
        try:
            ordenes = self.orden_repo.get_recientes(dias)
            
            resumen = {
                'total_ordenes': ordenes.count(),
                'ordenes_pendientes': ordenes.filter(estado='PENDIENTE').count(),
                'ordenes_completadas': ordenes.filter(estado='COMPLETADA').count(),
                'ordenes_canceladas': ordenes.filter(estado='CANCELADA').count(),
                'en_produccion': ordenes.filter(estado__in=['INSUMOS_SOLICITADOS', 'PRODUCCION_INICIADA']).count(),
                'listas_entrega': ordenes.filter(estado='LISTA_ENTREGA').count(),
            }
            
            # Calcular totales
            from django.db.models import Sum
            total_vendido = ordenes.filter(
                estado__in=['COMPLETADA', 'LISTA_ENTREGA']
            ).aggregate(
                total=Sum('items_ov__subtotal')
            )['total'] or 0
            
            resumen['total_vendido'] = float(total_vendido)
            
            return ServiceResult.ok(data=resumen)
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_productos_mas_vendidos(self, limit: int = 10, dias: int = 30) -> ServiceResult:
        """Obtiene los productos más vendidos en el período."""
        try:
            from django.db.models import Sum, Count
            from datetime import datetime, timedelta
            from App_LUMINOVA.models import ItemOrdenVenta
            
            fecha_limite = datetime.now() - timedelta(days=dias)
            
            productos = ItemOrdenVenta.objects.filter(
                orden_venta__fecha_creacion__gte=fecha_limite,
                orden_venta__estado__in=['COMPLETADA', 'LISTA_ENTREGA']
            )
            
            if self.empresa:
                productos = productos.filter(empresa=self.empresa)
            
            productos = productos.values(
                'producto_terminado__id',
                'producto_terminado__descripcion'
            ).annotate(
                total_cantidad=Sum('cantidad'),
                total_vendido=Sum('subtotal'),
                veces_vendido=Count('id')
            ).order_by('-total_cantidad')[:limit]
            
            return ServiceResult.ok(data=list(productos))
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
