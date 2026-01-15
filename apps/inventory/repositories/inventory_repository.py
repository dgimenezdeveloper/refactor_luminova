"""
Repositorios para el módulo de inventario.

Proporcionan una capa de abstracción sobre el ORM de Django para
acceso a datos de productos, insumos, categorías y stock.
"""

from typing import List, Optional, Dict, Any
from django.db.models import QuerySet, Sum, F, Q
from django.db import transaction

from apps.core.base import BaseRepository

# Importamos los modelos desde las nuevas apps modulares
from apps.inventory.models import (
    ProductoTerminado,
    Insumo,
    CategoriaProductoTerminado,
    CategoriaInsumo,
    ComponenteProducto,
    StockProductoTerminado,
    StockInsumo,
    MovimientoStock,
)
from apps.core.models import Deposito


class ProductoRepository(BaseRepository[ProductoTerminado]):
    """Repositorio para operaciones con productos terminados."""
    
    model = ProductoTerminado
    
    def get_by_deposito(self, deposito_id: int) -> QuerySet[ProductoTerminado]:
        """Obtiene productos por depósito."""
        return self._get_base_queryset().filter(deposito_id=deposito_id)
    
    def get_by_categoria(self, categoria_id: int) -> QuerySet[ProductoTerminado]:
        """Obtiene productos por categoría."""
        return self._get_base_queryset().filter(categoria_id=categoria_id)
    
    def get_productos_con_stock_bajo(self) -> QuerySet[ProductoTerminado]:
        """Obtiene productos que necesitan reposición de stock."""
        # Usamos anotación para calcular stock total desde StockProductoTerminado
        productos = self._get_base_queryset().annotate(
            stock_total=Sum('stockproductoterminado__cantidad')
        ).filter(
            stock_total__lte=F('stock_minimo'),
            stock_minimo__gt=0
        )
        return productos
    
    def get_productos_habilitados_produccion(self) -> QuerySet[ProductoTerminado]:
        """Obtiene productos habilitados para producción."""
        return self._get_base_queryset().filter(
            produccion_habilitada=True,
            stock_objetivo__gt=0
        )
    
    def get_stock_by_deposito(self, producto_id: int, deposito_id: int) -> int:
        """Obtiene el stock de un producto en un depósito específico."""
        try:
            stock = StockProductoTerminado.objects.get(
                producto_id=producto_id,
                deposito_id=deposito_id
            )
            return stock.cantidad
        except StockProductoTerminado.DoesNotExist:
            return 0
    
    def get_stock_total(self, producto_id: int) -> int:
        """Obtiene el stock total de un producto en todos los depósitos."""
        result = StockProductoTerminado.objects.filter(
            producto_id=producto_id
        ).aggregate(total=Sum('cantidad'))
        return result['total'] or 0
    
    def search(self, query: str) -> QuerySet[ProductoTerminado]:
        """Busca productos por descripción, modelo o material."""
        return self._get_base_queryset().filter(
            Q(descripcion__icontains=query) |
            Q(modelo__icontains=query) |
            Q(material__icontains=query)
        )


class InsumoRepository(BaseRepository[Insumo]):
    """Repositorio para operaciones con insumos."""
    
    model = Insumo
    
    def get_by_deposito(self, deposito_id: int) -> QuerySet[Insumo]:
        """Obtiene insumos por depósito."""
        return self._get_base_queryset().filter(deposito_id=deposito_id)
    
    def get_by_categoria(self, categoria_id: int) -> QuerySet[Insumo]:
        """Obtiene insumos por categoría."""
        return self._get_base_queryset().filter(categoria_id=categoria_id)
    
    def get_by_fabricante(self, fabricante_id: int) -> QuerySet[Insumo]:
        """Obtiene insumos por fabricante."""
        return self._get_base_queryset().filter(fabricante_id=fabricante_id)
    
    def get_insumos_con_stock_bajo(self, umbral: int = 10) -> QuerySet[Insumo]:
        """Obtiene insumos con stock bajo."""
        return self._get_base_queryset().annotate(
            stock_total=Sum('stockinsumo__cantidad')
        ).filter(stock_total__lte=umbral)
    
    def get_insumos_no_notificados(self) -> QuerySet[Insumo]:
        """Obtiene insumos con stock bajo que aún no fueron notificados a compras."""
        return self.get_insumos_con_stock_bajo().filter(notificado_a_compras=False)
    
    def get_stock_by_deposito(self, insumo_id: int, deposito_id: int) -> int:
        """Obtiene el stock de un insumo en un depósito específico."""
        try:
            stock = StockInsumo.objects.get(
                insumo_id=insumo_id,
                deposito_id=deposito_id
            )
            return stock.cantidad
        except StockInsumo.DoesNotExist:
            return 0
    
    def get_stock_total(self, insumo_id: int) -> int:
        """Obtiene el stock total de un insumo en todos los depósitos."""
        result = StockInsumo.objects.filter(
            insumo_id=insumo_id
        ).aggregate(total=Sum('cantidad'))
        return result['total'] or 0
    
    def search(self, query: str) -> QuerySet[Insumo]:
        """Busca insumos por descripción."""
        return self._get_base_queryset().filter(
            descripcion__icontains=query
        )


class CategoriaProductoRepository(BaseRepository[CategoriaProductoTerminado]):
    """Repositorio para categorías de productos terminados."""
    
    model = CategoriaProductoTerminado
    
    def get_by_deposito(self, deposito_id: int) -> QuerySet[CategoriaProductoTerminado]:
        """Obtiene categorías por depósito."""
        return self._get_base_queryset().filter(deposito_id=deposito_id)
    
    def get_with_product_count(self) -> QuerySet:
        """Obtiene categorías con conteo de productos."""
        from django.db.models import Count
        return self._get_base_queryset().annotate(
            producto_count=Count('productos_terminados')
        )


class CategoriaInsumoRepository(BaseRepository[CategoriaInsumo]):
    """Repositorio para categorías de insumos."""
    
    model = CategoriaInsumo
    
    def get_by_deposito(self, deposito_id: int) -> QuerySet[CategoriaInsumo]:
        """Obtiene categorías por depósito."""
        return self._get_base_queryset().filter(deposito_id=deposito_id)
    
    def get_with_insumo_count(self) -> QuerySet:
        """Obtiene categorías con conteo de insumos."""
        from django.db.models import Count
        return self._get_base_queryset().annotate(
            insumo_count=Count('insumos')
        )


class ComponenteProductoRepository(BaseRepository[ComponenteProducto]):
    """Repositorio para componentes de productos (BOM - Bill of Materials)."""
    
    model = ComponenteProducto
    
    def get_by_producto(self, producto_id: int) -> QuerySet[ComponenteProducto]:
        """Obtiene componentes requeridos para un producto."""
        return self._get_base_queryset().filter(producto_terminado_id=producto_id)
    
    def get_productos_que_usan_insumo(self, insumo_id: int) -> QuerySet[ComponenteProducto]:
        """Obtiene qué productos usan un insumo específico."""
        return self._get_base_queryset().filter(insumo_id=insumo_id)


class StockProductoRepository(BaseRepository[StockProductoTerminado]):
    """Repositorio para stock de productos terminados por depósito."""
    
    model = StockProductoTerminado
    
    def get_stock_matrix(self, deposito_id: int = None) -> QuerySet:
        """
        Obtiene matriz de stock con información del producto.
        """
        qs = self._get_base_queryset().select_related('producto', 'deposito')
        if deposito_id:
            qs = qs.filter(deposito_id=deposito_id)
        return qs
    
    def update_stock(
        self, 
        producto_id: int, 
        deposito_id: int, 
        cantidad: int,
        incrementar: bool = True
    ) -> StockProductoTerminado:
        """
        Actualiza el stock de un producto en un depósito.
        
        Args:
            producto_id: ID del producto
            deposito_id: ID del depósito
            cantidad: Cantidad a ajustar
            incrementar: Si True suma, si False resta
        """
        with transaction.atomic():
            stock, created = StockProductoTerminado.objects.get_or_create(
                producto_id=producto_id,
                deposito_id=deposito_id,
                defaults={'cantidad': 0}
            )
            
            if incrementar:
                stock.cantidad = F('cantidad') + cantidad
            else:
                stock.cantidad = F('cantidad') - cantidad
            
            stock.save()
            stock.refresh_from_db()
            return stock


class StockInsumoRepository(BaseRepository[StockInsumo]):
    """Repositorio para stock de insumos por depósito."""
    
    model = StockInsumo
    
    def get_stock_matrix(self, deposito_id: int = None) -> QuerySet:
        """Obtiene matriz de stock con información del insumo."""
        qs = self._get_base_queryset().select_related('insumo', 'deposito')
        if deposito_id:
            qs = qs.filter(deposito_id=deposito_id)
        return qs
    
    def update_stock(
        self, 
        insumo_id: int, 
        deposito_id: int, 
        cantidad: int,
        incrementar: bool = True
    ) -> StockInsumo:
        """Actualiza el stock de un insumo en un depósito."""
        with transaction.atomic():
            stock, created = StockInsumo.objects.get_or_create(
                insumo_id=insumo_id,
                deposito_id=deposito_id,
                defaults={'cantidad': 0}
            )
            
            if incrementar:
                stock.cantidad = F('cantidad') + cantidad
            else:
                stock.cantidad = F('cantidad') - cantidad
            
            stock.save()
            stock.refresh_from_db()
            return stock


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    """Repositorio para historial de movimientos de stock."""
    
    model = MovimientoStock
    
    def get_by_deposito_origen(self, deposito_id: int) -> QuerySet[MovimientoStock]:
        """Obtiene movimientos de salida de un depósito."""
        return self._get_base_queryset().filter(deposito_origen_id=deposito_id)
    
    def get_by_deposito_destino(self, deposito_id: int) -> QuerySet[MovimientoStock]:
        """Obtiene movimientos de entrada a un depósito."""
        return self._get_base_queryset().filter(deposito_destino_id=deposito_id)
    
    def get_transferencias(self) -> QuerySet[MovimientoStock]:
        """Obtiene todas las transferencias entre depósitos."""
        return self._get_base_queryset().filter(tipo='transferencia')
    
    def get_by_producto(self, producto_id: int) -> QuerySet[MovimientoStock]:
        """Obtiene movimientos de un producto específico."""
        return self._get_base_queryset().filter(producto_id=producto_id)
    
    def get_by_insumo(self, insumo_id: int) -> QuerySet[MovimientoStock]:
        """Obtiene movimientos de un insumo específico."""
        return self._get_base_queryset().filter(insumo_id=insumo_id)
    
    def registrar_movimiento(
        self,
        tipo: str,
        cantidad: int,
        usuario,
        motivo: str = "",
        insumo_id: int = None,
        producto_id: int = None,
        deposito_origen_id: int = None,
        deposito_destino_id: int = None
    ) -> MovimientoStock:
        """
        Registra un nuevo movimiento de stock.
        
        Args:
            tipo: 'entrada', 'salida' o 'transferencia'
            cantidad: Cantidad del movimiento
            usuario: Usuario que realiza el movimiento
            motivo: Motivo del movimiento
            insumo_id: ID del insumo (si aplica)
            producto_id: ID del producto (si aplica)
            deposito_origen_id: ID del depósito de origen
            deposito_destino_id: ID del depósito de destino
        """
        return self.create(
            tipo=tipo,
            cantidad=cantidad,
            usuario=usuario,
            motivo=motivo,
            insumo_id=insumo_id,
            producto_id=producto_id,
            deposito_origen_id=deposito_origen_id,
            deposito_destino_id=deposito_destino_id
        )


class DepositoRepository(BaseRepository[Deposito]):
    """Repositorio para depósitos."""
    
    model = Deposito
    
    def get_by_empresa(self, empresa_id: int) -> QuerySet[Deposito]:
        """Obtiene depósitos de una empresa."""
        return self.model.objects.filter(empresa_id=empresa_id)
    
    def get_con_stock_summary(self) -> QuerySet:
        """Obtiene depósitos con resumen de stock."""
        from django.db.models import Count
        return self._get_base_queryset().annotate(
            total_productos=Count('stockproductoterminado'),
            total_insumos=Count('stockinsumo')
        )
