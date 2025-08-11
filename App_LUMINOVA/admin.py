# TP_LUMINOVA-main/App_LUMINOVA/admin.py


from django.contrib import admin, messages

from .models import (  # Usando tus nombres actuales para EstadoOrden y SectorAsignado
    AuditoriaAcceso,
    CategoriaInsumo,
    CategoriaProductoTerminado,
    Cliente,
    ComponenteProducto,
    EstadoOrden,
    Fabricante,
    Factura,
    Insumo,
    ItemOrdenVenta,
    OfertaProveedor,
    Orden,
    OrdenProduccion,
    OrdenVenta,
    ProductoTerminado,
    Proveedor,
    Reportes,
    RolDescripcion,
    SectorAsignado,
    Deposito,
    UsuarioDeposito,
    StockInsumo,
    StockProductoTerminado,
    MovimientoStock,
    NotificacionSistema,
)


class OfertaProveedorInline(admin.TabularInline):  # O admin.StackedInline
    model = OfertaProveedor
    extra = 1
    fields = (
        "proveedor",
        "precio_unitario_compra",
        "tiempo_entrega_estimado_dias",
        "fecha_actualizacion_precio",
    )
    autocomplete_fields = ["proveedor"]
    verbose_name = "Oferta de Proveedor"
    verbose_name_plural = "Ofertas de Proveedores para este Insumo"


class ComponenteProductoInline(admin.TabularInline):
    model = ComponenteProducto
    extra = 1
    autocomplete_fields = ["insumo"]
    verbose_name_plural = "Componentes Requeridos para este Producto (BOM)"
    fields = ("insumo", "cantidad_necesaria")


@admin.register(ProductoTerminado)
class ProductoTerminadoAdmin(admin.ModelAdmin):
    list_display = (
        "descripcion", 
        "categoria", 
        "stock", 
        "stock_minimo", 
        "stock_objetivo", 
        "produccion_habilitada",
        "estado_stock",
        "precio_unitario", 
        "modelo",
        "deposito"
    )
    list_filter = ("categoria", "produccion_habilitada", "deposito")
    search_fields = ("descripcion", "modelo")
    inlines = [ComponenteProductoInline]
    autocomplete_fields = ["categoria", "deposito"]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('descripcion', 'categoria', 'modelo', 'precio_unitario', 'deposito')
        }),
        ('Características', {
            'fields': ('potencia', 'acabado', 'color_luz', 'material', 'imagen'),
            'classes': ('collapse',)
        }),
        ('Gestión de Stock', {
            'fields': ('stock', 'stock_minimo', 'stock_objetivo', 'produccion_habilitada'),
            'description': 'Configure los niveles de stock para producción automática'
        }),
    )
    
    def estado_stock(self, obj):
        """Muestra el estado del stock del producto"""
        if obj.stock == 0:
            return "🔴 Sin Stock"
        elif obj.necesita_reposicion:
            return "🟡 Stock Bajo"
        elif obj.stock > obj.stock_objetivo:
            return "🔵 Sobre Stock"
        else:
            return "🟢 Normal"
    estado_stock.short_description = "Estado Stock"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('categoria', 'deposito')


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = (
        "descripcion",
        "categoria",
        "stock",
        "fabricante",
        "mostrar_ofertas_resumen",
    )  # 'mostrar_ofertas_resumen' es el nombre del método
    list_filter = ("categoria", "fabricante")
    search_fields = ("descripcion", "fabricante", "categoria__nombre")
    autocomplete_fields = ["categoria"]
    inlines = [OfertaProveedorInline]

    # No necesitas @admin.display aquí si el método está en la clase ModelAdmin
    def mostrar_ofertas_resumen(self, obj):
        # 'obj' aquí es una instancia del modelo Insumo
        ofertas = (
            obj.ofertas_de_proveedores.all()
        )  # Usando el related_name de OfertaProveedor.insumo
        if not ofertas:
            return "Ninguna"

        resumen = []
        for o in ofertas[:3]:  # Mostrar hasta 3 ofertas
            resumen.append(
                f"{o.proveedor.nombre}: ${o.precio_unitario_compra} ({o.tiempo_entrega_estimado_dias}d)"
            )

        if ofertas.count() > 3:
            resumen.append("...")

        return ", ".join(resumen)

    mostrar_ofertas_resumen.short_description = (
        "Ofertas de Proveedores (Resumen)"  # Esto sí es útil para el
    )


class ItemOrdenVentaInline(admin.TabularInline):
    model = ItemOrdenVenta
    fields = ("producto_terminado", "cantidad", "precio_unitario_venta", "subtotal")
    readonly_fields = ("subtotal",)
    extra = 1
    autocomplete_fields = ["producto_terminado"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "producto_terminado":
            kwargs["queryset"] = ProductoTerminado.objects.order_by("descripcion")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(OrdenVenta)
class OrdenVentaAdmin(admin.ModelAdmin):
    list_display = ("numero_ov", "cliente", "fecha_creacion", "estado", "total_ov")
    list_filter = ("estado", "fecha_creacion", "cliente")
    search_fields = ("numero_ov", "cliente__nombre")
    inlines = [ItemOrdenVentaInline]
    readonly_fields = ("fecha_creacion", "total_ov")


@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    list_display = (
        "numero_op",
        "tipo_orden",
        "producto_a_producir",
        "cantidad_a_producir",
        "get_estado_op_nombre",
        "get_sector_asignado_nombre",
        "get_origen_display",
        "fecha_solicitud",
    )
    list_filter = ("tipo_orden", "estado_op", "sector_asignado_op", "fecha_solicitud")
    search_fields = (
        "numero_op",
        "producto_a_producir__descripcion",
        "orden_venta_origen__numero_ov",
    )
    autocomplete_fields = [
        "producto_a_producir",
        "orden_venta_origen",
        "estado_op",
        "sector_asignado_op",
    ]
    readonly_fields = ("fecha_solicitud",)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_op', 'tipo_orden', 'producto_a_producir', 'cantidad_a_producir')
        }),
        ('Origen y Estado', {
            'fields': ('orden_venta_origen', 'estado_op', 'sector_asignado_op'),
            'description': 'Para órdenes MTO (bajo demanda) debe seleccionar una Orden de Venta origen. Para órdenes MTS (para stock) deje este campo vacío.'
        }),
        ('Planificación', {
            'fields': ('fecha_inicio_planificada', 'fecha_fin_planificada', 'fecha_inicio_real', 'fecha_fin_real'),
            'classes': ('collapse',)
        }),
        ('Notas', {
            'fields': ('notas',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description="Estado")
    def get_estado_op_nombre(self, obj):
        return obj.estado_op.nombre if obj.estado_op else "-"

    @admin.display(description="Sector Asignado")
    def get_sector_asignado_nombre(self, obj):
        return obj.sector_asignado_op.nombre if obj.sector_asignado_op else "-"
    
    @admin.display(description="Origen")
    def get_origen_display(self, obj):
        if obj.tipo_orden == 'MTO' and obj.orden_venta_origen:
            return f"OV: {obj.orden_venta_origen.numero_ov}"
        elif obj.tipo_orden == 'MTS':
            return "Para Stock"
        else:
            return "-"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'producto_a_producir', 'orden_venta_origen', 'estado_op', 'sector_asignado_op'
        )


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    search_fields = ("nombre", "email")


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(CategoriaInsumo)
class CategoriaInsumoAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(CategoriaProductoTerminado)
class CategoriaProductoTerminadoAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(EstadoOrden)
class EstadoOrdenAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(SectorAsignado)
class SectorAsignadoAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


# Registros simples
admin.site.register(Reportes)
admin.site.register(Factura)
admin.site.register(RolDescripcion)
admin.site.register(AuditoriaAcceso)
# admin.site.register(CategoriaProductoTerminado)
# admin.site.register(Proveedor)

admin.site.register(
    ComponenteProducto
)  # Descomentado, puede ser útil para verlos todos
admin.site.register(Fabricante)
# admin.site.register(Orden) # Descomenta y configura si quieres 'Orden' en el admin


# Si quieres un admin más detallado para Orden (Órdenes de Compra)
@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = (
        "numero_orden",
        "tipo",
        "proveedor",
        "insumo_principal",
        "cantidad_principal",
        "estado",
        "fecha_creacion",
        "total_orden_compra",
    )
    list_filter = ("tipo", "estado", "proveedor", "fecha_creacion")
    search_fields = (
        "numero_orden",
        "proveedor__nombre",
        "insumo_principal__descripcion",
        "notas",
    )
    autocomplete_fields = ["proveedor", "insumo_principal"]
    readonly_fields = ("fecha_creacion", "total_orden_compra")

    actions = ["marcar_como_enviada_a_proveedor", "marcar_como_en_transito_y_notificar"]

    def get_readonly_fields(self, request, obj=None):
        # Hacer que ciertos campos sean editables solo en estados específicos
        readonly = list(self.readonly_fields)
        if obj:  # Si el objeto ya existe
            # Los campos de tracking y fecha de entrega solo son editables cuando el pedido fue enviado al proveedor
            if obj.estado != "ENVIADA_PROVEEDOR":
                readonly.extend(["numero_tracking", "fecha_estimada_entrega"])
            # Una vez que la OC está en tránsito o más allá, no se debería poder cambiar el proveedor, insumo, etc.
            if obj.estado not in ["BORRADOR", "APROBADA"]:
                readonly.extend(
                    [
                        "proveedor",
                        "insumo_principal",
                        "cantidad_principal",
                        "precio_unitario_compra",
                    ]
                )
        return tuple(readonly)

    @admin.action(
        description='Marcar seleccionadas como "Gestionada (Enviada a Proveedor)"'
    )
    def marcar_como_enviada_a_proveedor(self, request, queryset):
        # Filtra solo las que están en estado 'Aprobada'
        actualizadas = queryset.filter(estado="APROBADA").update(
            estado="ENVIADA_PROVEEDOR"
        )
        self.message_user(
            request,
            f"{actualizadas} órdenes de compra han sido marcadas como enviadas al proveedor.",
            messages.SUCCESS,
        )

    @admin.action(
        description='Marcar seleccionadas como "En Tránsito" (requiere tracking)'
    )
    def marcar_como_en_transito_y_notificar(self, request, queryset):
        # Filtra las que están listas para pasar a tránsito y tienen un tracking asignado
        listas_para_transito = (
            queryset.filter(estado="ENVIADA_PROVEEDOR")
            .exclude(numero_tracking__exact="")
            .exclude(numero_tracking__isnull=True)
        )

        actualizadas = listas_para_transito.update(estado="EN_TRANSITO")

        if actualizadas > 0:
            self.message_user(
                request,
                f'{actualizadas} órdenes de compra han sido marcadas como "En Tránsito".',
                messages.SUCCESS,
            )

        fallidas = queryset.count() - actualizadas
        if fallidas > 0:
            self.message_user(
                request,
                f'{fallidas} órdenes no se actualizaron. Asegúrese de que estén en estado "Gestionada" y tengan un número de tracking guardado antes de ejecutar esta acción.',
                messages.WARNING,
            )

    fieldsets = (
        (None, {"fields": ("numero_orden", "tipo", "estado")}),
        (
            "Detalles del Proveedor y Pedido",
            {
                "fields": (
                    "proveedor",
                    "insumo_principal",
                    "cantidad_principal",
                    "precio_unitario_compra",
                )
            },
        ),
        (
            'Seguimiento y Entrega (Editable cuando la OC es "Gestionada")',
            {"fields": ("fecha_estimada_entrega", "numero_tracking")},
        ),
        (
            "Información Adicional",
            {"fields": ("notas", "total_orden_compra", "fecha_creacion")},
        ),
    )


from .models import LoteProductoTerminado


@admin.register(LoteProductoTerminado)
class LoteProductoTerminadoAdmin(admin.ModelAdmin):
    list_display = ("producto", "op_asociada", "cantidad", "enviado", "fecha_creacion")
    list_filter = ("enviado", "producto")
    search_fields = ("producto__descripcion", "op_asociada__numero_op")


@admin.register(Deposito)
class DepositoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "descripcion")
    search_fields = ("nombre", "ubicacion")


@admin.register(UsuarioDeposito)
class UsuarioDepositoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "deposito", "puede_transferir", "puede_entradas", "puede_salidas", "fecha_asignacion")
    list_filter = ("puede_transferir", "puede_entradas", "puede_salidas", "deposito")
    search_fields = ("usuario__username", "deposito__nombre")
    autocomplete_fields = ["usuario", "deposito"]
    fieldsets = (
        (None, {
            'fields': ('usuario', 'deposito')
        }),
        ('Permisos', {
            'fields': ('puede_transferir', 'puede_entradas', 'puede_salidas'),
            'description': 'Configure los permisos específicos del usuario para este depósito.'
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario', 'deposito')


@admin.register(StockInsumo)
class StockInsumoAdmin(admin.ModelAdmin):
    list_display = ("insumo", "deposito", "cantidad")
    search_fields = ("insumo__descripcion", "deposito__nombre")


@admin.register(StockProductoTerminado)
class StockProductoTerminadoAdmin(admin.ModelAdmin):
    list_display = ("producto", "deposito", "cantidad")
    search_fields = ("producto__descripcion", "deposito__nombre")


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ("insumo", "producto", "deposito_origen", "deposito_destino", "cantidad", "tipo", "fecha", "usuario")
    list_filter = ("tipo", "fecha", "deposito_origen", "deposito_destino")
    search_fields = ("insumo__descripcion", "producto__descripcion", "usuario__username")


@admin.register(NotificacionSistema)
class NotificacionSistemaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "destinatario_grupo", "prioridad", "remitente", "leida", "atendida", "fecha_creacion")
    list_filter = ("tipo", "destinatario_grupo", "prioridad", "leida", "atendida", "fecha_creacion")
    search_fields = ("titulo", "mensaje", "remitente__username")
    readonly_fields = ("fecha_creacion", "fecha_lectura", "fecha_atencion")
    
    fieldsets = (
        ("Información Principal", {
            "fields": ("tipo", "titulo", "mensaje", "prioridad")
        }),
        ("Remitente y Destinatario", {
            "fields": ("remitente", "destinatario_grupo")
        }),
        ("Estado", {
            "fields": ("leida", "atendida", "fecha_expiracion")
        }),
        ("Datos Adicionales", {
            "fields": ("datos_contexto",),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("fecha_creacion", "fecha_lectura", "fecha_atencion"),
            "classes": ("collapse",)
        }),
    )
    
    actions = ["marcar_como_leida", "marcar_como_atendida"]
    
    def marcar_como_leida(self, request, queryset):
        for notificacion in queryset:
            notificacion.marcar_como_leida()
        self.message_user(request, f"{queryset.count()} notificaciones marcadas como leídas.")
    marcar_como_leida.short_description = "Marcar como leída"
    
    def marcar_como_atendida(self, request, queryset):
        for notificacion in queryset:
            notificacion.marcar_como_atendida()
        self.message_user(request, f"{queryset.count()} notificaciones marcadas como atendidas.")
    marcar_como_atendida.short_description = "Marcar como atendida"
