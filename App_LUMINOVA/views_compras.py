from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

# --- AJAX: Marcar notificación como leída ---
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@login_required
@require_POST
def ajax_marcar_notificacion_leida(request):
    import json
    import logging
    logger = logging.getLogger(__name__)
    try:
        data = json.loads(request.body)
        notif_id = data.get('id')
        notif = NotificacionSistema.objects.get(id=notif_id)
        # Solo marcar como leída si el insumo ya no es crítico
        # Buscar el insumo relacionado (asumiendo que el mensaje tiene el id del insumo)
        insumo_id = notif.datos_contexto.get('insumo_id') if notif.datos_contexto else None
        logger.info(f"[AJAX] Intentando marcar notificación {notif_id} como leída. insumo_id={insumo_id}")
        if insumo_id:
            from App_LUMINOVA.models import Insumo, Orden
            UMBRAL_STOCK_BAJO_INSUMOS = 15000
            try:
                insumo = Insumo.objects.get(id=insumo_id)
                stock_actual = insumo.stock
                from django.db.models import Q, Sum
                ESTADOS_OC_POST_BORRADOR = [
                    "APROBADA",
                    "ENVIADA_PROVEEDOR",
                    "EN_TRANSITO",
                    "RECIBIDA_PARCIAL",
                    "RECIBIDA_TOTAL",
                    "COMPLETADA",
                ]
                total_en_ocs = Orden.objects.filter(
                    tipo="compra",
                    estado__in=ESTADOS_OC_POST_BORRADOR,
                    insumo_principal=insumo
                ).filter(
                    Q(deposito=insumo.deposito) | Q(deposito__isnull=True)
                ).aggregate(total=Sum('cantidad_principal'))['total'] or 0
                logger.info(f"[AJAX] Insumo {insumo_id}: stock_actual={stock_actual}, total_en_ocs={total_en_ocs}, umbral={UMBRAL_STOCK_BAJO_INSUMOS}")
                if (stock_actual + total_en_ocs) >= UMBRAL_STOCK_BAJO_INSUMOS:
                    notif.marcar_como_leida(request.user)
                    logger.info(f"[AJAX] Notificación {notif_id} marcada como leída (insumo ya no crítico)")
                    return JsonResponse({'success': True, 'marcada': True})
                else:
                    logger.info(f"[AJAX] Notificación {notif_id} NO marcada como leída (insumo sigue crítico)")
                    return JsonResponse({'success': True, 'marcada': False, 'error': 'El insumo sigue siendo crítico'})
            except Insumo.DoesNotExist:
                logger.warning(f"[AJAX] Insumo {insumo_id} no existe. No se marca como leída.")
                return JsonResponse({'success': False, 'error': 'El insumo relacionado no existe.'}, status=400)
            except Exception as e:
                logger.error(f"[AJAX] Error al procesar insumo {insumo_id}: {e}")
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        else:
            # Si no hay insumo relacionado, NO marcar como leída (por seguridad)
            logger.info(f"[AJAX] Notificación {notif_id} sin insumo relacionado. No se marca como leída.")
            return JsonResponse({'success': True, 'marcada': False, 'error': 'No hay insumo relacionado.'})
    except Exception as e:
        logger.error(f"[AJAX] Error general: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from App_LUMINOVA.models import NotificacionSistema

# --- VISTA AJAX: Notificaciones no leídas para el usuario/grupo ---
@login_required
@require_GET
def ajax_notificaciones_no_leidas(request):
    user = request.user
    grupos = user.groups.values_list('name', flat=True)
    # Antes de obtener las notificaciones, marcar como leídas todas las de insumos con OC post-borrador
    from App_LUMINOVA.models import Insumo, Orden
    from django.db.models import Q, Sum
    UMBRAL_STOCK_BAJO_INSUMOS = 15000
    ESTADOS_OC_POST_BORRADOR = [
        "APROBADA",
        "ENVIADA_PROVEEDOR",
        "EN_TRANSITO",
        "RECIBIDA_PARCIAL",
        "RECIBIDA_TOTAL",
        "COMPLETADA",
    ]
    # Buscar todos los insumos con OC post-borrador
    insumos_con_oc_post_borrador = set(
        Orden.objects.filter(
            tipo="compra",
            estado__in=ESTADOS_OC_POST_BORRADOR
        ).values_list('insumo_principal', flat=True)
    )
    # Marcar como leídas todas las notificaciones de stock bajo de esos insumos
    if insumos_con_oc_post_borrador:
        NotificacionSistema.objects.filter(
            leida=False,
            tipo='stock_bajo',
            datos_contexto__insumo_id__in=insumos_con_oc_post_borrador,
            destinatario_grupo__in=grupos
        ).update(leida=True)

    # Ahora sí, obtener solo las no leídas (ya filtradas)
    notificaciones = NotificacionSistema.objects.filter(
        leida=False,
        destinatario_grupo__in=grupos
    ).order_by('-fecha_creacion')[:20]

    # Solo mostrar notificaciones de insumos que realmente siguen críticos
    data = []
    from App_LUMINOVA.models import Insumo, Orden
    from django.db.models import Q, Sum
    UMBRAL_STOCK_BAJO_INSUMOS = 15000
    ESTADOS_OC_POST_BORRADOR = [
        "APROBADA",
        "ENVIADA_PROVEEDOR",
        "EN_TRANSITO",
        "RECIBIDA_PARCIAL",
        "RECIBIDA_TOTAL",
        "COMPLETADA",
    ]
    # Para evitar duplicados, llevamos registro de insumos ya notificados
    insumos_notificados = set()
    for n in notificaciones:
        insumo_id = n.datos_contexto.get('insumo_id') if n.datos_contexto else None
        if n.tipo == 'stock_bajo' and insumo_id:
            try:
                insumo = Insumo.objects.get(id=insumo_id)
                # Si existe al menos una OC en estado post-borrador para este insumo y depósito, marcar todas las notificaciones como leídas
                existe_oc_post_borrador = Orden.objects.filter(
                    tipo="compra",
                    estado__in=ESTADOS_OC_POST_BORRADOR,
                    insumo_principal=insumo
                ).filter(
                    Q(deposito=insumo.deposito) | Q(deposito__isnull=True)
                ).exists()
                if existe_oc_post_borrador:
                    # Marcar todas las notificaciones de stock bajo de este insumo como leídas para este usuario
                    NotificacionSistema.objects.filter(
                        leida=False,
                        tipo='stock_bajo',
                        datos_contexto__insumo_id=insumo_id,
                        destinatario_grupo__in=grupos
                    ).update(leida=True)
                    continue  # No mostrar ninguna notificación de este insumo
                # Evitar duplicados: solo mostrar una notificación por insumo
                if insumo_id in insumos_notificados:
                    continue
                insumos_notificados.add(insumo_id)
                data.append({
                    'id': n.id,
                    'titulo': n.titulo,
                    'mensaje': n.mensaje,
                    'tipo': n.tipo,
                    'fecha': n.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                    'prioridad': n.prioridad,
                })
            except Insumo.DoesNotExist:
                continue
        else:
            # Para otros tipos de notificación, mostrar normalmente
            data.append({
                'id': n.id,
                'titulo': n.titulo,
                'mensaje': n.mensaje,
                'tipo': n.tipo,
                'fecha': n.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                'prioridad': n.prioridad,
            })
    return JsonResponse({'notificaciones': data})
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout_function
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm

# Django Contrib Imports
from django.contrib.auth.models import Group, Permission, User
from django.db import IntegrityError as DjangoIntegrityError
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Prefetch, ProtectedError, Q, Sum

# Django Core Imports
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt  # Usar con precaución
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ReportLab (Third-party for PDF generation)
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from Proyecto_LUMINOVA import settings

# Local Application Imports (Forms)
from .forms import (
    ClienteForm,
    FacturaForm,
    ItemOrdenVentaFormSet,
    ItemOrdenVentaFormSetCreacion,
    OrdenCompraForm,
    OrdenProduccionUpdateForm,
    OrdenVentaForm,
    PermisosRolForm,
    ProveedorForm,
    ReporteProduccionForm,
    RolForm,
)

# Local Application Imports (Models)
from .models import (
    AuditoriaAcceso,
    CategoriaInsumo,
    CategoriaProductoTerminado,
    Cliente,
    ComponenteProducto,
    EstadoOrden,
    Fabricante,
    Factura,
    HistorialOV,
    Insumo,
    ItemOrdenVenta,
    LoteProductoTerminado,
    OfertaProveedor,
    Orden,
    OrdenProduccion,
    OrdenVenta,
    PasswordChangeRequired,
    ProductoTerminado,
    Proveedor,
    Reportes,
    RolDescripcion,
    SectorAsignado,
    NotificacionSistema,
)

# Local Application Imports (Services)
from .services.notification_service import NotificationService
from .signals import get_client_ip

from .services.document_services import generar_siguiente_numero_documento
from .services.pdf_services import generar_pdf_factura
from .utils import es_admin, es_admin_o_rol

logger = logging.getLogger(__name__)

# --- COMPRAS VIEWS ---
@login_required
def compras_lista_oc_view(request):
    # if not es_admin_o_rol(request.user, ['compras', 'administrador']):
    #     messages.error(request, "Acceso denegado.")
    #     return redirect('App_LUMINOVA:dashboard')

    # Filtrar órdenes de tipo 'compra'
    # Asumiendo que tu modelo Orden tiene un campo 'tipo' y 'proveedor'
    ordenes_compra = (
        Orden.objects.filter(tipo="compra")
        .select_related(
            "proveedor",  # Si el campo se llama 'proveedor' en el modelo Orden
            "insumo_principal",  # Si el campo se llama 'insumo' en el modelo Orden
        )
        .order_by("-fecha_creacion")
    )

    # Para un futuro modal de creación de OC
    # from .forms import OrdenCompraForm # Necesitarás crear este formulario
    # form_oc = OrdenCompraForm()
    # oc_count = Orden.objects.filter(tipo='compra').count()
    # next_oc_number = f"OC-{str(oc_count + 1).zfill(4)}"
    # form_oc.fields['numero_orden'].initial = next_oc_number

    context = {
        "ordenes_list": ordenes_compra,  # Nombre genérico para la plantilla
        "titulo_seccion": "Listado de Órdenes de Compra",
        # 'form_orden': form_oc, # Para el modal de creación
        # 'tipo_orden_actual': 'compra',
    }
    # Necesitarás una plantilla para esto, ej. 'compras/compras_lista_oc.html'
    return render(request, "compras/compras_lista_oc.html", context)


@login_required
def compras_desglose_view(request):
    """Vista principal de compras con notificaciones de depósito"""
    # Validar permisos de acceso solo para compras y administradores
    if not es_admin_o_rol(request.user, ["compras", "administrador"]):
        messages.error(request, "Acceso denegado. No tiene permisos para acceder a Compras.")
        return redirect("App_LUMINOVA:dashboard")
        
    logger.info("--- compras_desglose_view: INICIO ---")

    # Obtener notificaciones de stock bajo del depósito
    notificaciones_usuario = NotificationService.obtener_notificaciones_usuario(
        request.user, solo_no_leidas=True
    )
    # Puede ser queryset o lista
    if hasattr(notificaciones_usuario, 'filter'):
        notificaciones_stock_bajo = notificaciones_usuario.filter(tipo='stock_bajo')
    else:
        notificaciones_stock_bajo = [n for n in notificaciones_usuario if getattr(n, 'tipo', None) == 'stock_bajo']

    UMBRAL_STOCK_BAJO_INSUMOS = 15000

    # --- LÓGICA CORREGIDA ---
    # Un insumo necesita gestión si su OC o no existe, o si está SOLAMENTE en estado 'BORRADOR'.
    # Si ya está 'APROBADA' o más allá, el equipo de compras ya hizo su parte principal.

    # 1. Obtenemos los IDs de insumos que ya tienen una OC "en firme" (es decir, post-borrador)
    # con cantidad suficiente para cubrir el déficit
    ESTADOS_OC_POST_BORRADOR = [
        "APROBADA",
        "ENVIADA_PROVEEDOR",
        "EN_TRANSITO",
        "RECIBIDA_PARCIAL",
        "RECIBIDA_TOTAL",
        "COMPLETADA",
    ]
    
    # Obtener insumos con OC aprobadas y verificar si la cantidad es suficiente
    from django.db.models import Sum
    insumos_con_oc_suficiente = []
    
    for insumo in Insumo.objects.filter(stock__lt=UMBRAL_STOCK_BAJO_INSUMOS):
        # Calcular total en órdenes de compra activas para este insumo y su depósito
        from django.db.models import Q
        total_en_ocs = Orden.objects.filter(
            tipo="compra",
            estado__in=ESTADOS_OC_POST_BORRADOR,
            insumo_principal=insumo
        ).filter(
            Q(deposito=insumo.deposito) | Q(deposito__isnull=True)
        ).aggregate(total=Sum('cantidad_principal'))['total'] or 0
        # Si el stock actual + lo que viene en OCs >= umbral, no necesita más gestión
        if (insumo.stock + total_en_ocs) >= UMBRAL_STOCK_BAJO_INSUMOS:
            insumos_con_oc_suficiente.append(insumo.id)
    
    insumos_ya_gestionados_ids = insumos_con_oc_suficiente

    logger.info(
        f"IDs de insumos que ya tienen OC post-borrador con cantidad suficiente: {list(insumos_ya_gestionados_ids)}"
    )

    # Debug detallado para verificar cada insumo
    all_insumos_bajo_stock = Insumo.objects.filter(stock__lt=UMBRAL_STOCK_BAJO_INSUMOS)
    logger.info(f"=== DEBUG DESGLOSE DE COMPRAS ===")
    logger.info(f"Umbral de stock bajo: {UMBRAL_STOCK_BAJO_INSUMOS}")
    if hasattr(all_insumos_bajo_stock, 'count'):
        logger.info(f"Total de insumos con stock bajo: {all_insumos_bajo_stock.count()}")
    else:
        logger.info(f"Total de insumos con stock bajo: {len(all_insumos_bajo_stock)}")
    
    for insumo in all_insumos_bajo_stock:
        ocs_activas = Orden.objects.filter(
            tipo="compra",
            estado__in=ESTADOS_OC_POST_BORRADOR,
            insumo_principal=insumo
        )
        total_en_ocs = ocs_activas.aggregate(total=Sum('cantidad_principal'))['total'] or 0
        stock_final = insumo.stock + total_en_ocs
        necesita_compra = stock_final < UMBRAL_STOCK_BAJO_INSUMOS
        
        logger.info(f"  Insumo '{insumo.descripcion}' (ID: {insumo.id}):")
        logger.info(f"    Stock actual: {insumo.stock}")
        logger.info(f"    En OCs activas: {total_en_ocs}")
        logger.info(f"    Stock proyectado: {stock_final}")
        logger.info(f"    Necesita compra: {necesita_compra}")
        logger.info(f"    OCs activas: {ocs_activas.count()}")
        
        for oc in ocs_activas:
            logger.info(f"      - OC #{oc.id}: Estado={oc.estado}, Cantidad={oc.cantidad_principal}")

    # 2. Buscamos insumos críticos, EXCLUYENDO los que ya están gestionados.
    #    La lista resultante solo contendrá insumos sin OC o con OC en 'BORRADOR'.
    # Agrupar insumos por depósito
    from collections import defaultdict
    insumos_criticos = (
        Insumo.objects.filter(stock__lt=UMBRAL_STOCK_BAJO_INSUMOS)
        .exclude(id__in=insumos_ya_gestionados_ids)
        .select_related("categoria", "deposito")
        .order_by("deposito__nombre", "categoria__nombre", "stock", "descripcion")
    )
    insumos_por_deposito = defaultdict(list)
    for insumo in insumos_criticos:
        tiene_oc_borrador = Orden.objects.filter(
            tipo="compra",
            estado="BORRADOR",
            insumo_principal=insumo,
            deposito=insumo.deposito
        ).exists()
        insumo.tiene_oc_borrador = tiene_oc_borrador
        insumos_por_deposito[insumo.deposito.nombre if insumo.deposito else "Sin depósito"].append(insumo)
    
    context = {
        "insumos_por_deposito": dict(insumos_por_deposito),
        "notificaciones_stock_bajo": notificaciones_stock_bajo,
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO_INSUMOS,
        "titulo_seccion": "Gestionar Compra por Stock Bajo",
    }
    
    if hasattr(notificaciones_stock_bajo, 'count'):
        try:
            logger.info(f"Notificaciones de stock bajo: {notificaciones_stock_bajo.count()}")
        except TypeError:
            logger.info(f"Notificaciones de stock bajo: {len(list(notificaciones_stock_bajo))}")
    else:
        logger.info(f"Notificaciones de stock bajo: {len(notificaciones_stock_bajo)}")
    return render(request, "compras/compras_desglose.html", context)


@login_required
def compras_seguimiento_view(request):
    """
    Muestra las Órdenes de Compra que ya fueron gestionadas y están
    en proceso de envío o recepción.
    """
    estados_en_seguimiento = ["ENVIADA_PROVEEDOR", "EN_TRANSITO", "RECIBIDA_PARCIAL"]
    ordenes = (
        Orden.objects.filter(tipo="compra", estado__in=estados_en_seguimiento)
        .select_related("proveedor")
        .order_by("-fecha_creacion")
    )

    context = {
        "ordenes_en_seguimiento": ordenes,
        "titulo_seccion": "Seguimiento de Órdenes de Compra",
    }
    return render(request, "compras/seguimiento.html", context)


@login_required
def compras_tracking_pedido_view(
    request, oc_id
):  # Cambiado para usar ID, es más robusto
    """
    Muestra la página de tracking visual para una OC específica.
    """
    orden_compra = get_object_or_404(
        Orden.objects.select_related("proveedor"),
        id=oc_id,  # Buscamos por ID
        tipo="compra",
    )
    context = {
        "orden_compra": orden_compra,
    }
    return render(request, "compras/compras_tracking_pedido.html", context)


@login_required
def compras_desglose_detalle_oc_view(request, numero_orden_desglose):
    # Aquí mostrarías el detalle de una OC específica de la vista de desglose
    # orden_compra = get_object_or_404(Orden, numero_orden=numero_orden_desglose, tipo='compra')
    # Aquí podrías listar los insumos si una OC puede tener múltiples.
    context = {
        # 'orden': orden_compra,
        "numero_orden_desglose": numero_orden_desglose,  # Pasar para mostrar en la plantilla
        "titulo_seccion": f"Detalle Desglose OC: {numero_orden_desglose}",
    }
    return render(
        request, "compras/compras_desglose_detalle.html", context
    )  # Nombre de plantilla sugerido


@login_required
def compras_seleccionar_proveedor_para_insumo_view(request, insumo_id):
    insumo_objetivo = get_object_or_404(
        Insumo.objects.select_related("categoria"), id=insumo_id
    )
    logger.info(
        f"Seleccionando proveedor para insumo: {insumo_objetivo.descripcion} (ID: {insumo_id})"
    )

    if request.method == "POST":
        oferta_id_seleccionada = request.POST.get("oferta_proveedor_id")
        proveedor_fallback_id_seleccionado = request.POST.get("proveedor_fallback_id")

        proveedor_id_final_para_oc = None  # Renombrado para claridad

        if oferta_id_seleccionada:
            try:
                oferta = OfertaProveedor.objects.get(
                    id=oferta_id_seleccionada, insumo_id=insumo_id
                )  # Asegurar que la oferta sea para este insumo
                proveedor_id_final_para_oc = oferta.proveedor.id
                logger.info(
                    f"Oferta ID {oferta_id_seleccionada} seleccionada. Proveedor ID: {proveedor_id_final_para_oc}"
                )
            except OfertaProveedor.DoesNotExist:
                messages.error(
                    request,
                    "La oferta seleccionada no es válida o no corresponde al insumo.",
                )
                return redirect(
                    "App_LUMINOVA:compras_seleccionar_proveedor_para_insumo",
                    insumo_id=insumo_id,
                )
        elif proveedor_fallback_id_seleccionado:
            proveedor_id_final_para_oc = proveedor_fallback_id_seleccionado
            logger.info(
                f"Proveedor fallback ID {proveedor_fallback_id_seleccionado} seleccionado."
            )
        else:
            messages.error(request, "Debe seleccionar un proveedor u oferta.")
            return redirect(
                "App_LUMINOVA:compras_seleccionar_proveedor_para_insumo",
                insumo_id=insumo_id,
            )

        # Redirigir a la vista de creación de OC con los nombres de parámetros que espera la URL pattern
        logger.info(
            f"Redirigiendo a crear OC con insumo_id={insumo_id} y proveedor_id={proveedor_id_final_para_oc}"
        )
        return redirect(
            "App_LUMINOVA:compras_crear_oc_desde_insumo_y_proveedor",
            insumo_id=insumo_id,  # <--- USA 'insumo_id'
            proveedor_id=proveedor_id_final_para_oc,
        )  # <--- USA 'proveedor_id'
    # ... (resto de la lógica GET) ...
    # ... (código de la lógica GET de la vista) ...
    ofertas = (
        OfertaProveedor.objects.filter(insumo_id=insumo_id)
        .select_related("proveedor")
        .order_by("precio_unitario_compra", "tiempo_entrega_estimado_dias")
    )
    insumo_objetivo = get_object_or_404(
        Insumo, id=insumo_id
    )  # Necesario para el contexto GET

    proveedores_fallback = []
    if not ofertas.exists():
        proveedores_fallback = Proveedor.objects.all().order_by("nombre")[:5]

    UMBRAL_STOCK_BAJO_INSUMOS = 15000
    context = {
        "insumo_objetivo": insumo_objetivo,
        "ofertas_proveedores": ofertas,
        "proveedores_fallback": proveedores_fallback,
        "titulo_seccion": f"Seleccionar Oferta para: {insumo_objetivo.descripcion}",
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO_INSUMOS,
    }
    return render(request, "compras/compras_seleccionar_proveedor.html", context)


@login_required
def compras_detalle_oc_view(request, oc_id):
    # if not es_admin_o_rol(request.user, ['compras', 'administrador', 'deposito']): # Ajusta permisos
    #     messages.error(request, "Acceso denegado.")
    #     return redirect('App_LUMINOVA:compras_lista_oc')

    orden_compra = get_object_or_404(
        Orden.objects.select_related("proveedor", "insumo_principal__categoria"),
        id=oc_id,
        tipo="compra",  # Asegurar que sea una OC
    )

    # Si tuvieras ItemsOrdenCompra, los prefetch aquí:
    # .prefetch_related('items_oc__insumo')

    context = {
        "oc": orden_compra,
        "titulo_seccion": f"Detalle OC: {orden_compra.numero_orden}",
    }
    return render(request, "compras/compras_detalle_oc.html", context)


@login_required
@transaction.atomic
def compras_crear_oc_view(request, insumo_id=None, proveedor_id=None):
    insumo_preseleccionado_obj = None
    proveedor_preseleccionado_obj = None
    initial_data = {}
    form_kwargs = {}

    if insumo_id:
        insumo_preseleccionado_obj = get_object_or_404(Insumo, id=insumo_id)
        initial_data['insumo_principal'] = insumo_preseleccionado_obj
        form_kwargs['insumo_fijado'] = insumo_preseleccionado_obj

        UMBRAL_STOCK_BAJO = 15000
        cantidad_sugerida = max(10, UMBRAL_STOCK_BAJO - insumo_preseleccionado_obj.stock)
        initial_data['cantidad_principal'] = cantidad_sugerida

        if proveedor_id:
            proveedor_preseleccionado_obj = get_object_or_404(Proveedor, id=proveedor_id)
            initial_data['proveedor'] = proveedor_preseleccionado_obj
            oferta_seleccionada = OfertaProveedor.objects.filter(insumo=insumo_preseleccionado_obj, proveedor=proveedor_preseleccionado_obj).first()
            if oferta_seleccionada:
                initial_data['precio_unitario_compra'] = oferta_seleccionada.precio_unitario_compra
                if oferta_seleccionada.tiempo_entrega_estimado_dias is not None:
                    try:
                        dias = int(oferta_seleccionada.tiempo_entrega_estimado_dias)
                        fecha_estimada = timezone.now().date() + timedelta(days=dias)
                        initial_data['fecha_estimada_entrega'] = fecha_estimada.strftime('%Y-%m-%d')
                    except (ValueError, TypeError): pass

    if request.method == 'POST':
        logger.info(f"=== DEBUG CREAR OC ===")
        logger.info(f"POST data: {dict(request.POST)}")
        logger.info(f"insumo_id: {insumo_id}")
        logger.info(f"proveedor_id: {proveedor_id}")
        
        form = OrdenCompraForm(request.POST, **form_kwargs)
        if form.is_valid():
            orden_compra = form.save(commit=False)
            orden_compra.tipo = 'compra'
            orden_compra.estado = 'BORRADOR'
            # Asignar depósito correctamente
            deposito_id = None
            if orden_compra.insumo_principal and orden_compra.insumo_principal.deposito:
                deposito_id = orden_compra.insumo_principal.deposito.id
            else:
                deposito_id = request.session.get('deposito_seleccionado')
            if deposito_id:
                from App_LUMINOVA.models import Deposito
                orden_compra.deposito = Deposito.objects.get(id=deposito_id)
            logger.info(f"Orden antes de guardar:")
            logger.info(f"  - insumo_principal: {orden_compra.insumo_principal}")
            logger.info(f"  - proveedor: {orden_compra.proveedor}")
            logger.info(f"  - cantidad_principal: {orden_compra.cantidad_principal}")
            logger.info(f"  - deposito: {getattr(orden_compra.deposito, 'nombre', None)}")
            # --- Aquí asignamos el número de orden usando el servicio ---
            orden_compra.numero_orden = generar_siguiente_numero_documento(Orden, 'OC', 'numero_orden')
            orden_compra.save()
            logger.info(f"Orden después de guardar:")
            logger.info(f"  - ID: {orden_compra.id}")
            logger.info(f"  - numero_orden: {orden_compra.numero_orden}")
            logger.info(f"  - insumo_principal: {orden_compra.insumo_principal}")
            logger.info(f"  - deposito: {getattr(orden_compra.deposito, 'nombre', None)}")
            messages.success(request, f"Orden de Compra '{orden_compra.numero_orden}' creada en Borrador.")
            return redirect('App_LUMINOVA:compras_lista_oc')
        else:
            messages.error(request, "Por favor, corrija los errores del formulario.")
            logger.error(f"Errores del formulario: {form.errors}")
    else: # GET
        form = OrdenCompraForm(initial=initial_data, **form_kwargs)

    context = {
        'form_oc': form,
        'titulo_seccion': 'Crear Orden de Compra',
        'insumo_preseleccionado': insumo_preseleccionado_obj,
    }
    return render(request, 'compras/compras_crear_editar_oc.html', context)


@login_required
@transaction.atomic
def compras_editar_oc_view(request, oc_id):
    orden_compra_instance = get_object_or_404(Orden, id=oc_id, tipo="compra")
    logger.info(
        f"Editando OC: {orden_compra_instance.numero_orden} (ID: {oc_id}), Estado actual: {orden_compra_instance.estado}"
    )

    estados_no_editables_campos_principales = [
        "APROBADA",
        "ENVIADA_PROVEEDOR",
        "CONFIRMADA_PROVEEDOR",
        "EN_TRANSITO",
        "RECIBIDA_PARCIAL",
        "RECIBIDA_TOTAL",
        "COMPLETADA",
        "CANCELADA",
    ]

    if orden_compra_instance.estado in estados_no_editables_campos_principales:
        messages.warning(
            request,
            f"La OC {orden_compra_instance.numero_orden} en estado '{orden_compra_instance.get_estado_display()}' tiene edición limitada (ej. solo notas o tracking). Los campos principales no se modificarán.",
        )
        # La lógica del __init__ del form deshabilitará la mayoría de los campos.

    insumo_original_obj_al_cargar = orden_compra_instance.insumo_principal
    cantidad_original_guardada = orden_compra_instance.cantidad_principal or 0

    # Preparar kwargs para el formulario, sin incluir 'instance' aquí si se pasa explícitamente
    form_init_kwargs = {}
    if insumo_original_obj_al_cargar:
        form_init_kwargs["insumo_fijado"] = insumo_original_obj_al_cargar
    if orden_compra_instance.proveedor and orden_compra_instance.estado != "BORRADOR":
        form_init_kwargs["proveedor_fijado"] = orden_compra_instance.proveedor

    if request.method == "POST":
        # Al instanciar para POST, pasamos instance explícitamente, y el resto en form_init_kwargs
        form = OrdenCompraForm(
            request.POST, instance=orden_compra_instance, **form_init_kwargs
        )
        if form.is_valid():
            try:
                oc_actualizada = form.save(commit=False)

                insumo_nuevo_obj_form = form.cleaned_data.get("insumo_principal")
                cantidad_nueva_form = form.cleaned_data.get("cantidad_principal") or 0

                if orden_compra_instance.estado == "BORRADOR":
                    insumo_original_en_db = Orden.objects.get(
                        pk=oc_id
                    ).insumo_principal  # Estado del insumo antes de esta edición
                    cantidad_original_en_db = (
                        Orden.objects.get(pk=oc_id).cantidad_principal or 0
                    )

                    # Caso 1: El insumo principal cambió
                    if (
                        insumo_original_en_db
                        and insumo_nuevo_obj_form
                        and insumo_original_en_db.id != insumo_nuevo_obj_form.id
                    ):
                        Insumo.objects.filter(id=insumo_original_en_db.id).update(
                            cantidad_en_pedido=F("cantidad_en_pedido")
                            - cantidad_original_en_db
                        )
                        Insumo.objects.filter(id=insumo_nuevo_obj_form.id).update(
                            cantidad_en_pedido=F("cantidad_en_pedido")
                            + cantidad_nueva_form
                        )
                    # Caso 2: El insumo no cambió, pero la cantidad sí
                    elif (
                        insumo_original_en_db
                        and insumo_original_en_db.id
                        == (insumo_nuevo_obj_form.id if insumo_nuevo_obj_form else None)
                        and cantidad_original_en_db != cantidad_nueva_form
                    ):
                        cambio_neto_cantidad = (
                            cantidad_nueva_form - cantidad_original_en_db
                        )
                        Insumo.objects.filter(id=insumo_original_en_db.id).update(
                            cantidad_en_pedido=F("cantidad_en_pedido")
                            + cambio_neto_cantidad
                        )
                    # Caso 3: Se añadió un insumo donde antes no había
                    elif (
                        not insumo_original_en_db
                        and insumo_nuevo_obj_form
                        and cantidad_nueva_form > 0
                    ):
                        Insumo.objects.filter(id=insumo_nuevo_obj_form.id).update(
                            cantidad_en_pedido=F("cantidad_en_pedido")
                            + cantidad_nueva_form
                        )
                    # Caso 4: Se quitó un insumo que antes estaba
                    elif insumo_original_en_db and not insumo_nuevo_obj_form:
                        Insumo.objects.filter(id=insumo_original_en_db.id).update(
                            cantidad_en_pedido=F("cantidad_en_pedido")
                            - cantidad_original_en_db
                        )

                oc_actualizada.save()
                messages.success(
                    request,
                    f"Orden de Compra '{oc_actualizada.numero_orden}' actualizada exitosamente.",
                )
                return redirect(
                    "App_LUMINOVA:compras_detalle_oc", oc_id=oc_actualizada.id
                )

            except DjangoIntegrityError as e_int:
                if (
                    "UNIQUE constraint" in str(e_int).lower()
                    and "numero_orden" in str(e_int).lower()
                ):
                    messages.error(
                        request,
                        f"Error: El N° de OC '{form.cleaned_data.get('numero_orden', '')}' ya existe.",
                    )
                else:
                    messages.error(request, f"Error de base de datos: {e_int}")
            except Exception as e:
                messages.error(request, f"Error inesperado al actualizar la OC: {e}")
                logger.exception(f"Error al editar OC {oc_id} (POST):")
        else:  # Formulario no es válido
            logger.warning(f"Formulario OC (edición) inválido: {form.errors.as_json()}")
            messages.error(request, "Por favor, corrija los errores en el formulario.")
            # El form con errores (ya instanciado con request.POST, instance y form_init_kwargs)
            # se pasará al contexto
    else:  # GET request
        # Al instanciar para GET, pasamos instance explícitamente y el resto en form_init_kwargs
        form = OrdenCompraForm(instance=orden_compra_instance, **form_init_kwargs)

    context = {
        "form_oc": form,
        "titulo_seccion": f"Editar Orden de Compra: {orden_compra_instance.numero_orden}",
        "oc_instance": orden_compra_instance,
        "insumo_preseleccionado": orden_compra_instance.insumo_principal,
        "proveedor_preseleccionado": orden_compra_instance.proveedor,
    }
    return render(request, "compras/compras_crear_editar_oc.html", context)


@login_required
@require_POST  # Esta acción debería ser un POST, ya que modifica datos
@transaction.atomic
def compras_aprobar_oc_directamente_view(request, oc_id):  # Nuevo nombre
    # if not es_admin_o_rol(request.user, ['compras_manager', 'administrador']): # Permisos
    #     messages.error(request, "No tiene permiso para aprobar Órdenes de Compra.")
    #     return redirect('App_LUMINOVA:compras_lista_oc')

    orden_compra = get_object_or_404(Orden, id=oc_id, tipo="compra")

    if orden_compra.estado == "BORRADOR":  # Solo aprobar desde borrador
        try:
            orden_compra.estado = "APROBADA"
            # Aquí es un buen lugar para confirmar/actualizar la cantidad_en_pedido del insumo
            # si no se hizo al crear el borrador, o si quieres que solo las aprobadas la afecten.
            if (
                orden_compra.insumo_principal
                and orden_compra.cantidad_principal
                and orden_compra.cantidad_principal > 0
            ):
                # Asegúrate que esta lógica no duplique si ya lo hiciste en la creación del borrador.
                # Si la cantidad_en_pedido se suma al crear el BORRADOR, no necesitas hacerlo de nuevo aquí.
                # Si solo se suma al APROBAR, entonces este es el lugar:
                # Insumo.objects.filter(id=orden_compra.insumo_principal.id).update(
                #     cantidad_en_pedido=F('cantidad_en_pedido') + orden_compra.cantidad_principal
                # )
                # logger.info(f"OC {orden_compra.numero_orden} aprobada. Incrementada cantidad_en_pedido para {orden_compra.insumo_principal.descripcion}.")
                pass  # Asumimos que cantidad_en_pedido ya se actualizó al crear el borrador

            orden_compra.save(update_fields=["estado"])
            messages.success(
                request,
                f"Orden de Compra '{orden_compra.numero_orden}' ha sido APROBADA.",
            )
            logger.info(
                f"OC {orden_compra.numero_orden} (ID: {oc_id}) cambió estado a APROBADA por {request.user.username}"
            )
        except Exception as e:
            messages.error(request, f"Error al aprobar la OC: {e}")
            logger.error(f"Error al cambiar estado de OC {oc_id} a APROBADA: {e}")
    else:
        messages.warning(
            request,
            f"La OC '{orden_compra.numero_orden}' no está en estado 'Borrador'. Estado actual: {orden_compra.get_estado_display()}",
        )

    return redirect("App_LUMINOVA:compras_lista_oc")


@login_required
@require_GET  # Esta vista solo necesita obtener datos
def get_oferta_proveedor_ajax(request):
    insumo_id = request.GET.get("insumo_id")
    proveedor_id = request.GET.get("proveedor_id")

    if not insumo_id or not proveedor_id:
        return JsonResponse({"error": "Faltan IDs de insumo o proveedor"}, status=400)

    try:
        insumo_id = int(insumo_id)
        proveedor_id = int(proveedor_id)
    except ValueError:
        return JsonResponse({"error": "IDs inválidos"}, status=400)

    oferta = OfertaProveedor.objects.filter(
        insumo_id=insumo_id, proveedor_id=proveedor_id
    ).first()

    if oferta:
        fecha_estimada_entrega_calculada = None
        if oferta.tiempo_entrega_estimado_dias is not None:
            try:
                dias = int(oferta.tiempo_entrega_estimado_dias)
                fecha_estimada_entrega_calculada = (
                    timezone.now().date() + timedelta(days=dias)
                ).strftime("%Y-%m-%d")
            except ValueError:
                pass  # No se pudo calcular

        data = {
            "success": True,
            "precio_unitario": oferta.precio_unitario_compra,
            "tiempo_entrega_dias": oferta.tiempo_entrega_estimado_dias,
            "fecha_estimada_entrega": fecha_estimada_entrega_calculada,
            "fecha_actualizacion_oferta": (
                oferta.fecha_actualizacion_precio.strftime("%d/%m/%Y")
                if oferta.fecha_actualizacion_precio
                else None
            ),
        }
        return JsonResponse(data)
    else:
        return JsonResponse(
            {"success": False, "error": "No se encontró oferta para esta combinación."},
            status=404,
        )


@login_required
@require_GET
def ajax_get_proveedores_for_insumo(request):
    insumo_id = request.GET.get("insumo_id")
    if not insumo_id:
        return JsonResponse({"proveedores": []})

    try:
        # Obtiene los IDs de los proveedores que tienen una oferta para el insumo dado.
        proveedor_ids = (
            OfertaProveedor.objects.filter(insumo_id=insumo_id)
            .values_list("proveedor_id", flat=True)
            .distinct()
        )

        # Obtiene los objetos Proveedor correspondientes a esos IDs.
        proveedores = (
            Proveedor.objects.filter(id__in=proveedor_ids)
            .values("id", "nombre")
            .order_by("nombre")
        )

        return JsonResponse({"proveedores": list(proveedores)})
    except ValueError:
        return JsonResponse({"error": "ID de insumo inválido"}, status=400)
    except Exception as e:
        logger.error(f"Error en ajax_get_proveedores_for_insumo: {e}")
        return JsonResponse({"error": "Ocurrió un error en el servidor"}, status=500)
