"""
Servicios para el módulo de inventario.

Contienen la lógica de negocio para gestión de productos, insumos y stock.
Los servicios coordinan repositorios y no acceden directamente al ORM.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.core.base import BaseService, ServiceResult
from apps.inventory.repositories.inventory_repository import (
    ProductoRepository,
    InsumoRepository,
    StockProductoRepository,
    StockInsumoRepository,
    MovimientoStockRepository,
    ComponenteProductoRepository,
    DepositoRepository,
)


class InventoryService(BaseService):
    """
    Servicio principal de inventario.
    
    Coordina operaciones entre productos, insumos y stock.
    Implementa la lógica de negocio de gestión de inventario.
    """
    
    def __init__(self, empresa=None):
        super().__init__(empresa)
        self.producto_repo = ProductoRepository(empresa)
        self.insumo_repo = InsumoRepository(empresa)
        self.stock_producto_repo = StockProductoRepository(empresa)
        self.stock_insumo_repo = StockInsumoRepository(empresa)
        self.movimiento_repo = MovimientoStockRepository(empresa)
        self.componente_repo = ComponenteProductoRepository(empresa)
        self.deposito_repo = DepositoRepository(empresa)
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos de entrada para operaciones de inventario."""
        errors = []
        
        if 'cantidad' in data:
            if data['cantidad'] < 0:
                errors.append("La cantidad no puede ser negativa")
        
        if 'precio_unitario' in data:
            if data['precio_unitario'] < 0:
                errors.append("El precio no puede ser negativo")
        
        if errors:
            raise ValidationError(errors)
        
        return data
    
    # ==================== PRODUCTOS ====================
    
    def get_productos(self, deposito_id: int = None) -> ServiceResult:
        """
        Obtiene lista de productos, opcionalmente filtrada por depósito.
        """
        try:
            if deposito_id:
                productos = self.producto_repo.get_by_deposito(deposito_id)
            else:
                productos = self.producto_repo.get_all()
            
            return ServiceResult.ok(data=list(productos))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)], message="Error al obtener productos")
    
    def get_producto(self, producto_id: int) -> ServiceResult:
        """Obtiene un producto por ID."""
        producto = self.producto_repo.get_by_id(producto_id)
        if not producto:
            return ServiceResult.fail(message="Producto no encontrado")
        return ServiceResult.ok(data=producto)
    
    def get_productos_necesitan_reposicion(self) -> ServiceResult:
        """Obtiene productos que necesitan reposición de stock."""
        try:
            productos = self.producto_repo.get_productos_con_stock_bajo()
            return ServiceResult.ok(data=list(productos))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def search_productos(self, query: str) -> ServiceResult:
        """Busca productos por texto."""
        try:
            productos = self.producto_repo.search(query)
            return ServiceResult.ok(data=list(productos))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== INSUMOS ====================
    
    def get_insumos(self, deposito_id: int = None) -> ServiceResult:
        """Obtiene lista de insumos, opcionalmente filtrada por depósito."""
        try:
            if deposito_id:
                insumos = self.insumo_repo.get_by_deposito(deposito_id)
            else:
                insumos = self.insumo_repo.get_all()
            
            return ServiceResult.ok(data=list(insumos))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)], message="Error al obtener insumos")
    
    def get_insumo(self, insumo_id: int) -> ServiceResult:
        """Obtiene un insumo por ID."""
        insumo = self.insumo_repo.get_by_id(insumo_id)
        if not insumo:
            return ServiceResult.fail(message="Insumo no encontrado")
        return ServiceResult.ok(data=insumo)
    
    def get_insumos_stock_bajo(self, umbral: int = 10) -> ServiceResult:
        """Obtiene insumos con stock bajo."""
        try:
            insumos = self.insumo_repo.get_insumos_con_stock_bajo(umbral)
            return ServiceResult.ok(data=list(insumos))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== STOCK ====================
    
    def get_stock_producto(self, producto_id: int, deposito_id: int = None) -> ServiceResult:
        """
        Obtiene el stock de un producto.
        
        Args:
            producto_id: ID del producto
            deposito_id: Si se especifica, retorna stock solo de ese depósito
        """
        try:
            if deposito_id:
                stock = self.producto_repo.get_stock_by_deposito(producto_id, deposito_id)
            else:
                stock = self.producto_repo.get_stock_total(producto_id)
            
            return ServiceResult.ok(data={'stock': stock})
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_stock_insumo(self, insumo_id: int, deposito_id: int = None) -> ServiceResult:
        """Obtiene el stock de un insumo."""
        try:
            if deposito_id:
                stock = self.insumo_repo.get_stock_by_deposito(insumo_id, deposito_id)
            else:
                stock = self.insumo_repo.get_stock_total(insumo_id)
            
            return ServiceResult.ok(data={'stock': stock})
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    @transaction.atomic
    def ajustar_stock_producto(
        self,
        producto_id: int,
        deposito_id: int,
        cantidad: int,
        tipo: str,
        usuario,
        motivo: str = ""
    ) -> ServiceResult:
        """
        Ajusta el stock de un producto (entrada o salida).
        
        Args:
            producto_id: ID del producto
            deposito_id: ID del depósito
            cantidad: Cantidad a ajustar (siempre positiva)
            tipo: 'entrada' o 'salida'
            usuario: Usuario que realiza el ajuste
            motivo: Motivo del ajuste
        """
        try:
            # Validar
            if cantidad <= 0:
                return ServiceResult.fail(message="La cantidad debe ser positiva")
            
            if tipo not in ['entrada', 'salida']:
                return ServiceResult.fail(message="Tipo debe ser 'entrada' o 'salida'")
            
            # Verificar que exista el producto
            producto = self.producto_repo.get_by_id(producto_id)
            if not producto:
                return ServiceResult.fail(message="Producto no encontrado")
            
            # Si es salida, verificar stock disponible
            if tipo == 'salida':
                stock_actual = self.producto_repo.get_stock_by_deposito(producto_id, deposito_id)
                if stock_actual < cantidad:
                    return ServiceResult.fail(
                        message=f"Stock insuficiente. Disponible: {stock_actual}, Solicitado: {cantidad}"
                    )
            
            # Realizar ajuste
            incrementar = tipo == 'entrada'
            self.stock_producto_repo.update_stock(
                producto_id=producto_id,
                deposito_id=deposito_id,
                cantidad=cantidad,
                incrementar=incrementar
            )
            
            # Registrar movimiento
            deposito_origen = deposito_id if tipo == 'salida' else None
            deposito_destino = deposito_id if tipo == 'entrada' else None
            
            self.movimiento_repo.registrar_movimiento(
                tipo=tipo,
                cantidad=cantidad,
                usuario=usuario,
                motivo=motivo,
                producto_id=producto_id,
                deposito_origen_id=deposito_origen,
                deposito_destino_id=deposito_destino
            )
            
            return ServiceResult.ok(message=f"Stock ajustado correctamente ({tipo}: {cantidad})")
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)], message="Error al ajustar stock")
    
    @transaction.atomic
    def ajustar_stock_insumo(
        self,
        insumo_id: int,
        deposito_id: int,
        cantidad: int,
        tipo: str,
        usuario,
        motivo: str = ""
    ) -> ServiceResult:
        """Ajusta el stock de un insumo (entrada o salida)."""
        try:
            if cantidad <= 0:
                return ServiceResult.fail(message="La cantidad debe ser positiva")
            
            if tipo not in ['entrada', 'salida']:
                return ServiceResult.fail(message="Tipo debe ser 'entrada' o 'salida'")
            
            insumo = self.insumo_repo.get_by_id(insumo_id)
            if not insumo:
                return ServiceResult.fail(message="Insumo no encontrado")
            
            if tipo == 'salida':
                stock_actual = self.insumo_repo.get_stock_by_deposito(insumo_id, deposito_id)
                if stock_actual < cantidad:
                    return ServiceResult.fail(
                        message=f"Stock insuficiente. Disponible: {stock_actual}"
                    )
            
            incrementar = tipo == 'entrada'
            self.stock_insumo_repo.update_stock(
                insumo_id=insumo_id,
                deposito_id=deposito_id,
                cantidad=cantidad,
                incrementar=incrementar
            )
            
            deposito_origen = deposito_id if tipo == 'salida' else None
            deposito_destino = deposito_id if tipo == 'entrada' else None
            
            self.movimiento_repo.registrar_movimiento(
                tipo=tipo,
                cantidad=cantidad,
                usuario=usuario,
                motivo=motivo,
                insumo_id=insumo_id,
                deposito_origen_id=deposito_origen,
                deposito_destino_id=deposito_destino
            )
            
            return ServiceResult.ok(message=f"Stock de insumo ajustado correctamente")
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    @transaction.atomic
    def transferir_stock_producto(
        self,
        producto_id: int,
        deposito_origen_id: int,
        deposito_destino_id: int,
        cantidad: int,
        usuario,
        motivo: str = ""
    ) -> ServiceResult:
        """
        Transfiere stock de producto entre depósitos.
        """
        try:
            if cantidad <= 0:
                return ServiceResult.fail(message="La cantidad debe ser positiva")
            
            if deposito_origen_id == deposito_destino_id:
                return ServiceResult.fail(message="El depósito origen y destino no pueden ser iguales")
            
            # Verificar stock disponible
            stock_disponible = self.producto_repo.get_stock_by_deposito(
                producto_id, deposito_origen_id
            )
            if stock_disponible < cantidad:
                return ServiceResult.fail(
                    message=f"Stock insuficiente en origen. Disponible: {stock_disponible}"
                )
            
            # Realizar transferencia
            self.stock_producto_repo.update_stock(
                producto_id=producto_id,
                deposito_id=deposito_origen_id,
                cantidad=cantidad,
                incrementar=False
            )
            
            self.stock_producto_repo.update_stock(
                producto_id=producto_id,
                deposito_id=deposito_destino_id,
                cantidad=cantidad,
                incrementar=True
            )
            
            # Registrar movimiento
            self.movimiento_repo.registrar_movimiento(
                tipo='transferencia',
                cantidad=cantidad,
                usuario=usuario,
                motivo=motivo,
                producto_id=producto_id,
                deposito_origen_id=deposito_origen_id,
                deposito_destino_id=deposito_destino_id
            )
            
            return ServiceResult.ok(message=f"Transferencia realizada correctamente ({cantidad} unidades)")
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    @transaction.atomic
    def transferir_stock_insumo(
        self,
        insumo_id: int,
        deposito_origen_id: int,
        deposito_destino_id: int,
        cantidad: int,
        usuario,
        motivo: str = ""
    ) -> ServiceResult:
        """Transfiere stock de insumo entre depósitos."""
        try:
            if cantidad <= 0:
                return ServiceResult.fail(message="La cantidad debe ser positiva")
            
            if deposito_origen_id == deposito_destino_id:
                return ServiceResult.fail(message="El depósito origen y destino no pueden ser iguales")
            
            stock_disponible = self.insumo_repo.get_stock_by_deposito(
                insumo_id, deposito_origen_id
            )
            if stock_disponible < cantidad:
                return ServiceResult.fail(
                    message=f"Stock insuficiente en origen. Disponible: {stock_disponible}"
                )
            
            self.stock_insumo_repo.update_stock(
                insumo_id=insumo_id,
                deposito_id=deposito_origen_id,
                cantidad=cantidad,
                incrementar=False
            )
            
            self.stock_insumo_repo.update_stock(
                insumo_id=insumo_id,
                deposito_id=deposito_destino_id,
                cantidad=cantidad,
                incrementar=True
            )
            
            self.movimiento_repo.registrar_movimiento(
                tipo='transferencia',
                cantidad=cantidad,
                usuario=usuario,
                motivo=motivo,
                insumo_id=insumo_id,
                deposito_origen_id=deposito_origen_id,
                deposito_destino_id=deposito_destino_id
            )
            
            return ServiceResult.ok(message="Transferencia de insumo realizada correctamente")
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== BOM (Bill of Materials) ====================
    
    def get_componentes_producto(self, producto_id: int) -> ServiceResult:
        """Obtiene la lista de componentes (insumos) requeridos para un producto."""
        try:
            componentes = self.componente_repo.get_by_producto(producto_id)
            return ServiceResult.ok(data=list(componentes))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def verificar_disponibilidad_produccion(
        self, 
        producto_id: int, 
        cantidad: int,
        deposito_id: int
    ) -> ServiceResult:
        """
        Verifica si hay insumos suficientes para producir una cantidad de producto.
        
        Args:
            producto_id: ID del producto a producir
            cantidad: Cantidad a producir
            deposito_id: Depósito donde verificar disponibilidad
            
        Returns:
            ServiceResult con datos de disponibilidad por componente
        """
        try:
            componentes = self.componente_repo.get_by_producto(producto_id)
            
            disponibilidad = []
            puede_producir = True
            cantidad_maxima_producible = float('inf')
            
            for comp in componentes:
                cantidad_necesaria = comp.cantidad_necesaria * cantidad
                stock_disponible = self.insumo_repo.get_stock_by_deposito(
                    comp.insumo_id, deposito_id
                )
                
                disponible = stock_disponible >= cantidad_necesaria
                faltante = max(0, cantidad_necesaria - stock_disponible)
                
                # Calcular máximo producible con este componente
                if comp.cantidad_necesaria > 0:
                    max_con_este = stock_disponible // comp.cantidad_necesaria
                    cantidad_maxima_producible = min(cantidad_maxima_producible, max_con_este)
                
                if not disponible:
                    puede_producir = False
                
                disponibilidad.append({
                    'insumo': comp.insumo.descripcion,
                    'insumo_id': comp.insumo_id,
                    'cantidad_necesaria': cantidad_necesaria,
                    'stock_disponible': stock_disponible,
                    'disponible': disponible,
                    'faltante': faltante
                })
            
            return ServiceResult.ok(data={
                'puede_producir': puede_producir,
                'cantidad_solicitada': cantidad,
                'cantidad_maxima_producible': int(cantidad_maxima_producible) if cantidad_maxima_producible != float('inf') else 0,
                'componentes': disponibilidad
            })
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    # ==================== REPORTES ====================
    
    def get_resumen_inventario(self, deposito_id: int = None) -> ServiceResult:
        """
        Genera un resumen del inventario.
        
        Returns:
            Diccionario con totales de productos, insumos, y alertas de stock bajo
        """
        try:
            productos_qs = self.producto_repo.get_all()
            insumos_qs = self.insumo_repo.get_all()
            
            if deposito_id:
                productos_qs = self.producto_repo.get_by_deposito(deposito_id)
                insumos_qs = self.insumo_repo.get_by_deposito(deposito_id)
            
            productos_stock_bajo = self.producto_repo.get_productos_con_stock_bajo()
            insumos_stock_bajo = self.insumo_repo.get_insumos_con_stock_bajo()
            
            resumen = {
                'total_productos': productos_qs.count(),
                'total_insumos': insumos_qs.count(),
                'productos_stock_bajo': productos_stock_bajo.count(),
                'insumos_stock_bajo': insumos_stock_bajo.count(),
                'alertas_pendientes': productos_stock_bajo.count() + insumos_stock_bajo.count()
            }
            
            return ServiceResult.ok(data=resumen)
            
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
    
    def get_movimientos_recientes(self, limit: int = 50) -> ServiceResult:
        """Obtiene los movimientos de stock más recientes."""
        try:
            movimientos = self.movimiento_repo.get_all().order_by('-fecha')[:limit]
            return ServiceResult.ok(data=list(movimientos))
        except Exception as e:
            return ServiceResult.fail(errors=[str(e)])
