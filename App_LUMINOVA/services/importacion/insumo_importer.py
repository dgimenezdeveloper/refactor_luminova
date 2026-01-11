"""
Importador de Insumos - Adaptable a cualquier rubro
"""
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import logging

from .base_importer import BaseImporter, ValidationError
from App_LUMINOVA.models import Insumo, CategoriaInsumo, Fabricante

logger = logging.getLogger(__name__)


class InsumoImporter(BaseImporter):
    """
    Importador de insumos/materias primas
    Flexible para cualquier tipo de empresa
    """
    
    REQUIRED_FIELDS = ['descripcion']
    
    FIELD_ALIASES = {
        'descripcion': ['descripcion', 'nombre', 'producto', 'item', 'artículo', 'material'],
        'precio_unitario': ['precio', 'precio_unitario', 'costo', 'valor', 'precio unitario'],
        'stock_minimo': ['stock_minimo', 'minimo', 'min_stock', 'stock mínimo', 'punto_reorden'],
        'stock_actual': ['stock', 'stock_actual', 'cantidad', 'existencia', 'stock actual'],
        'categoria': ['categoria', 'categoría', 'tipo', 'grupo', 'familia'],
        'fabricante': ['fabricante', 'proveedor', 'marca', 'supplier'],
        'unidad_medida': ['unidad', 'unidad_medida', 'um', 'unidad medida', 'presentacion'],
        'codigo': ['codigo', 'código', 'sku', 'referencia', 'cod'],
    }
    
    def __init__(self, empresa, deposito):
        super().__init__(empresa, deposito)
        if not deposito:
            raise ValidationError("Se requiere especificar un depósito para importar insumos")
    
    def validate_row(self, row: pd.Series, row_number: int) -> Tuple[bool, Optional[str]]:
        """Valida una fila de insumo"""
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
        
        # Validar stock si existe
        if 'stock_actual' in row and not pd.isna(row['stock_actual']):
            try:
                stock = int(float(row['stock_actual']))
                if stock < 0:
                    return False, "Stock no puede ser negativo"
            except (ValueError, TypeError):
                return False, f"Stock inválido: {row['stock_actual']}"
        
        return True, None
    
    def get_or_create_categoria(self, categoria_nombre: str) -> Optional[CategoriaInsumo]:
        """Obtiene o crea una categoría de insumo"""
        if not categoria_nombre or pd.isna(categoria_nombre):
            # Crear/obtener categoría por defecto
            categoria_nombre = "Sin Categoría"
        
        categoria_nombre = str(categoria_nombre).strip()
        
        try:
            categoria, created = CategoriaInsumo.objects.get_or_create(
                nombre=categoria_nombre,
                deposito=self.deposito,
                defaults={'nombre': categoria_nombre}
            )
            if created:
                logger.info(f"Categoría creada: {categoria_nombre}")
            return categoria
        except Exception as e:
            logger.error(f"Error al crear categoría '{categoria_nombre}': {str(e)}")
            return None
    
    def get_or_create_fabricante(self, fabricante_nombre: str) -> Optional[Fabricante]:
        """Obtiene o crea un fabricante"""
        if not fabricante_nombre or pd.isna(fabricante_nombre):
            return None
        
        fabricante_nombre = str(fabricante_nombre).strip()
        
        try:
            fabricante, created = Fabricante.objects.get_or_create(
                nombre=fabricante_nombre,
                defaults={
                    'nombre': fabricante_nombre,
                    'email': f"contacto@{fabricante_nombre.lower().replace(' ', '')}.com"
                }
            )
            if created:
                logger.info(f"Fabricante creado: {fabricante_nombre}")
            return fabricante
        except Exception as e:
            logger.error(f"Error al crear fabricante '{fabricante_nombre}': {str(e)}")
            return None
    
    def transform_row(self, row: pd.Series) -> Dict[str, Any]:
        """Transforma una fila a formato de insumo"""
        data = {
            'descripcion': str(row['descripcion']).strip(),
            'deposito': self.deposito,
        }
        
        # Campos opcionales
        if 'precio_unitario' in row and not pd.isna(row['precio_unitario']):
            try:
                data['precio_unitario'] = Decimal(str(row['precio_unitario']))
            except (InvalidOperation, ValueError):
                data['precio_unitario'] = Decimal('0.00')
        
        if 'stock_minimo' in row and not pd.isna(row['stock_minimo']):
            try:
                data['stock_minimo'] = int(float(row['stock_minimo']))
            except (ValueError, TypeError):
                data['stock_minimo'] = 0
        
        if 'stock_actual' in row and not pd.isna(row['stock_actual']):
            try:
                data['stock_actual'] = int(float(row['stock_actual']))
            except (ValueError, TypeError):
                data['stock_actual'] = 0
        
        if 'unidad_medida' in row and not pd.isna(row['unidad_medida']):
            data['unidad_medida'] = str(row['unidad_medida']).strip()
        
        if 'codigo' in row and not pd.isna(row['codigo']):
            data['codigo'] = str(row['codigo']).strip()
        
        # Categoria
        if 'categoria' in row:
            categoria = self.get_or_create_categoria(row['categoria'])
            if categoria:
                data['categoria'] = categoria
        
        # Fabricante
        if 'fabricante' in row:
            fabricante = self.get_or_create_fabricante(row['fabricante'])
            if fabricante:
                data['fabricante'] = fabricante
        
        return data
    
    def import_row(self, row_data: Dict[str, Any]) -> Optional[Insumo]:
        """Crea el insumo en la base de datos"""
        try:
            # Verificar si ya existe (por descripción y depósito)
            descripcion = row_data['descripcion']
            deposito = row_data['deposito']
            
            insumo, created = Insumo.objects.get_or_create(
                descripcion=descripcion,
                deposito=deposito,
                defaults=row_data
            )
            
            if not created:
                # Actualizar campos si el insumo ya existe
                for key, value in row_data.items():
                    if key not in ['descripcion', 'deposito']:
                        setattr(insumo, key, value)
                insumo.save()
                logger.debug(f"Insumo actualizado: {descripcion}")
            else:
                logger.debug(f"Insumo creado: {descripcion}")
            
            return insumo
            
        except Exception as e:
            logger.error(f"Error al importar insumo '{row_data.get('descripcion')}': {str(e)}")
            self.warnings.append(f"No se pudo importar: {row_data.get('descripcion')} - {str(e)}")
            return None
