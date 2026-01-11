"""
Sistema base de importación masiva flexible para LUMINOVA
Soporta cualquier tipo de empresa y rubro
"""
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Error de validación durante la importación"""
    pass


class BaseImporter:
    """
    Clase base para importar datos masivos desde CSV/Excel
    Adaptable a cualquier rubro empresarial
    """
    
    # Campos requeridos - debe ser sobrescrito en clases hijas
    REQUIRED_FIELDS: List[str] = []
    
    # Mapeo flexible de nombres de columnas
    FIELD_ALIASES: Dict[str, List[str]] = {}
    
    # Tipos de datos esperados
    FIELD_TYPES: Dict[str, type] = {}
    
    def __init__(self, empresa, deposito=None):
        """
        Args:
            empresa: Instancia del modelo Empresa
            deposito: Instancia del modelo Deposito (opcional)
        """
        self.empresa = empresa
        self.deposito = deposito
        self.errors = []
        self.warnings = []
        self.imported_count = 0
        self.skipped_count = 0
        
    def read_file(self, file_path: str) -> pd.DataFrame:
        """Lee archivo CSV o Excel y retorna DataFrame"""
        try:
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                # Intentar detectar encoding automáticamente
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='latin-1')
            else:
                raise ValueError(f"Formato de archivo no soportado: {file_path}")
            
            logger.info(f"Archivo leído exitosamente: {len(df)} filas")
            return df
            
        except Exception as e:
            logger.error(f"Error al leer archivo: {str(e)}")
            raise ValidationError(f"No se pudo leer el archivo: {str(e)}")
    
    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nombres de columnas usando aliases configurados
        Permite flexibilidad en nombres de columnas del archivo
        """
        # Convertir nombres a minúsculas y eliminar espacios
        df.columns = df.columns.str.strip().str.lower()
        
        # Aplicar aliases
        column_mapping = {}
        for standard_name, aliases in self.FIELD_ALIASES.items():
            for col in df.columns:
                if col in [alias.lower() for alias in aliases]:
                    column_mapping[col] = standard_name
                    break
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
            logger.info(f"Columnas renombradas: {column_mapping}")
        
        return df
    
    def validate_structure(self, df: pd.DataFrame) -> bool:
        """Valida que el DataFrame tenga la estructura mínima requerida"""
        missing_fields = []
        
        for field in self.REQUIRED_FIELDS:
            if field not in df.columns:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Faltan columnas requeridas: {', '.join(missing_fields)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return False
        
        logger.info("Estructura validada correctamente")
        return True
    
    def validate_row(self, row: pd.Series, row_number: int) -> Tuple[bool, Optional[str]]:
        """
        Valida una fila individual
        Debe ser implementado por clases hijas según el tipo de entidad
        
        Returns:
            (is_valid, error_message)
        """
        raise NotImplementedError("validate_row debe ser implementado en clase hija")
    
    def transform_row(self, row: pd.Series) -> Dict[str, Any]:
        """
        Transforma una fila del DataFrame a un diccionario con formato correcto
        Debe ser implementado por clases hijas
        """
        raise NotImplementedError("transform_row debe ser implementado en clase hija")
    
    def import_row(self, row_data: Dict[str, Any]) -> Optional[Any]:
        """
        Importa una fila (crea o actualiza registro en base de datos)
        Debe ser implementado por clases hijas
        
        Returns:
            Instancia del objeto creado/actualizado o None si falló
        """
        raise NotImplementedError("import_row debe ser implementado en clase hija")
    
    def process_dataframe(self, df: pd.DataFrame, update_existing: bool = False) -> Dict[str, Any]:
        """
        Procesa el DataFrame completo
        
        Args:
            df: DataFrame con los datos a importar
            update_existing: Si True, actualiza registros existentes
        
        Returns:
            Diccionario con estadísticas de importación
        """
        # Normalizar nombres de columnas
        df = self.normalize_column_names(df)
        
        # Validar estructura
        if not self.validate_structure(df):
            return {
                'success': False,
                'errors': self.errors,
                'imported': 0,
                'skipped': 0
            }
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            row_number = idx + 2  # +2 porque pandas usa índice 0 y hay header
            
            try:
                # Validar fila
                is_valid, error_msg = self.validate_row(row, row_number)
                if not is_valid:
                    self.errors.append(f"Fila {row_number}: {error_msg}")
                    self.skipped_count += 1
                    continue
                
                # Transformar datos
                row_data = self.transform_row(row)
                
                # Importar
                instance = self.import_row(row_data)
                if instance:
                    self.imported_count += 1
                    logger.debug(f"Fila {row_number} importada correctamente")
                else:
                    self.skipped_count += 1
                    self.warnings.append(f"Fila {row_number}: No se pudo importar")
                    
            except Exception as e:
                error_msg = f"Fila {row_number}: Error inesperado - {str(e)}"
                self.errors.append(error_msg)
                self.skipped_count += 1
                logger.error(error_msg)
        
        return {
            'success': len(self.errors) == 0 or self.imported_count > 0,
            'imported': self.imported_count,
            'skipped': self.skipped_count,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def import_from_file(self, file_path: str, update_existing: bool = False) -> Dict[str, Any]:
        """
        Método principal para importar desde un archivo
        
        Args:
            file_path: Ruta al archivo CSV o Excel
            update_existing: Si True, actualiza registros existentes
        
        Returns:
            Diccionario con resultado de la importación
        """
        try:
            df = self.read_file(file_path)
            result = self.process_dataframe(df, update_existing)
            
            logger.info(f"Importación finalizada: {result['imported']} importados, {result['skipped']} omitidos")
            return result
            
        except Exception as e:
            logger.error(f"Error en importación: {str(e)}")
            return {
                'success': False,
                'imported': 0,
                'skipped': 0,
                'errors': [str(e)],
                'warnings': []
            }
