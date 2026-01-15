"""
Base Repository y Service classes para el patrón Repository + Service Layer.

Este módulo proporciona las clases base abstractas que deben ser heredadas
por los repositorios y servicios específicos de cada dominio.

Patrón implementado:
- Repository: Abstrae el acceso a datos (ORM Django)
- Service: Contiene la lógica de negocio y coordina repositorios
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from django.db import models
from django.db.models import QuerySet

# Type variable para modelos genéricos
T = TypeVar('T', bound=models.Model)


class BaseRepository(ABC, Generic[T]):
    """
    Repositorio base abstracto que define la interfaz para operaciones CRUD.
    
    Proporciona una capa de abstracción sobre el ORM de Django para:
    - Desacoplar la lógica de negocio del acceso a datos
    - Facilitar testing con mocks
    - Centralizar queries comunes
    
    Uso:
        class ProductoRepository(BaseRepository[ProductoTerminado]):
            model = ProductoTerminado
    """
    
    model: type[T] = None
    
    def __init__(self, empresa=None):
        """
        Inicializa el repositorio con contexto de empresa opcional.
        
        Args:
            empresa: Instancia de Empresa para filtrar por tenant
        """
        if self.model is None:
            raise NotImplementedError("La clase hija debe definir 'model'")
        self.empresa = empresa
    
    def _get_base_queryset(self) -> QuerySet[T]:
        """Retorna el queryset base, filtrado por empresa si aplica."""
        qs = self.model.objects.all()
        if self.empresa and hasattr(self.model, 'empresa'):
            qs = qs.filter(empresa=self.empresa)
        return qs
    
    def get_all(self) -> QuerySet[T]:
        """Obtiene todos los registros."""
        return self._get_base_queryset()
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Obtiene un registro por ID."""
        try:
            return self._get_base_queryset().get(pk=id)
        except self.model.DoesNotExist:
            return None
    
    def get_by_ids(self, ids: List[int]) -> QuerySet[T]:
        """Obtiene múltiples registros por lista de IDs."""
        return self._get_base_queryset().filter(pk__in=ids)
    
    def filter(self, **kwargs) -> QuerySet[T]:
        """Filtra registros por criterios."""
        return self._get_base_queryset().filter(**kwargs)
    
    def exists(self, **kwargs) -> bool:
        """Verifica si existen registros que cumplan los criterios."""
        return self._get_base_queryset().filter(**kwargs).exists()
    
    def count(self, **kwargs) -> int:
        """Cuenta registros que cumplan los criterios."""
        qs = self._get_base_queryset()
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs.count()
    
    def create(self, **kwargs) -> T:
        """Crea un nuevo registro."""
        if self.empresa and 'empresa' not in kwargs:
            kwargs['empresa'] = self.empresa
        return self.model.objects.create(**kwargs)
    
    def bulk_create(self, instances: List[T], batch_size: int = 1000) -> List[T]:
        """Crea múltiples registros en lote."""
        if self.empresa:
            for instance in instances:
                if hasattr(instance, 'empresa') and not instance.empresa_id:
                    instance.empresa = self.empresa
        return self.model.objects.bulk_create(instances, batch_size=batch_size)
    
    def update(self, instance: T, **kwargs) -> T:
        """Actualiza un registro existente."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance
    
    def bulk_update(self, instances: List[T], fields: List[str], batch_size: int = 1000) -> int:
        """Actualiza múltiples registros en lote."""
        return self.model.objects.bulk_update(instances, fields, batch_size=batch_size)
    
    def delete(self, instance: T) -> bool:
        """Elimina un registro."""
        instance.delete()
        return True
    
    def delete_by_id(self, id: int) -> bool:
        """Elimina un registro por ID."""
        return self._get_base_queryset().filter(pk=id).delete()[0] > 0


class BaseService(ABC):
    """
    Servicio base abstracto que define la interfaz para lógica de negocio.
    
    Los servicios coordinan repositorios y contienen la lógica de negocio.
    No deben acceder directamente al ORM, sino a través de repositorios.
    
    Uso:
        class InventoryService(BaseService):
            def __init__(self, producto_repo: ProductoRepository):
                self.producto_repo = producto_repo
    """
    
    def __init__(self, empresa=None):
        """
        Inicializa el servicio con contexto de empresa opcional.
        
        Args:
            empresa: Instancia de Empresa para operaciones multi-tenant
        """
        self.empresa = empresa
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida datos de entrada antes de procesar.
        
        Args:
            data: Diccionario con datos a validar
            
        Returns:
            Diccionario con datos validados/normalizados
            
        Raises:
            ValidationError: Si los datos no son válidos
        """
        pass


class ServiceResult:
    """
    Clase para encapsular el resultado de operaciones de servicio.
    
    Proporciona una forma consistente de retornar resultados con:
    - Estado de éxito/error
    - Datos del resultado
    - Mensajes de error
    """
    
    def __init__(
        self, 
        success: bool, 
        data: Any = None, 
        errors: List[str] = None,
        message: str = ""
    ):
        self.success = success
        self.data = data
        self.errors = errors or []
        self.message = message
    
    @classmethod
    def ok(cls, data: Any = None, message: str = "") -> 'ServiceResult':
        """Crea un resultado exitoso."""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def fail(cls, errors: List[str] = None, message: str = "") -> 'ServiceResult':
        """Crea un resultado fallido."""
        return cls(success=False, errors=errors, message=message)
    
    def __bool__(self):
        return self.success
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario."""
        return {
            'success': self.success,
            'data': self.data,
            'errors': self.errors,
            'message': self.message
        }
