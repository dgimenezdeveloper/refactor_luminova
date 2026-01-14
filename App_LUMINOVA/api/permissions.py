"""
Permisos personalizados para la API REST de LUMINOVA.

Este módulo define los permisos que garantizan el aislamiento multi-tenant
y controles de acceso granulares para la API.
"""

from rest_framework import permissions


class IsAuthenticatedAndHasEmpresa(permissions.BasePermission):
    """
    Permiso que verifica que el usuario esté autenticado y tenga
    una empresa asignada a través de su perfil.
    """
    message = "Debe estar autenticado y tener una empresa asignada."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar que el usuario tenga un perfil con empresa
        return hasattr(request.user, 'perfil') and request.user.perfil.empresa is not None


class EmpresaScopedPermission(permissions.BasePermission):
    """
    Permiso que asegura que los objetos pertenezcan a la empresa del usuario.
    """
    message = "No tiene permiso para acceder a recursos de otra empresa."

    def has_object_permission(self, request, view, obj):
        # Superusuarios tienen acceso total
        if request.user.is_superuser:
            return True
        
        # Verificar que el usuario tenga empresa
        if not hasattr(request.user, 'perfil') or not request.user.perfil.empresa:
            return False
        
        user_empresa = request.user.perfil.empresa
        
        # Verificar si el objeto tiene empresa directamente
        if hasattr(obj, 'empresa') and obj.empresa is not None:
            return obj.empresa == user_empresa
        
        # Para modelos como Deposito que tienen empresa directa
        if hasattr(obj, 'empresa_id') and obj.empresa_id is not None:
            return obj.empresa_id == user_empresa.id
        
        return True  # Si no tiene empresa, permitir (para catálogos compartidos)


class CanAccessDeposito(permissions.BasePermission):
    """
    Permiso que verifica si el usuario tiene acceso a un depósito específico.
    """
    message = "No tiene permiso para acceder a este depósito."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Determinar el depósito del objeto
        deposito = None
        if hasattr(obj, 'deposito'):
            deposito = obj.deposito
        elif hasattr(obj, 'deposito_origen'):
            deposito = obj.deposito_origen
        
        if deposito is None:
            return True
        
        # Verificar si el usuario tiene asignación a este depósito
        from App_LUMINOVA.models import UsuarioDeposito
        return UsuarioDeposito.objects.filter(
            usuario=request.user,
            deposito=deposito
        ).exists()


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permite lectura a todos los autenticados, pero solo staff puede modificar.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class CanManageStock(permissions.BasePermission):
    """
    Permiso para gestionar movimientos de stock.
    Verifica permisos específicos del UsuarioDeposito.
    """
    message = "No tiene permisos para gestionar stock en este depósito."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Para métodos de lectura, solo verificar autenticación
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return True  # La verificación detallada se hace en has_object_permission

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        from App_LUMINOVA.models import UsuarioDeposito
        
        # Determinar el depósito involucrado
        deposito = None
        if hasattr(obj, 'deposito'):
            deposito = obj.deposito
        elif hasattr(obj, 'deposito_destino'):
            deposito = obj.deposito_destino
        
        if deposito is None:
            return True
        
        try:
            asignacion = UsuarioDeposito.objects.get(
                usuario=request.user,
                deposito=deposito
            )
            
            # Verificar permisos según el tipo de operación
            if hasattr(obj, 'tipo'):
                if obj.tipo == 'entrada':
                    return asignacion.puede_entradas
                elif obj.tipo == 'salida':
                    return asignacion.puede_salidas
                elif obj.tipo == 'transferencia':
                    return asignacion.puede_transferir
            
            return True
            
        except UsuarioDeposito.DoesNotExist:
            return False


class NotificacionPermission(permissions.BasePermission):
    """
    Permiso para notificaciones.
    El usuario puede ver notificaciones de su grupo destino.
    """
    message = "No tiene permiso para acceder a esta notificación."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # El remitente siempre puede ver su notificación
        if obj.remitente == request.user:
            return True
        
        # Verificar si el usuario pertenece al grupo destino
        user_groups = request.user.groups.values_list('name', flat=True)
        
        group_mapping = {
            'compras': ['Compras', 'compras'],
            'ventas': ['Ventas', 'ventas'],
            'deposito': ['Depósito', 'deposito', 'Deposito'],
            'produccion': ['Producción', 'produccion', 'Produccion'],
            'control_calidad': ['Control de Calidad', 'control_calidad'],
            'administrador': ['Administrador', 'administrador', 'Admin'],
            'todos': list(user_groups),  # Todos pueden ver
        }
        
        allowed_groups = group_mapping.get(obj.destinatario_grupo, [])
        
        return any(g in allowed_groups for g in user_groups)


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso que permite al propietario o admin modificar un recurso.
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Verificar propietario según el campo disponible
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user
        elif hasattr(obj, 'remitente'):
            return obj.remitente == request.user
        elif hasattr(obj, 'reportado_por'):
            return obj.reportado_por == request.user
        
        return False
