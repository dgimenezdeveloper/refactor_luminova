from django.db import transaction
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .forms import TransferenciaInsumoForm, TransferenciaProductoForm
from .models import Insumo, ProductoTerminado, UsuarioDeposito
from django.http import HttpResponseForbidden
# --- TRANSFERENCIA DE INSUMOS ENTRE DEPÓSITOS ---
from .utils import es_admin_o_rol

def _usuario_puede_acceder_deposito(user, deposito, accion="transferir"):
    """Verifica si el usuario puede acceder al depósito especificado para la acción dada"""
    if user.is_superuser or user.groups.filter(name='administrador').exists():
        return True
    
    from .models import UsuarioDeposito
    
    try:
        asignacion = UsuarioDeposito.objects.get(usuario=user, deposito=deposito)
        if accion == "transferir":
            return asignacion.puede_transferir
        elif accion == "entrada":
            return asignacion.puede_entradas
        elif accion == "salida":
            return asignacion.puede_salidas
        else:
            return True  # Por defecto permitir si la acción no está especificada
    except UsuarioDeposito.DoesNotExist:
        # Si no hay asignación específica, verificar por rol general
        # Usuarios con rol 'deposito' pueden acceder a todos por defecto
        if user.groups.filter(name='Depósito').exists():
            return True
        return False

def _auditar_movimiento(tipo, usuario, insumo=None, producto=None, deposito_origen=None, deposito_destino=None, cantidad=0, motivo=""):
    """Registra el movimiento en la auditoría"""
    from .models import MovimientoStock
    
    MovimientoStock.objects.create(
        insumo=insumo,
        producto=producto,
        deposito_origen=deposito_origen,
        deposito_destino=deposito_destino,
        cantidad=cantidad,
        tipo=tipo,
        usuario=usuario,
        motivo=motivo or f"{tipo.title()} registrado automáticamente"
    )

@login_required
@transaction.atomic
def transferencia_insumo_view(request):
    # Solo usuarios con rol 'deposito' o 'administrador'
    if not es_admin_o_rol(request.user, ["deposito", "administrador"]):
        messages.error(request, "Acceso denegado. No tiene permisos para transferir insumos.")
        return redirect("App_LUMINOVA:deposito_view")

    if request.method == "POST":
        form = TransferenciaInsumoForm(request.POST, user=request.user)
        if form.is_valid():
            insumo = form.cleaned_data["insumo"]
            deposito_origen = form.cleaned_data["deposito_origen"]
            deposito_destino = form.cleaned_data["deposito_destino"]
            cantidad = form.cleaned_data["cantidad"]
            motivo = form.cleaned_data["motivo"]
            
            # Validar que el usuario tenga acceso a ambos depósitos para transferencias
            if not _usuario_puede_acceder_deposito(request.user, deposito_origen, "transferir") or \
               not _usuario_puede_acceder_deposito(request.user, deposito_destino, "transferir"):
                messages.error(request, "No tiene permisos para transferir entre los depósitos seleccionados.")
                return redirect("App_LUMINOVA:transferencia_insumo")
            
            from .models import StockInsumo, MovimientoStock, CategoriaInsumo

            # Buscar o crear la categoría en el destino
            categoria_destino = CategoriaInsumo.objects.filter(nombre=insumo.categoria.nombre, deposito=deposito_destino).first()
            if not categoria_destino:
                categoria_destino = CategoriaInsumo.objects.create(
                    nombre=insumo.categoria.nombre,
                    imagen=insumo.categoria.imagen,
                    deposito=deposito_destino
                )

            # Buscar o crear el insumo en el destino
            insumo_destino = Insumo.objects.filter(
                descripcion=insumo.descripcion,
                fabricante=insumo.fabricante,
                categoria=categoria_destino,
                deposito=deposito_destino
            ).first()
            if not insumo_destino:
                insumo_destino = Insumo.objects.create(
                    descripcion=insumo.descripcion,
                    categoria=categoria_destino,
                    fabricante=insumo.fabricante,
                    imagen=insumo.imagen,
                    deposito=deposito_destino
                )

            import logging
            logger = logging.getLogger(__name__)
            # Descontar stock del origen (StockInsumo)
            stock_origen = StockInsumo.objects.get(insumo=insumo, deposito=deposito_origen)
            logger.info(f"[TRANSFERENCIA] Stock origen antes: {stock_origen.cantidad}")
            if stock_origen.cantidad < cantidad:
                messages.error(request, "Stock insuficiente en el depósito de origen.")
                logger.warning(f"[TRANSFERENCIA] Stock insuficiente en origen: {stock_origen.cantidad} < {cantidad}")
                return redirect("App_LUMINOVA:transferencia_insumo")
            stock_origen.cantidad -= cantidad
            stock_origen.save()
            logger.info(f"[TRANSFERENCIA] Stock origen después: {stock_origen.cantidad}")
            # Sincronizar campo stock del Insumo origen si existe
            if hasattr(insumo, 'stock'):
                insumo.stock = stock_origen.cantidad
                insumo.save(update_fields=["stock"])
                logger.info(f"[TRANSFERENCIA] Insumo origen stock actualizado a {insumo.stock}")
            else:
                logger.warning(f"[TRANSFERENCIA] El modelo Insumo no tiene campo 'stock'.")

            # Sumar stock al destino (StockInsumo)
            stock_destino, created = StockInsumo.objects.get_or_create(
                insumo=insumo_destino, deposito=deposito_destino, defaults={"cantidad": 0}
            )
            logger.info(f"[TRANSFERENCIA] Stock destino antes: {stock_destino.cantidad}")
            stock_destino.cantidad += cantidad
            stock_destino.save()
            logger.info(f"[TRANSFERENCIA] Stock destino después: {stock_destino.cantidad}")
            # Sincronizar campo stock del Insumo destino si existe
            if hasattr(insumo_destino, 'stock'):
                insumo_destino.stock = stock_destino.cantidad
                insumo_destino.save(update_fields=["stock"])
                logger.info(f"[TRANSFERENCIA] Insumo destino stock actualizado a {insumo_destino.stock}")
            else:
                logger.warning(f"[TRANSFERENCIA] El modelo Insumo no tiene campo 'stock'.")

            # Registrar movimiento usando la función de auditoría
            _auditar_movimiento(
                tipo="transferencia",
                usuario=request.user,
                insumo=insumo_destino,
                deposito_origen=deposito_origen,
                deposito_destino=deposito_destino,
                cantidad=cantidad,
                motivo=motivo or "Transferencia entre depósitos"
            )
            messages.success(request, "Transferencia realizada correctamente.")
            # Redirigir al historial de transferencias
            return redirect("App_LUMINOVA:historial_transferencias")
    else:
        form = TransferenciaInsumoForm(user=request.user)
    return render(request, "deposito/transferencia_insumo.html", {"form": form})


@login_required
@transaction.atomic
def transferencia_producto_view(request):
    """Vista para transferir productos terminados entre depósitos"""
    # Solo usuarios con rol 'deposito' o 'administrador'
    if not es_admin_o_rol(request.user, ["deposito", "administrador"]):
        messages.error(request, "Acceso denegado. No tiene permisos para transferir productos.")
        return redirect("App_LUMINOVA:deposito_view")

    if request.method == "POST":
        form = TransferenciaProductoForm(request.POST, user=request.user)
        if form.is_valid():
            producto = form.cleaned_data["producto"]
            deposito_origen = form.cleaned_data["deposito_origen"]
            deposito_destino = form.cleaned_data["deposito_destino"]
            cantidad = form.cleaned_data["cantidad"]
            motivo = form.cleaned_data["motivo"]
            
            # Validar que el usuario tenga acceso a ambos depósitos para transferencias
            if not _usuario_puede_acceder_deposito(request.user, deposito_origen, "transferir") or \
               not _usuario_puede_acceder_deposito(request.user, deposito_destino, "transferir"):
                messages.error(request, "No tiene permisos para transferir entre los depósitos seleccionados.")
                return redirect("App_LUMINOVA:transferencia_producto")
            
            from .models import StockProductoTerminado, CategoriaProductoTerminado
            import logging
            logger = logging.getLogger(__name__)

            # Buscar o crear la categoría en el destino
            categoria_destino = CategoriaProductoTerminado.objects.filter(
                nombre=producto.categoria.nombre, 
                deposito=deposito_destino
            ).first()
            if not categoria_destino:
                categoria_destino = CategoriaProductoTerminado.objects.create(
                    nombre=producto.categoria.nombre,
                    imagen=producto.categoria.imagen,
                    deposito=deposito_destino
                )

            # Buscar o crear el producto en el destino
            producto_destino = ProductoTerminado.objects.filter(
                descripcion=producto.descripcion,
                categoria=categoria_destino,
                deposito=deposito_destino
            ).first()
            if not producto_destino:
                producto_destino = ProductoTerminado.objects.create(
                    descripcion=producto.descripcion,
                    categoria=categoria_destino,
                    precio_unitario=producto.precio_unitario,
                    modelo=producto.modelo,
                    potencia=producto.potencia,
                    acabado=producto.acabado,
                    color_luz=producto.color_luz,
                    material=producto.material,
                    imagen=producto.imagen,
                    deposito=deposito_destino
                )

            # Descontar stock del origen
            stock_origen = StockProductoTerminado.objects.get(producto=producto, deposito=deposito_origen)
            logger.info(f"[TRANSFERENCIA PT] Stock origen antes: {stock_origen.cantidad}")
            if stock_origen.cantidad < cantidad:
                messages.error(request, "Stock insuficiente en el depósito de origen.")
                logger.warning(f"[TRANSFERENCIA PT] Stock insuficiente en origen: {stock_origen.cantidad} < {cantidad}")
                return redirect("App_LUMINOVA:transferencia_producto")
            
            stock_origen.cantidad -= cantidad
            stock_origen.save()
            logger.info(f"[TRANSFERENCIA PT] Stock origen después: {stock_origen.cantidad}")
            
            # Sincronizar campo stock del Producto origen si existe
            if hasattr(producto, 'stock'):
                producto.stock = stock_origen.cantidad
                producto.save(update_fields=["stock"])
                logger.info(f"[TRANSFERENCIA PT] Producto origen stock actualizado a {producto.stock}")

            # Sumar stock al destino
            stock_destino, created = StockProductoTerminado.objects.get_or_create(
                producto=producto_destino, 
                deposito=deposito_destino, 
                defaults={"cantidad": 0}
            )
            logger.info(f"[TRANSFERENCIA PT] Stock destino antes: {stock_destino.cantidad}")
            stock_destino.cantidad += cantidad
            stock_destino.save()
            logger.info(f"[TRANSFERENCIA PT] Stock destino después: {stock_destino.cantidad}")
            
            # Sincronizar campo stock del Producto destino si existe
            if hasattr(producto_destino, 'stock'):
                producto_destino.stock = stock_destino.cantidad
                producto_destino.save(update_fields=["stock"])
                logger.info(f"[TRANSFERENCIA PT] Producto destino stock actualizado a {producto_destino.stock}")

            # Registrar movimiento usando la función de auditoría
            _auditar_movimiento(
                tipo="transferencia",
                usuario=request.user,
                producto=producto_destino,
                deposito_origen=deposito_origen,
                deposito_destino=deposito_destino,
                cantidad=cantidad,
                motivo=motivo or "Transferencia entre depósitos"
            )
            
            messages.success(request, "Transferencia de producto realizada correctamente.")
            return redirect("App_LUMINOVA:historial_transferencias")
    else:
        form = TransferenciaProductoForm(user=request.user)
    
    return render(request, "deposito/transferencia_producto.html", {"form": form})


@login_required
@transaction.atomic
def entrada_stock_insumo(request, insumo_id, deposito_id):
    """Registra entrada de stock de insumo"""
    if not es_admin_o_rol(request.user, ["deposito", "administrador"]):
        messages.error(request, "Acceso denegado.")
        return redirect("App_LUMINOVA:deposito_view")
    
    from .models import Insumo, Deposito, StockInsumo
    
    insumo = get_object_or_404(Insumo, id=insumo_id)
    deposito = get_object_or_404(Deposito, id=deposito_id)
    
    if not _usuario_puede_acceder_deposito(request.user, deposito, "entrada"):
        messages.error(request, "No tiene permisos para registrar entradas en este depósito.")
        return redirect("App_LUMINOVA:deposito_view")
    
    if request.method == "POST":
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', 'Entrada manual de stock')
        
        if cantidad > 0:
            # Actualizar stock
            stock, created = StockInsumo.objects.get_or_create(
                insumo=insumo, deposito=deposito, defaults={"cantidad": 0}
            )
            stock.cantidad += cantidad
            stock.save()
            
            # Sincronizar campo stock del insumo si existe
            if hasattr(insumo, 'stock'):
                insumo.stock = stock.cantidad
                insumo.save(update_fields=["stock"])
            
            # Auditar movimiento
            _auditar_movimiento(
                tipo="entrada",
                usuario=request.user,
                insumo=insumo,
                deposito_destino=deposito,
                cantidad=cantidad,
                motivo=motivo
            )
            
            messages.success(request, f"Entrada de {cantidad} unidades registrada correctamente.")
        else:
            messages.error(request, "La cantidad debe ser mayor a 0.")
    
    return redirect("App_LUMINOVA:deposito_view")


@login_required
@transaction.atomic
def salida_stock_insumo(request, insumo_id, deposito_id):
    """Registra salida de stock de insumo"""
    if not es_admin_o_rol(request.user, ["deposito", "administrador"]):
        messages.error(request, "Acceso denegado.")
        return redirect("App_LUMINOVA:deposito_view")
    
    from .models import Insumo, Deposito, StockInsumo
    
    insumo = get_object_or_404(Insumo, id=insumo_id)
    deposito = get_object_or_404(Deposito, id=deposito_id)
    
    if not _usuario_puede_acceder_deposito(request.user, deposito, "salida"):
        messages.error(request, "No tiene permisos para registrar salidas en este depósito.")
        return redirect("App_LUMINOVA:deposito_view")
    
    if request.method == "POST":
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', 'Salida manual de stock')
        
        if cantidad > 0:
            try:
                stock = StockInsumo.objects.get(insumo=insumo, deposito=deposito)
                if stock.cantidad >= cantidad:
                    stock.cantidad -= cantidad
                    stock.save()
                    
                    # Sincronizar campo stock del insumo si existe
                    if hasattr(insumo, 'stock'):
                        insumo.stock = stock.cantidad
                        insumo.save(update_fields=["stock"])
                    
                    # Auditar movimiento
                    _auditar_movimiento(
                        tipo="salida",
                        usuario=request.user,
                        insumo=insumo,
                        deposito_origen=deposito,
                        cantidad=cantidad,
                        motivo=motivo
                    )
                    
                    messages.success(request, f"Salida de {cantidad} unidades registrada correctamente.")
                else:
                    messages.error(request, f"Stock insuficiente. Disponible: {stock.cantidad}")
            except StockInsumo.DoesNotExist:
                messages.error(request, "No hay stock disponible para este insumo en el depósito.")
        else:
            messages.error(request, "La cantidad debe ser mayor a 0.")
    
    return redirect("App_LUMINOVA:deposito_view")


@login_required
@transaction.atomic
def entrada_stock_producto(request, producto_id, deposito_id):
    """Registra entrada de stock de producto terminado"""
    if not es_admin_o_rol(request.user, ["deposito", "administrador"]):
        messages.error(request, "Acceso denegado.")
        return redirect("App_LUMINOVA:deposito_view")
    
    from .models import ProductoTerminado, Deposito, StockProductoTerminado
    
    producto = get_object_or_404(ProductoTerminado, id=producto_id)
    deposito = get_object_or_404(Deposito, id=deposito_id)
    
    if not _usuario_puede_acceder_deposito(request.user, deposito, "entrada"):
        messages.error(request, "No tiene permisos para registrar entradas en este depósito.")
        return redirect("App_LUMINOVA:deposito_view")
    
    if request.method == "POST":
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', 'Entrada manual de stock')
        
        if cantidad > 0:
            # Actualizar stock
            stock, created = StockProductoTerminado.objects.get_or_create(
                producto=producto, deposito=deposito, defaults={"cantidad": 0}
            )
            stock.cantidad += cantidad
            stock.save()
            
            # Sincronizar campo stock del producto si existe
            if hasattr(producto, 'stock'):
                producto.stock = stock.cantidad
                producto.save(update_fields=["stock"])
            
            # Auditar movimiento
            _auditar_movimiento(
                tipo="entrada",
                usuario=request.user,
                producto=producto,
                deposito_destino=deposito,
                cantidad=cantidad,
                motivo=motivo
            )
            
            messages.success(request, f"Entrada de {cantidad} unidades registrada correctamente.")
        else:
            messages.error(request, "La cantidad debe ser mayor a 0.")
    
    return redirect("App_LUMINOVA:deposito_view")


@login_required
@transaction.atomic
def salida_stock_producto(request, producto_id, deposito_id):
    """Registra salida de stock de producto terminado"""
    if not es_admin_o_rol(request.user, ["deposito", "administrador"]):
        messages.error(request, "Acceso denegado.")
        return redirect("App_LUMINOVA:deposito_view")
    
    from .models import ProductoTerminado, Deposito, StockProductoTerminado
    
    producto = get_object_or_404(ProductoTerminado, id=producto_id)
    deposito = get_object_or_404(Deposito, id=deposito_id)
    
    if not _usuario_puede_acceder_deposito(request.user, deposito, "salida"):
        messages.error(request, "No tiene permisos para registrar salidas en este depósito.")
        return redirect("App_LUMINOVA:deposito_view")
    
    if request.method == "POST":
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', 'Salida manual de stock')
        
        if cantidad > 0:
            try:
                stock = StockProductoTerminado.objects.get(producto=producto, deposito=deposito)
                if stock.cantidad >= cantidad:
                    stock.cantidad -= cantidad
                    stock.save()
                    
                    # Sincronizar campo stock del producto si existe
                    if hasattr(producto, 'stock'):
                        producto.stock = stock.cantidad
                        producto.save(update_fields=["stock"])
                    
                    # Auditar movimiento
                    _auditar_movimiento(
                        tipo="salida",
                        usuario=request.user,
                        producto=producto,
                        deposito_origen=deposito,
                        cantidad=cantidad,
                        motivo=motivo
                    )
                    
                    messages.success(request, f"Salida de {cantidad} unidades registrada correctamente.")
                else:
                    messages.error(request, f"Stock insuficiente. Disponible: {stock.cantidad}")
            except StockProductoTerminado.DoesNotExist:
                messages.error(request, "No hay stock disponible para este producto en el depósito.")
        else:
            messages.error(request, "La cantidad debe ser mayor a 0.")
    
    return redirect("App_LUMINOVA:deposito_view")
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
    Deposito,
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
)
from .signals import get_client_ip

from .services.document_services import generar_siguiente_numero_documento
from .services.pdf_services import generar_pdf_factura
from .utils import es_admin, es_admin_o_rol
from django.shortcuts import render, redirect, get_object_or_404
from .models import Deposito, Insumo, ProductoTerminado

logger = logging.getLogger(__name__)


# --- SELECTOR DE DEPÓSITOS ---
def seleccionar_deposito_view(request):
    depositos = Deposito.objects.all()
    if request.method == "POST":
        deposito_id = request.POST.get("deposito_id")
        if deposito_id:
            request.session["deposito_seleccionado"] = deposito_id
            return redirect("App_LUMINOVA:deposito_view")
    return render(request, "deposito/seleccionar_deposito.html", {"depositos": depositos})


def deposito_dashboard_view(request):
    deposito_id = request.session.get("deposito_seleccionado")
    if not deposito_id:
        return redirect("App_LUMINOVA:seleccionar_deposito")
    deposito = get_object_or_404(Deposito, id=deposito_id)
    insumos_count = Insumo.objects.filter(deposito=deposito).count()
    productos_count = ProductoTerminado.objects.filter(deposito=deposito).count()
    context = {
        "deposito": deposito,
        "insumos_count": insumos_count,
        "productos_count": productos_count,
    }
    return render(request, "deposito/deposito_dashboard.html", context)

# --- DEPÓSITO VIEWS ---
@login_required
@transaction.atomic
def deposito_enviar_insumos_op_view(request, op_id):
    op = get_object_or_404(
        OrdenProduccion.objects.select_related(
            "orden_venta_origen",
            "producto_a_producir",  # Necesario para los componentes
        ),
        id=op_id,
    )
    logger.info(
        f"Procesando envío de insumos para OP: {op.numero_op} (Estado actual: {op.estado_op.nombre if op.estado_op else 'N/A'})"
    )

    if request.method == "POST":
        # Solo permitir esta acción si la OP está en "Insumos Solicitados"
        if not op.estado_op or op.estado_op.nombre.lower() != "insumos solicitados":
            messages.error(
                request,
                f"La OP {op.numero_op} no está en estado 'Insumos Solicitados'. No se pueden enviar insumos.",
            )
            return redirect("App_LUMINOVA:deposito_detalle_solicitud_op", op_id=op.id)

        insumos_descontados_correctamente = True
        errores_stock = []

        if not op.producto_a_producir:
            messages.error(
                request,
                f"Error crítico: La OP {op.numero_op} no tiene un producto asignado.",
            )
            return redirect("App_LUMINOVA:deposito_detalle_solicitud_op", op_id=op.id)

        componentes_requeridos = ComponenteProducto.objects.filter(
            producto_terminado=op.producto_a_producir
        ).select_related("insumo")

        if not componentes_requeridos.exists():
            messages.error(
                request,
                f"No se puede procesar: No hay BOM definido para el producto '{op.producto_a_producir.descripcion}'.",
            )
            logger.error(
                f"BOM no definido para producto {op.producto_a_producir.id} en OP {op.numero_op}"
            )
            return redirect("App_LUMINOVA:deposito_detalle_solicitud_op", op_id=op.id)

        for comp in componentes_requeridos:
            cantidad_a_descontar = comp.cantidad_necesaria * op.cantidad_a_producir
            try:
                # Bloquear la fila del insumo para evitar condiciones de carrera (si tu DB lo soporta bien)
                # insumo_a_actualizar = Insumo.objects.select_for_update().get(id=comp.insumo.id)
                insumo_a_actualizar = Insumo.objects.get(
                    id=comp.insumo.id
                )  # Versión más simple

                if insumo_a_actualizar.stock >= cantidad_a_descontar:
                    # Usar F() expression para una actualización atómica es preferible
                    Insumo.objects.filter(id=insumo_a_actualizar.id).update(
                        stock=F("stock") - cantidad_a_descontar
                    )
                    logger.info(
                        f"Stock de '{insumo_a_actualizar.descripcion}' (ID: {insumo_a_actualizar.id}) descontado en {cantidad_a_descontar}."
                    )
                else:
                    errores_stock.append(
                        f"Stock insuficiente para '{insumo_a_actualizar.descripcion}'. Requeridos: {cantidad_a_descontar}, Disponible: {insumo_a_actualizar.stock}"
                    )
                    insumos_descontados_correctamente = False
                    # Aquí podrías decidir si continuar verificando otros insumos o hacer break.
                    # Si haces break, solo se reportará el primer error de stock.
            except Insumo.DoesNotExist:
                errores_stock.append(
                    f"Insumo '{comp.insumo.descripcion}' (ID: {comp.insumo.id}) no encontrado durante el descuento. Error de datos."
                )
                insumos_descontados_correctamente = False
                break  # Error crítico, no continuar si un insumo del BOM no existe

        if errores_stock:  # Si hubo algún error de stock
            for error_msg in errores_stock:
                messages.error(request, error_msg)
            # No es necesario reasignar insumos_descontados_correctamente = False aquí, ya se hizo.

        if insumos_descontados_correctamente:
            try:
                # Estado al que pasa la OP DESPUÉS de que Depósito envía los insumos
                nombre_estado_op_post_deposito = (
                    "Insumos Recibidos"  # ESTE ES EL NUEVO ESTADO OBJETIVO
                )

                estado_siguiente_op_obj = EstadoOrden.objects.get(
                    nombre__iexact=nombre_estado_op_post_deposito
                )

                op.estado_op = estado_siguiente_op_obj
                # Considera si fecha_inicio_real se debe setear aquí o cuando producción realmente empieza.
                # Si es cuando depósito entrega, está bien.
                if (
                    not op.fecha_inicio_real
                ):  # O un nuevo campo como 'fecha_insumos_entregados'
                    op.fecha_inicio_real = timezone.now()
                op.save(update_fields=["estado_op", "fecha_inicio_real"])

                messages.success(
                    request,
                    f"Insumos para OP {op.numero_op} marcados como enviados/recibidos. OP ahora en estado '{estado_siguiente_op_obj.nombre}'.",
                )
                logger.info(
                    f"OP {op.numero_op} actualizada a estado '{estado_siguiente_op_obj.nombre}' por Depósito."
                )

                # La OV podría seguir en "INSUMOS_SOLICITADOS" o pasar a un estado intermedio si lo tienes.
                # La transición a "PRODUCCION_INICIADA" para la OV debería ocurrir cuando Producción
                # explícitamente inicia la OP (cambiándola de "Insumos Recibidos" a "Producción Iniciada").
                # No hay cambio directo de estado de OV aquí, se deja a la lógica de produccion_detalle_op_view.

            except EstadoOrden.DoesNotExist:
                messages.error(
                    request,
                    f"Error de Configuración: El estado de OP '{nombre_estado_op_post_deposito}' no fue encontrado. Insumos descontados, pero el estado de la OP no se actualizó correctamente. Por favor, cree este estado en el panel de administración.",
                )
                logger.error(
                    f"CRÍTICO: Estado OP '{nombre_estado_op_post_deposito}' no encontrado. OP {op.numero_op} podría quedar en estado incorrecto."
                )
            return redirect(
                "App_LUMINOVA:deposito_solicitudes_insumos"
            )  # Vuelve a la lista de solicitudes pendientes
        else:  # Hubo errores de stock
            logger.warning(
                f"Errores de stock al procesar OP {op.numero_op}. Redirigiendo a detalle de solicitud."
            )
            return redirect("App_LUMINOVA:deposito_detalle_solicitud_op", op_id=op.id)

    # Si es GET
    messages.info(
        request,
        "Esta acción de enviar insumos debe realizarse mediante POST desde la página de detalle de la solicitud.",
    )
    return redirect("App_LUMINOVA:deposito_detalle_solicitud_op", op_id=op.id)


@login_required
def deposito_solicitudes_insumos_view(request):
    ops_pendientes_preparacion = OrdenProduccion.objects.none()
    ops_con_insumos_enviados = OrdenProduccion.objects.none()

    titulo_seccion = "Gestión de Insumos para Producción"  # Correcto
    logger.info(
        "--- Entrando a deposito_solicitudes_insumos_view ---"
    )  # Log de entrada

    try:
        # 1. OBTENER OPs QUE ESTÁN SOLICITANDO INSUMOS
        estado_insumos_solicitados_obj = EstadoOrden.objects.filter(
            nombre__iexact="Insumos Solicitados"
        ).first()  # Renombrado para claridad

        if estado_insumos_solicitados_obj:
            logger.info(
                f"Estado 'Insumos Solicitados' encontrado (ID: {estado_insumos_solicitados_obj.id}, Nombre: '{estado_insumos_solicitados_obj.nombre}')."
            )
            ops_pendientes_preparacion = (
                OrdenProduccion.objects.filter(
                    estado_op=estado_insumos_solicitados_obj  # Usar el objeto encontrado
                )
                .select_related(
                    "producto_a_producir", "estado_op", "orden_venta_origen__cliente"
                )
                .order_by("fecha_solicitud")
            )
            logger.info(
                f"Encontradas {ops_pendientes_preparacion.count()} OPs pendientes de preparación."
            )
        else:
            messages.error(
                request,
                "Configuración crítica: El estado 'Insumos Solicitados' no existe en la base de datos. No se pueden mostrar las solicitudes pendientes.",
            )
            logger.error(
                "CRÍTICO: Estado 'Insumos Solicitados' no encontrado en deposito_solicitudes_insumos_view."
            )

        # 2. OBTENER OPs A LAS QUE YA SE LES ENVIARON INSUMOS (AHORA EN ESTADO "En Proceso")
        estado_en_proceso_nombre_buscado = "En Proceso"
        estado_en_proceso_obj = EstadoOrden.objects.filter(
            nombre__iexact=estado_en_proceso_nombre_buscado
        ).first()  # Renombrado

        if estado_en_proceso_obj:
            logger.info(
                f"Estado '{estado_en_proceso_nombre_buscado}' encontrado (ID: {estado_en_proceso_obj.id}, Nombre: '{estado_en_proceso_obj.nombre}')."
            )
            ops_con_insumos_enviados = (
                OrdenProduccion.objects.filter(
                    estado_op=estado_en_proceso_obj  # Usar el objeto encontrado
                )
                .select_related(
                    "producto_a_producir", "estado_op", "orden_venta_origen__cliente"
                )
                .order_by("-fecha_inicio_real", "-fecha_solicitud")
            )
            logger.info(
                f"Encontradas {ops_con_insumos_enviados.count()} OPs con insumos ya enviados/en proceso."
            )
        else:
            messages.warning(
                request,
                f"Advertencia de configuración: El estado '{estado_en_proceso_nombre_buscado}' no existe. No se mostrará la lista de OPs con insumos enviados.",
            )
            logger.warning(
                f"Configuración: Estado '{estado_en_proceso_nombre_buscado}' no encontrado en deposito_solicitudes_insumos_view."
            )

    except Exception as e:  # Captura más genérica para cualquier otro error inesperado
        messages.error(
            request,
            f"Ocurrió un error inesperado al cargar las solicitudes de insumos: {e}",
        )
        logger.exception("Excepción inesperada en deposito_solicitudes_insumos_view:")
        # ops_pendientes_preparacion y ops_con_insumos_enviados ya están como QuerySet vacíos.

    context = {
        "ops_pendientes_list": ops_pendientes_preparacion,
        "ops_enviadas_list": ops_con_insumos_enviados,
        "titulo_seccion": titulo_seccion,
    }
    logger.info(
        f"Contexto para deposito_solicitudes_insumos.html: ops_pendientes_list count = {ops_pendientes_preparacion.count()}, ops_enviadas_list count = {ops_con_insumos_enviados.count()}"
    )
    return render(request, "deposito/deposito_solicitudes_insumos.html", context)


@login_required
def recepcion_pedidos_view(request):
    """
    Muestra una lista de Órdenes de Compra que están "En Tránsito" y listas para ser recibidas.
    """
    # if not es_admin_o_rol(request.user, ['deposito', 'administrador']):
    #     messages.error(request, "Acceso no permitido.")
    #     return redirect('App_LUMINOVA:dashboard')

    ocs_en_transito = (
        Orden.objects.filter(tipo="compra", estado="EN_TRANSITO")
        .select_related("proveedor", "insumo_principal")
        .order_by("fecha_estimada_entrega")
    )

    context = {
        "ordenes_a_recibir": ocs_en_transito,
        "titulo_seccion": "Recepción de Pedidos de Compra",
    }
    return render(request, "deposito/deposito_recepcion.html", context)


@login_required
@require_POST
@transaction.atomic
def recibir_pedido_oc_view(request, oc_id):
    """
    Procesa la recepción de una Orden de Compra.
    """
    # if not es_admin_o_rol(request.user, ['deposito', 'administrador']):
    #     messages.error(request, "Acción no permitida.")
    #     return redirect('App_LUMINOVA:deposito_recepcion_pedidos')

    orden_a_recibir = get_object_or_404(Orden, id=oc_id, estado="EN_TRANSITO")

    insumo_recibido = orden_a_recibir.insumo_principal
    cantidad_recibida = orden_a_recibir.cantidad_principal

    if insumo_recibido and cantidad_recibida:
        # 1. Incrementar el stock del insumo
        insumo_recibido.stock = F("stock") + cantidad_recibida

        # 2. Decrementar la cantidad en pedido
        insumo_recibido.cantidad_en_pedido = F("cantidad_en_pedido") - cantidad_recibida

        insumo_recibido.save(update_fields=["stock", "cantidad_en_pedido"])
        logger.info(
            f"Stock de '{insumo_recibido.descripcion}' actualizado (+{cantidad_recibida}) y 'en pedido' actualizado (-{cantidad_recibida})."
        )

        # 3. Actualizar el estado de la OC a "Completada" (o "Recibida Totalmente")
        orden_a_recibir.estado = "COMPLETADA"
        orden_a_recibir.save(update_fields=["estado"])

        messages.success(
            request,
            f"Pedido {orden_a_recibir.numero_orden} recibido exitosamente. Se agregaron {cantidad_recibida} unidades de '{insumo_recibido.descripcion}' al stock.",
        )
    else:
        messages.error(
            request,
            f"Error: La OC {orden_a_recibir.numero_orden} no tiene un insumo o cantidad principal válidos.",
        )

    return redirect("App_LUMINOVA:deposito_recepcion_pedidos")


@login_required
def deposito_view(request):
    logger.info("--- deposito_view: INICIO ---")

    # Validación de permisos de acceso
    if not (request.user.is_superuser or request.user.groups.filter(name='Depósito').exists()):
        return HttpResponseForbidden("No tienes permisos para acceder a depósitos.")

    deposito_id = request.session.get("deposito_seleccionado")
    deposito = get_object_or_404(Deposito, id=deposito_id)

    # Validar que el usuario tenga asignado el depósito (excepto admin)
    if not request.user.is_superuser:
        if not UsuarioDeposito.objects.filter(usuario=request.user, deposito=deposito).exists():
            return HttpResponseForbidden("No tienes acceso a este depósito.")

    categorias_I = CategoriaInsumo.objects.filter(deposito=deposito)
    categorias_PT = CategoriaProductoTerminado.objects.filter(deposito=deposito)

    # OPs pendientes SOLO del depósito seleccionado
    ops_pendientes_deposito_list = OrdenProduccion.objects.none()
    ops_pendientes_deposito_count = 0
    try:
        estado_sol = EstadoOrden.objects.filter(
            nombre__iexact="Insumos Solicitados"
        ).first()
        if estado_sol:
            ops_pendientes_deposito_list = (
                OrdenProduccion.objects.filter(
                    estado_op=estado_sol,
                    producto_a_producir__deposito=deposito
                )
                .select_related("producto_a_producir")
                .order_by("fecha_solicitud")
            )
            ops_pendientes_deposito_count = ops_pendientes_deposito_list.count()
    except Exception as e_op:
        logger.error(f"Deposito_view (OPs): Excepción al cargar OPs: {e_op}")

    # Lotes de productos terminados en stock SOLO de este depósito
    lotes_en_stock = (
        LoteProductoTerminado.objects.filter(enviado=False, producto__deposito=deposito)
        .select_related("producto", "op_asociada")
        .order_by("-fecha_creacion")
    )

    # Insumos con stock bajo SOLO de este depósito
    UMBRAL_STOCK_BAJO_INSUMOS = 15000

    # Refuerza la sincronización: SIEMPRE actualiza StockInsumo con el valor actual de stock de Insumo
    from .models import StockInsumo
    insumos_del_deposito = Insumo.objects.filter(deposito=deposito)
    for insumo in insumos_del_deposito:
        stock_obj, created = StockInsumo.objects.get_or_create(insumo=insumo, deposito=deposito, defaults={"cantidad": insumo.stock})
        # Siempre sincroniza, aunque el valor sea igual (por si hay triggers externos)
        if stock_obj.cantidad != insumo.stock:
            stock_obj.cantidad = insumo.stock
            stock_obj.save()

    # Obtener insumos con stock bajo según StockInsumo
    stock_insumos_bajo = StockInsumo.objects.filter(
        deposito=deposito, cantidad__lt=UMBRAL_STOCK_BAJO_INSUMOS
    ).select_related('insumo')
    insumos_con_stock_bajo = [si.insumo for si in stock_insumos_bajo]

    # Estados que consideramos como "pedido en firme"
    ESTADOS_OC_EN_PROCESO = [
        "APROBADA",
        "ENVIADA_PROVEEDOR",
        "EN_TRANSITO",
        "RECIBIDA_PARCIAL",
    ]

    insumos_a_gestionar = []
    insumos_en_pedido = []

    for stock_insumo in stock_insumos_bajo:
        insumo = stock_insumo.insumo
        oc_en_proceso = (
            Orden.objects.filter(
                insumo_principal=insumo, estado__in=ESTADOS_OC_EN_PROCESO
            )
            .order_by("-fecha_creacion")
            .first()
        )
        if oc_en_proceso:
            insumos_en_pedido.append({"insumo": insumo, "oc": oc_en_proceso, "stock_real": stock_insumo.cantidad})
        else:
            insumos_a_gestionar.append({"insumo": insumo, "stock_real": stock_insumo.cantidad})

    context = {
        "deposito": deposito,
        "categorias_I": categorias_I,
        "categorias_PT": categorias_PT,
        "ops_pendientes_deposito_list": ops_pendientes_deposito_list,
        "ops_pendientes_deposito_count": ops_pendientes_deposito_count,
        "lotes_productos_terminados_en_stock": lotes_en_stock,
        "insumos_a_gestionar_list": insumos_a_gestionar,
        "insumos_en_pedido_list": insumos_en_pedido,
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO_INSUMOS,
    }

    return render(request, "deposito/deposito.html", context)


@login_required
def deposito_solicitudes_insumos_view(request):
    # if not es_admin_o_rol(request.user, ['deposito', 'administrador']): # Control de permisos
    #     messages.error(request, "Acceso denegado.")
    #     return redirect('App_LUMINOVA:dashboard')

    ops_necesitan_insumos = (
        OrdenProduccion.objects.none()
    )  # Inicializar con un queryset vacío

    try:
        estado_objetivo = EstadoOrden.objects.get(nombre__iexact="Insumos Solicitados")
        ops_necesitan_insumos = (
            OrdenProduccion.objects.filter(  # ASIGNACIÓN AQUÍ (Camino A)
                estado_op=estado_objetivo
            )
            .select_related(
                "producto_a_producir", "estado_op", "orden_venta_origen__cliente"
            )
            .order_by("fecha_solicitud")
        )

    except EstadoOrden.DoesNotExist:
        messages.error(
            request,
            "Error: El estado 'Insumos Solicitados' no está configurado para las Órdenes de Producción. No se pueden listar las solicitudes.",
        )
        # ops_necesitan_insumos ya es un queryset vacío, así que está bien.
        # O podrías decidir mostrar un error más prominente o redirigir.
        # Para mantener la funcionalidad de la plantilla, dejaremos ops_necesitan_insumos como un queryset vacío.

    context = {
        "ops_necesitan_insumos_list": ops_necesitan_insumos,
        "titulo_seccion": "Solicitudes de Insumos desde Producción",
    }
    return render(request, "deposito/deposito_solicitudes_insumos.html", context)


@login_required
def deposito_detalle_solicitud_op_view(request, op_id):
    """
    Muestra el detalle de una OP desde la perspectiva del depósito,
    listando los insumos necesarios, su stock y si son suficientes.
    Permite confirmar el envío/descuento de insumos.
    """
    # if not es_admin_o_rol(request.user, ['deposito', 'administrador']): # Control de permisos
    #     messages.error(request, "Acceso denegado.")
    #     return redirect('App_LUMINOVA:dashboard')

    op = get_object_or_404(
        OrdenProduccion.objects.select_related("producto_a_producir", "estado_op"),
        id=op_id,
    )
    insumos_necesarios_data = []
    todos_los_insumos_disponibles = (
        True  # Asumir que sí hasta que se demuestre lo contrario
    )

    if op.producto_a_producir:
        componentes_requeridos = ComponenteProducto.objects.filter(
            producto_terminado=op.producto_a_producir
        ).select_related("insumo")

        if not componentes_requeridos.exists():
            messages.warning(
                request,
                f"No se ha definido el BOM (lista de componentes) para el producto '{op.producto_a_producir.descripcion}'. No se pueden determinar los insumos.",
            )
            todos_los_insumos_disponibles = False  # No se puede proceder

        for comp in componentes_requeridos:
            cantidad_total_req = comp.cantidad_necesaria * op.cantidad_a_producir
            suficiente = comp.insumo.stock >= cantidad_total_req
            if not suficiente:
                todos_los_insumos_disponibles = False
            insumos_necesarios_data.append(
                {
                    "insumo_id": comp.insumo.id,
                    "insumo_descripcion": comp.insumo.descripcion,
                    "cantidad_total_requerida_op": cantidad_total_req,
                    "stock_actual_insumo": comp.insumo.stock,
                    "suficiente_stock": suficiente,
                }
            )

    context = {
        "op": op,
        "insumos_necesarios_list": insumos_necesarios_data,
        "todos_los_insumos_disponibles": todos_los_insumos_disponibles,  # Para habilitar/deshabilitar botón
        "titulo_seccion": f"Detalle Solicitud Insumos para OP: {op.numero_op}",
    }
    return render(request, "deposito/deposito_detalle_solicitud_op.html", context)


@login_required
@require_POST
@transaction.atomic
def deposito_enviar_lote_pt_view(request, lote_id):
    """
    Procesa el envío de un lote de producto terminado.
    - Descuenta el stock del producto.
    - Marca el lote como enviado.
    - Actualiza el estado de la OV si corresponde.
    """
    lote = get_object_or_404(
        LoteProductoTerminado.objects.select_related(
            "producto", "op_asociada__orden_venta_origen"
        ),
        id=lote_id,
    )

    if lote.enviado:
        messages.warning(
            request,
            f"El lote del producto '{lote.producto.descripcion}' ya fue enviado anteriormente.",
        )
        return redirect("App_LUMINOVA:deposito_view")

    producto_terminado = lote.producto
    cantidad_a_enviar = lote.cantidad

    if producto_terminado.stock < cantidad_a_enviar:
        messages.error(
            request,
            f"Error de consistencia de datos: No hay stock suficiente para '{producto_terminado.descripcion}' para enviar el lote. Stock actual: {producto_terminado.stock}, se necesita: {cantidad_a_enviar}.",
        )
        return redirect("App_LUMINOVA:deposito_view")

    producto_terminado.stock -= cantidad_a_enviar
    producto_terminado.save(update_fields=["stock"])
    logger.info(
        f"Stock de '{producto_terminado.descripcion}' descontado en {cantidad_a_enviar}."
    )

    lote.enviado = True
    lote.save(update_fields=["enviado"])
    logger.info(
        f"Lote ID {lote.id} (OP: {lote.op_asociada.numero_op}) marcado como enviado."
    )

    # Registro en el historial
    if lote.op_asociada.orden_venta_origen:
        HistorialOV.objects.create(
            orden_venta=lote.op_asociada.orden_venta_origen,
            descripcion=f"Lote de {lote.cantidad} x '{lote.producto.descripcion}' (de OP {lote.op_asociada.numero_op}) enviado al cliente.",
            tipo_evento="Envío",
            realizado_por=request.user,
        )

    orden_venta = lote.op_asociada.orden_venta_origen
    if orden_venta:
        todos_los_lotes_de_la_ov = LoteProductoTerminado.objects.filter(
            op_asociada__orden_venta_origen=orden_venta
        )
        if not todos_los_lotes_de_la_ov.filter(enviado=False).exists():
            estado_ov_anterior_str = orden_venta.get_estado_display()
            orden_venta.estado = "COMPLETADA"
            orden_venta.save(update_fields=["estado"])

            # Log de cambio de estado de OV
            descripcion_ov = f"Estado de la Orden de Venta cambió de '{estado_ov_anterior_str}' a 'Completada/Entregada'."
            HistorialOV.objects.create(
                orden_venta=orden_venta,
                descripcion=descripcion_ov,
                tipo_evento="Cambio Estado OV",
                realizado_por=request.user,
            )

            messages.info(
                request,
                f"Todos los lotes para la OV '{orden_venta.numero_ov}' han sido enviados. La orden se ha marcado como 'Completada/Entregada'.",
            )
            logger.info(f"OV {orden_venta.numero_ov} actualizada a COMPLETADA.")

    messages.success(
        request,
        f"Lote de {cantidad_a_enviar} x '{producto_terminado.descripcion}' enviado exitosamente.",
    )
    return redirect("App_LUMINOVA:deposito_view")

