from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout as auth_logout_function
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F
from datetime import timedelta

from .models import AuditoriaAcceso, Reportes, OrdenProduccion, Orden, Insumo, OrdenVenta, Deposito

def get_client_ip(request):
    """Obtener la IP del cliente desde el request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# --- GENERAL VIEWS & AUTHENTICATION ---
def inicio(
    request,
):  # Esta vista es la que se muestra si el usuario no está autenticado
    if request.user.is_authenticated:
        return redirect("App_LUMINOVA:dashboard")
    return redirect("App_LUMINOVA:login")  # Redirige a login si no está autenticado


def login_view(request):
    if request.user.is_authenticated:
        return redirect("App_LUMINOVA:dashboard")  # Redirige si ya está logueado

    if request.method == "POST":
        # Obtener los datos del formulario de login
        username_from_form = request.POST.get("username")
        password_from_form = request.POST.get("password")

        # Autenticar al usuario
        user = authenticate(
            request,
            username=username_from_form,
            password=password_from_form,
        )

        if user is not None:
            # Si la autenticación es exitosa, iniciar la sesión
            login(request, user)

            # --- LÓGICA CLAVE DE AUDITORÍA ---
            # Ahora que el usuario está logueado y tenemos el 'request' completo,
            # registramos el evento.
            AuditoriaAcceso.objects.create(
                usuario=user,
                accion="Inicio de sesión",
                ip_address=get_client_ip(request),  # Obtendrá la IP
                user_agent=request.META.get(
                    "HTTP_USER_AGENT", ""
                ),  # Obtendrá el navegador
            )

            # Redirigir al dashboard (o a la página de cambio de contraseña si es necesario, el middleware se encargará)
            return redirect("App_LUMINOVA:dashboard")
        else:
            # Si las credenciales son inválidas, mostrar un error
            messages.error(request, "Usuario o contraseña incorrectos.")

    # Si es una petición GET, simplemente mostrar la página de login
    return render(request, "login.html")


def custom_logout_view(request):
    """
    Gestiona el cierre de sesión y registra el evento en la auditoría ANTES de desloguear.
    """
    user = request.user if request.user.is_authenticated else None

    # Registrar el evento de cierre de sesión con toda la información disponible
    AuditoriaAcceso.objects.create(
        usuario=user,
        accion="Cierre de sesión",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )

    # Llamar a la función de logout de Django para limpiar la sesión
    auth_logout_function(request)

    # Opcional: mostrar un mensaje de que cerró sesión exitosamente
    messages.info(request, "Has cerrado sesión exitosamente.")

    # Redirigir a la página de login
    return redirect("App_LUMINOVA:login")


@login_required
def dashboard_view(request):
    # Obtener empresa actual del usuario
    empresa_actual = request.empresa_actual
    
    # Filtrar depósitos por empresa
    if empresa_actual:
        depositos_empresa = Deposito.objects.filter(empresa=empresa_actual)
    else:
        depositos_empresa = Deposito.objects.none()
    
    # --- 1. Tarjeta: Acciones Urgentes ---
    # Filtrar por depósitos de la empresa
    ops_con_problemas_reportados_count = (
        Reportes.objects.filter(
            resuelto=False, 
            orden_produccion_asociada__isnull=False,
            orden_produccion_asociada__producto_a_producir__deposito__in=depositos_empresa
        )
        .values("orden_produccion_asociada_id")
        .distinct()
        .count()
    )
    solicitudes_insumos_pendientes = OrdenProduccion.objects.filter(
        estado_op__nombre__iexact="Insumos Solicitados",
        producto_a_producir__deposito__in=depositos_empresa
    ).count()
    ocs_para_aprobar = Orden.objects.filter(
        tipo="compra", 
        estado="BORRADOR",
        deposito__in=depositos_empresa
    ).count()

    # --- 2. Tarjeta: Stock Crítico ---
    UMBRAL_STOCK_BAJO = 15000
    # Solo mostrar insumos críticos que NO tengan OC activa (aprobada, enviada, en tránsito, etc.)
    ESTADOS_OC_ACTIVA = [
        "APROBADA",
        "ENVIADA_PROVEEDOR",
        "EN_TRANSITO",
        "RECIBIDA_PARCIAL",
        "RECIBIDA_TOTAL",
        "COMPLETADA",
    ]
    insumos_criticos_query = Insumo.objects.filter(
        stock__lt=UMBRAL_STOCK_BAJO,
        deposito__in=depositos_empresa  # Filtrar por empresa
    ).order_by("stock")
    insumos_criticos_filtrados = []
    for insumo in insumos_criticos_query:
        tiene_oc_activa = Orden.objects.filter(
            tipo="compra",
            estado__in=ESTADOS_OC_ACTIVA,
            insumo_principal=insumo
        ).exists()
        if not tiene_oc_activa:
            porcentaje_stock = (
                int((insumo.stock / UMBRAL_STOCK_BAJO) * 100)
                if UMBRAL_STOCK_BAJO > 0
                else 0
            )
            insumos_criticos_filtrados.append(
                {
                    "insumo": insumo,
                    "porcentaje_stock": min(100, porcentaje_stock),
                    "notificado": getattr(insumo, "notificado_a_compras", False),
                }
            )
    insumos_criticos_con_porcentaje = insumos_criticos_filtrados

    # --- 3. Tarjeta: Rendimiento de Producción ---
    hace_30_dias = timezone.now() - timedelta(days=30)
    ops_completadas_recientemente = OrdenProduccion.objects.filter(
        estado_op__nombre__iexact="Completada", 
        fecha_fin_real__gte=hace_30_dias,
        producto_a_producir__deposito__in=depositos_empresa  # Filtrar por empresa
    )
    total_luminarias_ensambladas = (
        ops_completadas_recientemente.aggregate(total=Sum("cantidad_a_producir"))[
            "total"
        ]
        or 0
    )
    total_ops_completadas = ops_completadas_recientemente.count()
    ops_a_tiempo = ops_completadas_recientemente.filter(
        fecha_fin_real__date__lte=F("fecha_fin_planificada")
    ).count()
    ops_con_retraso = total_ops_completadas - ops_a_tiempo
    tasa_cumplimiento = (
        (ops_a_tiempo / total_ops_completadas * 100) if total_ops_completadas > 0 else 0
    )

    # --- 4. Tarjeta: Actividad Reciente ---
    try:
        # Filtrar OVs por productos de la empresa
        ultima_ov = OrdenVenta.objects.filter(
            items_ov__producto_terminado__deposito__in=depositos_empresa
        ).distinct().latest("fecha_creacion")
    except OrdenVenta.DoesNotExist:
        ultima_ov = None
    try:
        ultima_op_completada = OrdenProduccion.objects.filter(
            estado_op__nombre__iexact="Completada",
            producto_a_producir__deposito__in=depositos_empresa
        ).latest("fecha_fin_real")
    except OrdenProduccion.DoesNotExist:
        ultima_op_completada = None
    try:
        ultimo_reporte = Reportes.objects.filter(
            orden_produccion_asociada__producto_a_producir__deposito__in=depositos_empresa
        ).latest("fecha")
    except Reportes.DoesNotExist:
        ultimo_reporte = None

    context = {
        "ops_con_problemas_count": ops_con_problemas_reportados_count,
        "solicitudes_insumos_pendientes_count": solicitudes_insumos_pendientes,
        "ocs_para_aprobar_count": ocs_para_aprobar,
        "insumos_criticos_list": insumos_criticos_con_porcentaje,
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO,
        "total_luminarias_ensambladas": total_luminarias_ensambladas,
        "ops_a_tiempo": ops_a_tiempo,
        "ops_con_retraso": ops_con_retraso,
        "tasa_cumplimiento": tasa_cumplimiento,
        "ultima_ov": ultima_ov,
        "ultima_op_completada": ultima_op_completada,
        "ultimo_reporte": ultimo_reporte,
    }
    return render(request, "admin/dashboard.html", context)
