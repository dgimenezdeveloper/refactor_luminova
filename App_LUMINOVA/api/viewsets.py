"""
ViewSets para la API REST de LUMINOVA.

Este módulo define los ViewSets que exponen las operaciones CRUD
para todos los modelos del sistema, con soporte multi-tenant.
"""

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.utils import timezone
from django.db.models import Sum

from App_LUMINOVA.models import (
    Empresa,
    Deposito,
    CategoriaProductoTerminado,
    CategoriaInsumo,
    ProductoTerminado,
    Insumo,
    Proveedor,
    Fabricante,
    OfertaProveedor,
    ComponenteProducto,
    Cliente,
    OrdenVenta,
    ItemOrdenVenta,
    EstadoOrden,
    SectorAsignado,
    OrdenProduccion,
    Reportes,
    Factura,
    Orden,
    LoteProductoTerminado,
    HistorialOV,
    UsuarioDeposito,
    StockInsumo,
    StockProductoTerminado,
    MovimientoStock,
    NotificacionSistema,
    AuditoriaAcceso,
    RolEmpresa,
)

from .serializers import (
    EmpresaSerializer,
    DepositoSerializer,
    CategoriaProductoTerminadoSerializer,
    CategoriaInsumoSerializer,
    ProductoTerminadoSerializer,
    ProductoTerminadoListSerializer,
    InsumoSerializer,
    ProveedorSerializer,
    FabricanteSerializer,
    OfertaProveedorSerializer,
    ComponenteProductoSerializer,
    ClienteSerializer,
    OrdenVentaSerializer,
    OrdenVentaListSerializer,
    OrdenVentaCreateSerializer,
    ItemOrdenVentaSerializer,
    EstadoOrdenSerializer,
    SectorAsignadoSerializer,
    OrdenProduccionSerializer,
    OrdenProduccionListSerializer,
    OrdenProduccionCreateSerializer,
    ReportesSerializer,
    FacturaSerializer,
    OrdenCompraSerializer,
    OrdenCompraListSerializer,
    LoteProductoTerminadoSerializer,
    HistorialOVSerializer,
    UsuarioDepositoSerializer,
    StockInsumoSerializer,
    StockProductoTerminadoSerializer,
    MovimientoStockSerializer,
    NotificacionSistemaSerializer,
    NotificacionSistemaCreateSerializer,
    AuditoriaAccesoSerializer,
    RolEmpresaSerializer,
    UserDetailSerializer,
)

from .permissions import (
    IsAuthenticatedAndHasEmpresa,
    EmpresaScopedPermission,
    CanAccessDeposito,
    CanManageStock,
    NotificacionPermission,
    IsAdminOrReadOnly,
)

from .filters import (
    ProductoTerminadoFilter,
    InsumoFilter,
    OrdenVentaFilter,
    OrdenProduccionFilter,
    OrdenCompraFilter,
    NotificacionFilter,
    MovimientoStockFilter,
    StockInsumoFilter,
    StockProductoTerminadoFilter,
    ClienteFilter,
    ProveedorFilter,
)


# =============================================================================
# CLASE BASE PARA VIEWSETS CON MULTI-TENANCY
# =============================================================================

class EmpresaScopedViewSet(viewsets.ModelViewSet):
    """
    ViewSet base que filtra automáticamente por la empresa del usuario
    y asigna la empresa al crear nuevos objetos.
    """
    permission_classes = [IsAuthenticated, EmpresaScopedPermission]

    def get_empresa(self):
        """Obtiene la empresa del usuario actual."""
        if hasattr(self.request.user, 'perfil') and self.request.user.perfil:
            return self.request.user.perfil.empresa
        return None

    def get_queryset(self):
        """Filtra el queryset por la empresa del usuario."""
        queryset = super().get_queryset()
        empresa = self.get_empresa()
        
        if empresa and hasattr(queryset.model, 'empresa'):
            return queryset.filter(empresa=empresa)
        
        return queryset

    def perform_create(self, serializer):
        """Asigna automáticamente la empresa al crear un objeto."""
        empresa = self.get_empresa()
        if empresa:
            serializer.save(empresa=empresa)
        else:
            serializer.save()


# =============================================================================
# AUTENTICACIÓN
# =============================================================================

class CustomAuthToken(ObtainAuthToken):
    """
    Vista personalizada para obtener token de autenticación.
    Incluye información adicional del usuario.
    """

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        # Información de empresa
        empresa_info = None
        if hasattr(user, 'perfil') and user.perfil and user.perfil.empresa:
            empresa_info = {
                'id': user.perfil.empresa.id,
                'nombre': user.perfil.empresa.nombre
            }
        
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'empresa': empresa_info
        })


class CurrentUserViewSet(viewsets.GenericViewSet):
    """ViewSet para obtener información del usuario actual."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    def list(self, request):
        """Retorna la información del usuario autenticado."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


# =============================================================================
# VIEWSETS DE CATÁLOGOS BASE
# =============================================================================

class EmpresaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para empresas (solo lectura para usuarios normales).
    Solo muestra la empresa del usuario actual.
    """
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Empresa.objects.all()
        if hasattr(self.request.user, 'perfil') and self.request.user.perfil:
            return Empresa.objects.filter(id=self.request.user.perfil.empresa_id)
        return Empresa.objects.none()


class DepositoViewSet(EmpresaScopedViewSet):
    """ViewSet para depósitos."""
    queryset = Deposito.objects.all()
    serializer_class = DepositoSerializer
    search_fields = ['nombre', 'ubicacion', 'descripcion']
    ordering_fields = ['nombre', 'ubicacion']
    ordering = ['nombre']

    def get_queryset(self):
        empresa = self.get_empresa()
        if empresa:
            return Deposito.objects.filter(empresa=empresa)
        return Deposito.objects.none()

    def perform_create(self, serializer):
        empresa = self.get_empresa()
        if empresa:
            serializer.save(empresa=empresa)


class CategoriaProductoTerminadoViewSet(EmpresaScopedViewSet):
    """ViewSet para categorías de productos terminados."""
    queryset = CategoriaProductoTerminado.objects.all()
    serializer_class = CategoriaProductoTerminadoSerializer
    search_fields = ['nombre']
    filterset_fields = ['deposito']
    ordering = ['nombre']


class CategoriaInsumoViewSet(EmpresaScopedViewSet):
    """ViewSet para categorías de insumos."""
    queryset = CategoriaInsumo.objects.all()
    serializer_class = CategoriaInsumoSerializer
    search_fields = ['nombre']
    filterset_fields = ['deposito']
    ordering = ['nombre']


class ProveedorViewSet(EmpresaScopedViewSet):
    """ViewSet para proveedores."""
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    filterset_class = ProveedorFilter
    search_fields = ['nombre', 'contacto', 'email']
    ordering_fields = ['nombre']
    ordering = ['nombre']


class FabricanteViewSet(EmpresaScopedViewSet):
    """ViewSet para fabricantes."""
    queryset = Fabricante.objects.all()
    serializer_class = FabricanteSerializer
    search_fields = ['nombre', 'contacto', 'email']
    ordering_fields = ['nombre']
    ordering = ['nombre']


class ClienteViewSet(EmpresaScopedViewSet):
    """ViewSet para clientes."""
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    filterset_class = ClienteFilter
    search_fields = ['nombre', 'email', 'telefono', 'direccion']
    ordering_fields = ['nombre']
    ordering = ['nombre']


class EstadoOrdenViewSet(EmpresaScopedViewSet):
    """ViewSet para estados de órdenes de producción."""
    queryset = EstadoOrden.objects.all()
    serializer_class = EstadoOrdenSerializer
    search_fields = ['nombre']
    ordering = ['nombre']


class SectorAsignadoViewSet(EmpresaScopedViewSet):
    """ViewSet para sectores de producción."""
    queryset = SectorAsignado.objects.all()
    serializer_class = SectorAsignadoSerializer
    search_fields = ['nombre']
    ordering = ['nombre']


# =============================================================================
# VIEWSETS DE INVENTARIO
# =============================================================================

class ProductoTerminadoViewSet(EmpresaScopedViewSet):
    """ViewSet para productos terminados."""
    queryset = ProductoTerminado.objects.select_related('categoria', 'deposito').all()
    serializer_class = ProductoTerminadoSerializer
    filterset_class = ProductoTerminadoFilter
    search_fields = ['descripcion', 'modelo', 'material']
    ordering_fields = ['descripcion', 'precio_unitario', 'stock_minimo']
    ordering = ['descripcion']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoTerminadoListSerializer
        return ProductoTerminadoSerializer

    @action(detail=False, methods=['get'])
    def necesitan_reposicion(self, request):
        """Retorna productos que necesitan reposición de stock."""
        queryset = self.get_queryset()
        productos = [p for p in queryset if p.necesita_reposicion]
        serializer = self.get_serializer(productos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stock_por_deposito(self, request, pk=None):
        """Retorna el stock del producto por cada depósito."""
        producto = self.get_object()
        stocks = StockProductoTerminado.objects.filter(producto=producto)
        serializer = StockProductoTerminadoSerializer(stocks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def componentes(self, request, pk=None):
        """Retorna los componentes (BOM) del producto."""
        producto = self.get_object()
        componentes = ComponenteProducto.objects.filter(producto_terminado=producto)
        serializer = ComponenteProductoSerializer(componentes, many=True)
        return Response(serializer.data)


class InsumoViewSet(EmpresaScopedViewSet):
    """ViewSet para insumos."""
    queryset = Insumo.objects.select_related('categoria', 'fabricante', 'deposito').all()
    serializer_class = InsumoSerializer
    filterset_class = InsumoFilter
    search_fields = ['descripcion']
    ordering_fields = ['descripcion']
    ordering = ['descripcion']

    @action(detail=True, methods=['get'])
    def ofertas(self, request, pk=None):
        """Retorna las ofertas de proveedores para este insumo."""
        insumo = self.get_object()
        ofertas = OfertaProveedor.objects.filter(insumo=insumo)
        serializer = OfertaProveedorSerializer(ofertas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stock_por_deposito(self, request, pk=None):
        """Retorna el stock del insumo por cada depósito."""
        insumo = self.get_object()
        stocks = StockInsumo.objects.filter(insumo=insumo)
        serializer = StockInsumoSerializer(stocks, many=True)
        return Response(serializer.data)


class OfertaProveedorViewSet(EmpresaScopedViewSet):
    """ViewSet para ofertas de proveedor."""
    queryset = OfertaProveedor.objects.select_related('insumo', 'proveedor').all()
    serializer_class = OfertaProveedorSerializer
    filterset_fields = ['insumo', 'proveedor']
    search_fields = ['insumo__descripcion', 'proveedor__nombre']
    ordering_fields = ['precio_unitario_compra', 'tiempo_entrega_estimado_dias']
    ordering = ['insumo__descripcion']


class ComponenteProductoViewSet(EmpresaScopedViewSet):
    """ViewSet para componentes de producto (BOM)."""
    queryset = ComponenteProducto.objects.select_related('producto_terminado', 'insumo').all()
    serializer_class = ComponenteProductoSerializer
    filterset_fields = ['producto_terminado', 'insumo']
    ordering = ['producto_terminado__descripcion']


class StockInsumoViewSet(EmpresaScopedViewSet):
    """ViewSet para stock de insumos por depósito."""
    queryset = StockInsumo.objects.select_related('insumo', 'deposito').all()
    serializer_class = StockInsumoSerializer
    filterset_class = StockInsumoFilter
    permission_classes = [IsAuthenticated, CanManageStock]
    ordering = ['insumo__descripcion', 'deposito__nombre']


class StockProductoTerminadoViewSet(EmpresaScopedViewSet):
    """ViewSet para stock de productos terminados por depósito."""
    queryset = StockProductoTerminado.objects.select_related('producto', 'deposito').all()
    serializer_class = StockProductoTerminadoSerializer
    filterset_class = StockProductoTerminadoFilter
    permission_classes = [IsAuthenticated, CanManageStock]
    ordering = ['producto__descripcion', 'deposito__nombre']


class MovimientoStockViewSet(EmpresaScopedViewSet):
    """ViewSet para movimientos de stock."""
    queryset = MovimientoStock.objects.select_related(
        'insumo', 'producto', 'deposito_origen', 'deposito_destino', 'usuario'
    ).all()
    serializer_class = MovimientoStockSerializer
    filterset_class = MovimientoStockFilter
    permission_classes = [IsAuthenticated, CanManageStock]
    ordering = ['-fecha']
    http_method_names = ['get', 'post', 'head', 'options']  # No permitir edición/eliminación

    def perform_create(self, serializer):
        """Asigna el usuario actual al crear un movimiento."""
        empresa = self.get_empresa()
        serializer.save(usuario=self.request.user, empresa=empresa)


# =============================================================================
# VIEWSETS DE VENTAS
# =============================================================================

class OrdenVentaViewSet(EmpresaScopedViewSet):
    """ViewSet para órdenes de venta."""
    queryset = OrdenVenta.objects.select_related('cliente').prefetch_related('items_ov').all()
    serializer_class = OrdenVentaSerializer
    filterset_class = OrdenVentaFilter
    search_fields = ['numero_ov', 'cliente__nombre', 'notas']
    ordering_fields = ['numero_ov', 'fecha_creacion', 'total_ov', 'estado']
    ordering = ['-fecha_creacion']

    def get_serializer_class(self):
        if self.action == 'list':
            return OrdenVentaListSerializer
        elif self.action == 'create':
            return OrdenVentaCreateSerializer
        return OrdenVentaSerializer

    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Retorna el historial de la orden de venta."""
        orden = self.get_object()
        historial = HistorialOV.objects.filter(orden_venta=orden)
        serializer = HistorialOVSerializer(historial, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def ordenes_produccion(self, request, pk=None):
        """Retorna las órdenes de producción asociadas."""
        orden = self.get_object()
        ops = OrdenProduccion.objects.filter(orden_venta_origen=orden)
        serializer = OrdenProduccionListSerializer(ops, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """Confirma una orden de venta pendiente."""
        orden = self.get_object()
        if orden.estado != 'PENDIENTE':
            return Response(
                {'error': 'Solo se pueden confirmar órdenes pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        orden.estado = 'CONFIRMADA'
        orden.save()
        return Response({'status': 'Orden confirmada'})


class ItemOrdenVentaViewSet(EmpresaScopedViewSet):
    """ViewSet para items de órdenes de venta."""
    queryset = ItemOrdenVenta.objects.select_related('orden_venta', 'producto_terminado').all()
    serializer_class = ItemOrdenVentaSerializer
    filterset_fields = ['orden_venta', 'producto_terminado']
    ordering = ['orden_venta__numero_ov']


class FacturaViewSet(EmpresaScopedViewSet):
    """ViewSet para facturas."""
    queryset = Factura.objects.select_related('orden_venta').all()
    serializer_class = FacturaSerializer
    search_fields = ['numero_factura', 'orden_venta__numero_ov']
    ordering_fields = ['numero_factura', 'fecha_emision', 'total_facturado']
    ordering = ['-fecha_emision']
    http_method_names = ['get', 'post', 'head', 'options']  # Solo lectura y creación


class HistorialOVViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """ViewSet para historial de órdenes de venta (solo lectura)."""
    queryset = HistorialOV.objects.select_related('orden_venta', 'realizado_por').all()
    serializer_class = HistorialOVSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['orden_venta', 'tipo_evento']
    ordering = ['-fecha_evento']


# =============================================================================
# VIEWSETS DE PRODUCCIÓN
# =============================================================================

class OrdenProduccionViewSet(EmpresaScopedViewSet):
    """ViewSet para órdenes de producción."""
    queryset = OrdenProduccion.objects.select_related(
        'producto_a_producir', 'estado_op', 'sector_asignado_op', 'orden_venta_origen'
    ).all()
    serializer_class = OrdenProduccionSerializer
    filterset_class = OrdenProduccionFilter
    search_fields = ['numero_op', 'producto_a_producir__descripcion', 'notas']
    ordering_fields = ['numero_op', 'fecha_solicitud', 'cantidad_a_producir']
    ordering = ['-fecha_solicitud']

    def get_serializer_class(self):
        if self.action == 'list':
            return OrdenProduccionListSerializer
        elif self.action == 'create':
            return OrdenProduccionCreateSerializer
        return OrdenProduccionSerializer

    @action(detail=False, methods=['get'])
    def para_stock(self, request):
        """Retorna solo órdenes de producción para stock (MTS)."""
        queryset = self.get_queryset().filter(tipo_orden='MTS')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def bajo_demanda(self, request):
        """Retorna solo órdenes de producción bajo demanda (MTO)."""
        queryset = self.get_queryset().filter(tipo_orden='MTO')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def iniciar(self, request, pk=None):
        """Inicia una orden de producción."""
        op = self.get_object()
        # Buscar o crear estado "En Proceso"
        empresa = self.get_empresa()
        estado, _ = EstadoOrden.objects.get_or_create(
            nombre='En Proceso', 
            empresa=empresa
        )
        op.estado_op = estado
        op.fecha_inicio_real = timezone.now()
        op.save()
        return Response({'status': 'Producción iniciada'})

    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        """Completa una orden de producción."""
        op = self.get_object()
        empresa = self.get_empresa()
        estado, _ = EstadoOrden.objects.get_or_create(
            nombre='Completada', 
            empresa=empresa
        )
        op.estado_op = estado
        op.fecha_fin_real = timezone.now()
        op.save()
        return Response({'status': 'Producción completada'})

    @action(detail=True, methods=['get'])
    def lotes(self, request, pk=None):
        """Retorna los lotes producidos por esta OP."""
        op = self.get_object()
        lotes = LoteProductoTerminado.objects.filter(op_asociada=op)
        serializer = LoteProductoTerminadoSerializer(lotes, many=True)
        return Response(serializer.data)


class ReportesViewSet(EmpresaScopedViewSet):
    """ViewSet para reportes de incidencias."""
    queryset = Reportes.objects.select_related(
        'orden_produccion_asociada', 'reportado_por', 'sector_reporta'
    ).all()
    serializer_class = ReportesSerializer
    filterset_fields = ['orden_produccion_asociada', 'resuelto', 'tipo_problema']
    search_fields = ['n_reporte', 'tipo_problema', 'informe_reporte']
    ordering = ['-fecha']

    def perform_create(self, serializer):
        """Asigna el usuario que reporta y genera número."""
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        empresa = self.get_empresa()
        serializer.save(
            reportado_por=self.request.user,
            n_reporte=f"REP-{timestamp}",
            empresa=empresa
        )

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        """Marca un reporte como resuelto."""
        reporte = self.get_object()
        reporte.resuelto = True
        reporte.fecha_resolucion = timezone.now()
        reporte.save()
        return Response({'status': 'Reporte marcado como resuelto'})


class LoteProductoTerminadoViewSet(EmpresaScopedViewSet):
    """ViewSet para lotes de productos terminados."""
    queryset = LoteProductoTerminado.objects.select_related(
        'producto', 'op_asociada', 'deposito'
    ).all()
    serializer_class = LoteProductoTerminadoSerializer
    filterset_fields = ['producto', 'op_asociada', 'deposito', 'enviado']
    ordering = ['-fecha_creacion']


# =============================================================================
# VIEWSETS DE COMPRAS
# =============================================================================

class OrdenCompraViewSet(EmpresaScopedViewSet):
    """ViewSet para órdenes de compra."""
    queryset = Orden.objects.select_related('proveedor', 'insumo_principal', 'deposito').all()
    serializer_class = OrdenCompraSerializer
    filterset_class = OrdenCompraFilter
    search_fields = ['numero_orden', 'proveedor__nombre', 'notas']
    ordering_fields = ['numero_orden', 'fecha_creacion', 'total_orden_compra']
    ordering = ['-fecha_creacion']

    def get_serializer_class(self):
        if self.action == 'list':
            return OrdenCompraListSerializer
        return OrdenCompraSerializer

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprueba una orden de compra."""
        orden = self.get_object()
        if orden.estado != 'BORRADOR':
            return Response(
                {'error': 'Solo se pueden aprobar órdenes en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        orden.estado = 'APROBADA'
        orden.save()
        return Response({'status': 'Orden aprobada'})

    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        """Marca la orden como enviada al proveedor."""
        orden = self.get_object()
        if orden.estado != 'APROBADA':
            return Response(
                {'error': 'Solo se pueden enviar órdenes aprobadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        orden.estado = 'ENVIADA_PROVEEDOR'
        orden.save()
        return Response({'status': 'Orden enviada al proveedor'})

    @action(detail=True, methods=['post'])
    def recibir(self, request, pk=None):
        """Marca la orden como recibida."""
        orden = self.get_object()
        orden.estado = 'RECIBIDA_TOTAL'
        orden.save()
        return Response({'status': 'Orden marcada como recibida'})


# =============================================================================
# VIEWSETS DE SISTEMA
# =============================================================================

class UsuarioDepositoViewSet(EmpresaScopedViewSet):
    """ViewSet para asignaciones usuario-depósito."""
    queryset = UsuarioDeposito.objects.select_related('usuario', 'deposito').all()
    serializer_class = UsuarioDepositoSerializer
    filterset_fields = ['usuario', 'deposito', 'puede_transferir', 'puede_entradas', 'puede_salidas']
    ordering = ['usuario__username', 'deposito__nombre']


class NotificacionSistemaViewSet(EmpresaScopedViewSet):
    """ViewSet para notificaciones del sistema."""
    queryset = NotificacionSistema.objects.select_related('remitente').all()
    serializer_class = NotificacionSistemaSerializer
    filterset_class = NotificacionFilter
    permission_classes = [IsAuthenticated, NotificacionPermission]
    search_fields = ['titulo', 'mensaje']
    ordering = ['-fecha_creacion']

    def get_serializer_class(self):
        if self.action == 'create':
            return NotificacionSistemaCreateSerializer
        return NotificacionSistemaSerializer

    def perform_create(self, serializer):
        """Asigna el remitente como usuario actual."""
        empresa = self.get_empresa()
        serializer.save(remitente=self.request.user, empresa=empresa)

    @action(detail=False, methods=['get'])
    def no_leidas(self, request):
        """Retorna solo notificaciones no leídas."""
        queryset = self.get_queryset().filter(leida=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def contador(self, request):
        """Retorna el conteo de notificaciones por estado."""
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'no_leidas': queryset.filter(leida=False).count(),
            'no_atendidas': queryset.filter(atendida=False).count(),
            'criticas': queryset.filter(prioridad='critica', leida=False).count()
        })

    @action(detail=True, methods=['post'])
    def marcar_leida(self, request, pk=None):
        """Marca una notificación como leída."""
        notificacion = self.get_object()
        notificacion.marcar_como_leida(request.user)
        return Response({'status': 'Notificación marcada como leída'})

    @action(detail=True, methods=['post'])
    def marcar_atendida(self, request, pk=None):
        """Marca una notificación como atendida."""
        notificacion = self.get_object()
        notificacion.marcar_como_atendida(request.user)
        return Response({'status': 'Notificación marcada como atendida'})

    @action(detail=False, methods=['post'])
    def marcar_todas_leidas(self, request):
        """Marca todas las notificaciones como leídas."""
        queryset = self.get_queryset().filter(leida=False)
        count = queryset.count()
        queryset.update(leida=True, fecha_lectura=timezone.now())
        return Response({'status': f'{count} notificaciones marcadas como leídas'})


class AuditoriaAccesoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """ViewSet para auditorías de acceso (solo lectura)."""
    queryset = AuditoriaAcceso.objects.select_related('usuario', 'empresa').all()
    serializer_class = AuditoriaAccesoSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['usuario', 'accion']
    search_fields = ['accion', 'usuario__username']
    ordering = ['-fecha_hora']

    def get_queryset(self):
        """Filtra por empresa del usuario."""
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        if hasattr(self.request.user, 'perfil') and self.request.user.perfil:
            return queryset.filter(empresa=self.request.user.perfil.empresa)
        return queryset.none()


class RolEmpresaViewSet(EmpresaScopedViewSet):
    """ViewSet para roles de empresa."""
    queryset = RolEmpresa.objects.select_related('empresa', 'group').all()
    serializer_class = RolEmpresaSerializer
    filterset_fields = ['empresa']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']
