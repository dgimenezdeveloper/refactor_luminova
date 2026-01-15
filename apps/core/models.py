"""
apps.core.models - Re-exportación de modelos base desde App_LUMINOVA

Este módulo re-exporta los modelos de core/infraestructura para facilitar
la migración gradual hacia una arquitectura modular.

Uso recomendado:
    from apps.core.models import Empresa, Deposito, EmpresaScopedModel
    
También funciona (compatibilidad legacy):
    from App_LUMINOVA.models import Empresa, Deposito, EmpresaScopedModel
"""

# Re-exportar modelos de core desde App_LUMINOVA
from App_LUMINOVA.models import (
    # Modelos de tenant (multi-tenancy)
    Empresa,
    Domain,
    
    # Modelo base abstracto
    EmpresaScopedModel,
    
    # Depósitos y permisos
    Deposito,
    UsuarioDeposito,
    
    # Usuarios y roles
    RolEmpresa,
    PerfilUsuario,
    RolDescripcion,
    PasswordChangeRequired,
    
    # Auditoría
    AuditoriaAcceso,
    
    # Historial de importaciones
    HistorialImportacion,
)

__all__ = [
    'Empresa',
    'Domain',
    'EmpresaScopedModel',
    'Deposito',
    'UsuarioDeposito',
    'RolEmpresa',
    'PerfilUsuario',
    'RolDescripcion',
    'PasswordChangeRequired',
    'AuditoriaAcceso',
    'HistorialImportacion',
]
