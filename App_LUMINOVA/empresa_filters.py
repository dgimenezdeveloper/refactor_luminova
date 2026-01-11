"""Filtros y helpers para aislamiento de datos por empresa."""
from django.db.models import Q

from .models import (
    Deposito, Insumo, ProductoTerminado, OrdenVenta, Orden, OrdenProduccion,
    Cliente, Proveedor, Fabricante, CategoriaInsumo, CategoriaProductoTerminado
)


def _filter_queryset_by_empresa(request, queryset, fallback_paths=None):
    """Aplica filtro por empresa incluyendo rutas de respaldo."""
    empresa_actual = getattr(request, 'empresa_actual', None)
    if not empresa_actual:
        return queryset.none()

    condition = Q(empresa=empresa_actual)
    if fallback_paths:
        fallback_condition = Q()
        for path in fallback_paths:
            fallback_condition |= Q(empresa__isnull=True) & Q(**{f"{path}__empresa": empresa_actual})
        condition |= fallback_condition
    return queryset.filter(condition)


def get_depositos_empresa(request):
    """
    Obtiene los depósitos de la empresa actual del usuario
    
    Args:
        request: HttpRequest object con empresa_actual
        
    Returns:
        QuerySet de Deposito filtrado por empresa
    """
    empresa_actual = getattr(request, 'empresa_actual', None)
    if empresa_actual:
        return Deposito.objects.filter(empresa=empresa_actual)
    return Deposito.objects.none()


def filter_insumos_por_empresa(request, queryset=None):
    """
    Filtra insumos por empresa actual
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional, usa Insumo.objects.all() por defecto)
        
    Returns:
        QuerySet de Insumo filtrado
    """
    if queryset is None:
        queryset = Insumo.objects.all()

    return _filter_queryset_by_empresa(request, queryset, fallback_paths=("deposito",))


def filter_productos_por_empresa(request, queryset=None):
    """
    Filtra productos terminados por empresa actual
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de ProductoTerminado filtrado
    """
    if queryset is None:
        queryset = ProductoTerminado.objects.all()

    return _filter_queryset_by_empresa(request, queryset, fallback_paths=("deposito",))


def filter_ordenes_venta_por_empresa(request, queryset=None):
    """
    Filtra órdenes de venta por empresa actual
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de OrdenVenta filtrado
    """
    if queryset is None:
        queryset = OrdenVenta.objects.all()

    return _filter_queryset_by_empresa(
        request,
        queryset.distinct(),
        fallback_paths=("items_ov__producto_terminado__deposito",),
    )


def filter_ordenes_compra_por_empresa(request, queryset=None):
    """
    Filtra órdenes de compra por empresa actual
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de Orden filtrado
    """
    if queryset is None:
        queryset = Orden.objects.filter(tipo='compra')

    return _filter_queryset_by_empresa(request, queryset, fallback_paths=("deposito",))


def filter_ordenes_produccion_por_empresa(request, queryset=None):
    """
    Filtra órdenes de producción por empresa actual
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de OrdenProduccion filtrado
    """
    if queryset is None:
        queryset = OrdenProduccion.objects.all()

    return _filter_queryset_by_empresa(
        request,
        queryset,
        fallback_paths=("producto_a_producir__deposito",),
    )


def filter_clientes_por_empresa(request, queryset=None):
    """
    Filtra clientes por empresa actual (vía órdenes de venta)
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de Cliente filtrado
    """
    if queryset is None:
        queryset = Cliente.objects.all()

    return _filter_queryset_by_empresa(
        request,
        queryset.distinct(),
        fallback_paths=("ordenes_venta__items_ov__producto_terminado__deposito",),
    )


def filter_proveedores_por_empresa(request, queryset=None):
    """
    Filtra proveedores por empresa actual (vía órdenes de compra)
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de Proveedor filtrado
    """
    if queryset is None:
        queryset = Proveedor.objects.all()

    return _filter_queryset_by_empresa(
        request,
        queryset.distinct(),
        fallback_paths=("ordenes_de_compra_a_proveedor__deposito",),
    )


def filter_fabricantes_por_empresa(request, queryset=None):
    """
    Filtra fabricantes por empresa actual (vía insumos)
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de Fabricante filtrado
    """
    if queryset is None:
        queryset = Fabricante.objects.all()

    return _filter_queryset_by_empresa(
        request,
        queryset.distinct(),
        fallback_paths=("insumos__deposito",),
    )


def filter_categorias_insumos_por_empresa(request, queryset=None):
    """
    Filtra categorías de insumos por empresa actual
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de CategoriaInsumo filtrado
    """
    if queryset is None:
        queryset = CategoriaInsumo.objects.all()

    return _filter_queryset_by_empresa(request, queryset, fallback_paths=("deposito",))


def filter_categorias_productos_por_empresa(request, queryset=None):
    """
    Filtra categorías de productos terminados por empresa actual
    
    Args:
        request: HttpRequest object
        queryset: QuerySet base (opcional)
        
    Returns:
        QuerySet de CategoriaProductoTerminado filtrado
    """
    if queryset is None:
        queryset = CategoriaProductoTerminado.objects.all()

    return _filter_queryset_by_empresa(request, queryset, fallback_paths=("deposito",))


# Decorator para vistas que requieren empresa
def require_empresa(view_func):
    """
    Decorator que verifica que el usuario tenga empresa asignada
    
    Usage:
        @require_empresa
        def mi_vista(request):
            # request.empresa_actual está garantizado
            pass
    """
    from functools import wraps
    from django.shortcuts import redirect
    from django.contrib import messages
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'empresa_actual') or request.empresa_actual is None:
            messages.error(request, "No tienes una empresa asignada. Contacta al administrador.")
            return redirect('App_LUMINOVA:dashboard')
        return view_func(request, *args, **kwargs)
    
    return wrapper
