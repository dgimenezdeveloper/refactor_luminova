"""
URLs para la API REST de LUMINOVA.

Este módulo configura el router de Django REST Framework y define
todas las rutas de la API v1.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from App_LUMINOVA.api.viewsets import (
    # Autenticación
    CustomAuthToken,
    CurrentUserViewSet,
    # Catálogos base
    EmpresaViewSet,
    DepositoViewSet,
    CategoriaProductoTerminadoViewSet,
    CategoriaInsumoViewSet,
    ProveedorViewSet,
    FabricanteViewSet,
    ClienteViewSet,
    EstadoOrdenViewSet,
    SectorAsignadoViewSet,
    # Inventario
    ProductoTerminadoViewSet,
    InsumoViewSet,
    OfertaProveedorViewSet,
    ComponenteProductoViewSet,
    StockInsumoViewSet,
    StockProductoTerminadoViewSet,
    MovimientoStockViewSet,
    # Ventas
    OrdenVentaViewSet,
    ItemOrdenVentaViewSet,
    FacturaViewSet,
    HistorialOVViewSet,
    # Producción
    OrdenProduccionViewSet,
    ReportesViewSet,
    LoteProductoTerminadoViewSet,
    # Compras
    OrdenCompraViewSet,
    # Sistema
    UsuarioDepositoViewSet,
    NotificacionSistemaViewSet,
    AuditoriaAccesoViewSet,
    RolEmpresaViewSet,
)


# =============================================================================
# CONFIGURACIÓN DEL ROUTER
# =============================================================================

router = DefaultRouter()

# Catálogos base
router.register(r'empresas', EmpresaViewSet, basename='empresa')
router.register(r'depositos', DepositoViewSet, basename='deposito')
router.register(r'categorias-producto', CategoriaProductoTerminadoViewSet, basename='categoria-producto')
router.register(r'categorias-insumo', CategoriaInsumoViewSet, basename='categoria-insumo')
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
router.register(r'fabricantes', FabricanteViewSet, basename='fabricante')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'estados-orden', EstadoOrdenViewSet, basename='estado-orden')
router.register(r'sectores', SectorAsignadoViewSet, basename='sector')

# Inventario
router.register(r'productos', ProductoTerminadoViewSet, basename='producto')
router.register(r'insumos', InsumoViewSet, basename='insumo')
router.register(r'ofertas-proveedor', OfertaProveedorViewSet, basename='oferta-proveedor')
router.register(r'componentes-producto', ComponenteProductoViewSet, basename='componente-producto')
router.register(r'stock-insumos', StockInsumoViewSet, basename='stock-insumo')
router.register(r'stock-productos', StockProductoTerminadoViewSet, basename='stock-producto')
router.register(r'movimientos-stock', MovimientoStockViewSet, basename='movimiento-stock')

# Ventas
router.register(r'ordenes-venta', OrdenVentaViewSet, basename='orden-venta')
router.register(r'items-orden-venta', ItemOrdenVentaViewSet, basename='item-orden-venta')
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'historial-ov', HistorialOVViewSet, basename='historial-ov')

# Producción
router.register(r'ordenes-produccion', OrdenProduccionViewSet, basename='orden-produccion')
router.register(r'reportes-produccion', ReportesViewSet, basename='reporte-produccion')
router.register(r'lotes-producto', LoteProductoTerminadoViewSet, basename='lote-producto')

# Compras
router.register(r'ordenes-compra', OrdenCompraViewSet, basename='orden-compra')

# Sistema
router.register(r'usuarios-deposito', UsuarioDepositoViewSet, basename='usuario-deposito')
router.register(r'notificaciones', NotificacionSistemaViewSet, basename='notificacion')
router.register(r'auditorias', AuditoriaAccesoViewSet, basename='auditoria')
router.register(r'roles-empresa', RolEmpresaViewSet, basename='rol-empresa')

# Usuario actual
router.register(r'auth/user', CurrentUserViewSet, basename='current-user')


# =============================================================================
# PATRONES DE URL
# =============================================================================

app_name = 'api'

urlpatterns = [
    # API versión 1
    path('v1/', include(router.urls)),
    
    # Autenticación por token
    path('v1/auth/token/', CustomAuthToken.as_view(), name='api-token-auth'),
    
    # Documentación OpenAPI
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]
