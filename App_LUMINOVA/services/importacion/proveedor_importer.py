"""
Importador de Proveedores - Adaptable a cualquier rubro
"""
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import logging

from .base_importer import BaseImporter, ValidationError
from App_LUMINOVA.models import Proveedor

logger = logging.getLogger(__name__)


class ProveedorImporter(BaseImporter):
    """
    Importador de proveedores
    Flexible para cualquier tipo de empresa
    """
    
    REQUIRED_FIELDS = ['nombre']
    
    FIELD_ALIASES = {
        'nombre': ['nombre', 'proveedor', 'razon_social', 'razón social', 'empresa', 'supplier', 'name'],
        'contacto': ['contacto', 'persona_contacto', 'contact', 'representante'],
        'telefono': ['telefono', 'teléfono', 'tel', 'celular', 'phone', 'movil'],
        'email': ['email', 'correo', 'e-mail', 'mail', 'correo_electronico'],
    }
    
    def __init__(self, empresa, deposito=None):
        super().__init__(empresa, deposito)
        self.updated_count = 0
    
    def validate_row(self, row: pd.Series, row_number: int) -> Tuple[bool, Optional[str]]:
        """Valida una fila de proveedor"""
        # Nombre es obligatorio
        if pd.isna(row.get('nombre')) or str(row.get('nombre')).strip() == '':
            return False, "Nombre es obligatorio"
        
        # Validar email si existe
        if 'email' in row and not pd.isna(row['email']):
            email = str(row['email']).strip()
            if email and '@' not in email:
                return False, f"Email inválido: {email}"
        
        return True, None
    
    def transform_row(self, row: pd.Series) -> Dict[str, Any]:
        """Transforma una fila a formato de proveedor"""
        data = {
            'nombre': str(row['nombre']).strip(),
            'empresa': self.empresa,
        }
        
        # Contacto
        if 'contacto' in row and not pd.isna(row['contacto']):
            data['contacto'] = str(row['contacto']).strip()
        else:
            data['contacto'] = ''
        
        # Teléfono
        if 'telefono' in row and not pd.isna(row['telefono']):
            data['telefono'] = str(row['telefono']).strip()
        else:
            data['telefono'] = ''
        
        # Email
        if 'email' in row and not pd.isna(row['email']):
            email = str(row['email']).strip()
            data['email'] = email if email else None
        else:
            data['email'] = None
        
        return data
    
    def import_row(self, row_data: Dict[str, Any]) -> Optional[Proveedor]:
        """Crea el proveedor en la base de datos"""
        try:
            nombre = row_data['nombre']
            empresa = row_data['empresa']
            
            # Verificar si ya existe (por nombre y empresa)
            proveedor, created = Proveedor.objects.get_or_create(
                nombre=nombre,
                empresa=empresa,
                defaults=row_data
            )
            
            if not created:
                # Actualizar campos si el proveedor ya existe
                for key, value in row_data.items():
                    if key not in ['nombre', 'empresa']:
                        setattr(proveedor, key, value)
                proveedor.save()
                self.updated_count += 1
                logger.debug(f"Proveedor actualizado: {nombre}")
            else:
                logger.debug(f"Proveedor creado: {nombre}")
            
            return proveedor
            
        except Exception as e:
            logger.error(f"Error al importar proveedor '{row_data.get('nombre')}': {str(e)}")
            self.warnings.append(f"No se pudo importar: {row_data.get('nombre')} - {str(e)}")
            return None
    
    def import_from_file(self, file_path: str, update_existing: bool = False) -> Dict[str, Any]:
        """Método principal para importar desde un archivo"""
        result = super().import_from_file(file_path, update_existing)
        result['updated'] = self.updated_count
        return result
