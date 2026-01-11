"""
Importador de Productos Terminados - Adaptable a cualquier rubro
"""
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import logging

from .base_importer import BaseImporter, ValidationError
from App_LUMINOVA.models import ProductoTerminado, CategoriaProductoTerminado

logger = logging.getLogger(__name__)


class ProductoImporter(BaseImporter):
    """
    Importador de productos terminados
    Flexible para cualquier tipo de empresa y rubro
    """
    
    REQUIRED_FIELDS = ['descripcion']
    
    FIELD_ALIASES = {
        'descripcion': ['descripcion', 'nombre', 'producto', 'item', 'artículo', 'plato', 'servicio'],
        'precio_unitario': ['precio', 'precio_unitario', 'valor', 'precio unitario', 'pvp'],
        'stock': ['stock', 'stock_actual', 'cantidad', 'existencia'],
        'stock_minimo': ['stock_minimo', 'minimo', 'min_stock', 'stock mínimo'],
        'stock_objetivo': ['stock_objetivo', 'objetivo', 'stock_max', 'stock máximo'],
        'categoria': ['categoria', 'categoría', 'tipo', 'grupo', 'familia'],
        'modelo': ['modelo', 'codigo', 'referencia', 'sku'],
        'produccion_habilitada': ['produccion', 'produccion_habilitada', 'fabricable', 'producible'],
    }
    
    def __init__(self, empresa, deposito):
        super().__init__(empresa, deposito)
        if not deposito:
            raise ValidationError("Se requiere especificar un depósito para importar productos")
    
    def validate_row(self, row: pd.Series, row_number: int) -> Tuple[bool, Optional[str]]:
        """Valida una fila de producto"""
        # Descripción es obligatoria
        if pd.isna(row.get('descripcion')) or str(row.get('descripcion')).strip() == '':
            return False, "Descripción es obligatoria"
        
        # Validar precio si existe
        if 'precio_unitario' in row and not pd.isna(row['precio_unitario']):
            try:
                precio = float(row['precio_unitario'])
                if precio < 0:
                    return False, "Precio no puede ser negativo"
            except (ValueError, TypeError):
                return False, f"Precio inválido: {row['precio_unitario']}"
        
        # Validar stocks si existen
        for stock_field in ['stock', 'stock_minimo', 'stock_objetivo']:
            if stock_field in row and not pd.isna(row[stock_field]):
                try:
                    stock = int(float(row[stock_field]))
                    if stock < 0:
                        return False, f"{stock_field} no puede ser negativo"
                except (ValueError, TypeError):
                    return False, f"{stock_field} inválido: {row[stock_field]}"
        
        return True, None
    
    def get_or_create_categoria(self, categoria_nombre: str) -> Optional[CategoriaProductoTerminado]:
        """Obtiene o crea una categoría de producto"""
        if not categoria_nombre or pd.isna(categoria_nombre):
            categoria_nombre = "Sin Categoría"
        
        categoria_nombre = str(categoria_nombre).strip()
        
        try:
            categoria, created = CategoriaProductoTerminado.objects.get_or_create(
                nombre=categoria_nombre,
                deposito=self.deposito,
                defaults={'nombre': categoria_nombre}
            )
            if created:
                logger.info(f"Categoría de producto creada: {categoria_nombre}")
            return categoria
        except Exception as e:
            logger.error(f"Error al crear categoría '{categoria_nombre}': {str(e)}")
            return None
    
    def transform_row(self, row: pd.Series) -> Dict[str, Any]:
        """Transforma una fila a formato de producto"""
        data = {
            'descripcion': str(row['descripcion']).strip(),
            'deposito': self.deposito,
        }
        
        # Precio
        if 'precio_unitario' in row and not pd.isna(row['precio_unitario']):
            try:
                data['precio_unitario'] = Decimal(str(row['precio_unitario']))
            except (InvalidOperation, ValueError):
                data['precio_unitario'] = Decimal('0.00')
        
        # Stock actual
        if 'stock' in row and not pd.isna(row['stock']):
            try:
                data['stock'] = int(float(row['stock']))
            except (ValueError, TypeError):
                data['stock'] = 0
        
        # Stock mínimo
        if 'stock_minimo' in row and not pd.isna(row['stock_minimo']):
            try:
                data['stock_minimo'] = int(float(row['stock_minimo']))
            except (ValueError, TypeError):
                data['stock_minimo'] = 0
        
        # Stock objetivo
        if 'stock_objetivo' in row and not pd.isna(row['stock_objetivo']):
            try:
                data['stock_objetivo'] = int(float(row['stock_objetivo']))
            except (ValueError, TypeError):
                data['stock_objetivo'] = 0
        
        # Modelo/código
        if 'modelo' in row and not pd.isna(row['modelo']):
            data['modelo'] = str(row['modelo']).strip()
        
        # Producción habilitada
        if 'produccion_habilitada' in row and not pd.isna(row['produccion_habilitada']):
            valor = str(row['produccion_habilitada']).lower().strip()
            data['produccion_habilitada'] = valor in ['si', 'sí', 'yes', 'true', '1', 'habilitado']
        
        # Categoría
        if 'categoria' in row:
            categoria = self.get_or_create_categoria(row['categoria'])
            if categoria:
                data['categoria'] = categoria
        
        return data
    
    def import_row(self, row_data: Dict[str, Any]) -> Optional[ProductoTerminado]:
        """Crea el producto en la base de datos"""
        try:
            descripcion = row_data['descripcion']
            deposito = row_data['deposito']
            
            # Verificar si ya existe
            producto, created = ProductoTerminado.objects.get_or_create(
                descripcion=descripcion,
                deposito=deposito,
                defaults=row_data
            )
            
            if not created:
                # Actualizar campos
                for key, value in row_data.items():
                    if key not in ['descripcion', 'deposito']:
                        setattr(producto, key, value)
                producto.save()
                logger.debug(f"Producto actualizado: {descripcion}")
            else:
                logger.debug(f"Producto creado: {descripcion}")
            
            return producto
            
        except Exception as e:
            logger.error(f"Error al importar producto '{row_data.get('descripcion')}': {str(e)}")
            self.warnings.append(f"No se pudo importar: {row_data.get('descripcion')} - {str(e)}")
            return None
