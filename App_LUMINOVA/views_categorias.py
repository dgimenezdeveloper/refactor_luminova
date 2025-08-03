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
)
from .signals import get_client_ip

from .services.document_services import generar_siguiente_numero_documento
from .services.pdf_services import generar_pdf_factura
from .utils import es_admin, es_admin_o_rol

logger = logging.getLogger(__name__)



# --- CLASS-BASED VIEWS (CRUDs) ---
class Categoria_IListView(ListView):
    model = CategoriaInsumo
    template_name = "deposito/deposito_view.html"
    context_object_name = (
        "categorias_I"  # Para diferenciar en el template deposito.html
    )


class Categoria_IDetailView(DetailView):
    model = CategoriaInsumo
    template_name = "deposito/categoria_insumo_detail.html"
    context_object_name = "categoria_I"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["insumos_de_categoria"] = Insumo.objects.filter(categoria=self.object)
        return context


class Categoria_ICreateView(CreateView):
    def form_valid(self, form):
        deposito_id = self.request.session.get("deposito_seleccionado")
        if deposito_id:
            from .models import Deposito
            deposito = Deposito.objects.get(id=deposito_id)
            form.instance.deposito = deposito
        return super().form_valid(form)
    model = CategoriaInsumo
    template_name = "deposito/categoria_insumo_crear.html"
    fields = ("nombre", "imagen")
    success_url = reverse_lazy("App_LUMINOVA:deposito_view")


class Categoria_IUpdateView(UpdateView):
    model = CategoriaInsumo
    template_name = "deposito/categoria_insumo_editar.html"
    fields = ("nombre", "imagen")
    context_object_name = "categoria"
    success_url = reverse_lazy("App_LUMINOVA:deposito_view")


class Categoria_IDeleteView(DeleteView):
    model = CategoriaInsumo
    template_name = "deposito/categoria_insumo_confirm_delete.html"
    context_object_name = "categoria"
    success_url = reverse_lazy("App_LUMINOVA:deposito_view")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasar los insumos protegidos a la plantilla para que se puedan listar
        # (Esto se podría hacer de forma más compleja si quieres una lista completa en caso de error,
        # pero el mensaje de ProtectedError ya los lista)
        context["insumos_asociados_count"] = (
            self.object.insumos.count()
        )  # insumos es el related_name
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            # Intenta eliminar el objeto
            response = super().delete(request, *args, **kwargs)
            messages.success(
                request,
                f"Categoría de Insumo '{self.object.nombre}' eliminada exitosamente.",
            )
            return response
        except ProtectedError as e:
            # e.protected_objects contiene los objetos que impiden la eliminación
            nombres_insumos_protegidos = [str(insumo) for insumo in e.protected_objects]
            mensaje_error = (
                f"No se puede eliminar la categoría '{self.object.nombre}' porque está "
                f"siendo utilizada por los siguientes insumos: {', '.join(nombres_insumos_protegidos)}. "
                "Por favor, reasigne o elimine estos insumos primero."
            )
            messages.error(request, mensaje_error)
            logger.warning(
                f"Intento fallido de eliminar CategoriaInsumo ID {self.object.id} debido a ProtectedError: {e}"
            )
            # Redirigir de vuelta a la página de detalle de la categoría o a la confirmación de borrado
            return redirect("App_LUMINOVA:categoria_i_detail", pk=self.object.pk)
            # O a: return self.get(request, *args, **kwargs) para volver a mostrar la página de confirmación con el mensaje


# --- CRUD Categorias Producto Terminado ---
class Categoria_PTListView(ListView):
    model = CategoriaProductoTerminado
    template_name = "deposito/deposito.html"
    context_object_name = "categorias_PT"


class Categoria_PTDetailView(DetailView):
    model = CategoriaProductoTerminado
    template_name = "deposito/categoria_producto_terminado_detail.html"
    context_object_name = "categoria_PT"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["productos_de_categoria"] = ProductoTerminado.objects.filter(
            categoria=self.object
        )
        return context


class Categoria_PTCreateView(CreateView):
    def form_valid(self, form):
        deposito_id = self.request.session.get("deposito_seleccionado")
        if deposito_id:
            from .models import Deposito
            deposito = Deposito.objects.get(id=deposito_id)
            form.instance.deposito = deposito
        return super().form_valid(form)
    model = CategoriaProductoTerminado
    template_name = "deposito/categoria_producto_terminado_crear.html"
    fields = ("nombre", "imagen")
    success_url = reverse_lazy("App_LUMINOVA:deposito_view")


class Categoria_PTUpdateView(UpdateView):
    model = CategoriaProductoTerminado
    template_name = "deposito/categoria_producto_terminado_editar.html"
    fields = ("nombre", "imagen")
    context_object_name = "categoria"
    success_url = reverse_lazy("App_LUMINOVA:deposito_view")


class Categoria_PTDeleteView(DeleteView):
    model = CategoriaProductoTerminado
    template_name = "deposito/categoria_producto_terminado_confirm_delete.html"
    context_object_name = "categoria"  # 'categoria' se usa en la plantilla
    success_url = reverse_lazy("App_LUMINOVA:deposito_view")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasar los productos terminados asociados a la plantilla para información
        context["productos_asociados_count"] = self.object.productos_terminados.count()
        if context["productos_asociados_count"] > 0:
            # Pasar una lista pequeña para mostrar ejemplos si es necesario,
            # aunque el mensaje de error ya los listará si ocurre el ProtectedError.
            context["productos_ejemplo"] = self.object.productos_terminados.all()[
                :5
            ]  # Muestra hasta 5 ejemplos
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()  # Es importante tener el objeto disponible
        nombre_categoria = self.object.nombre  # Guardar nombre para el mensaje de éxito

        try:
            # super().delete() es lo que realmente llama al self.object.delete()
            response = super().delete(request, *args, **kwargs)
            messages.success(
                request,
                f"Categoría de Producto Terminado '{nombre_categoria}' eliminada exitosamente.",
            )
            return response
        except ProtectedError as e:
            # Construir un mensaje detallado
            nombres_productos_protegidos = [str(pt) for pt in e.protected_objects]
            mensaje_error = (
                f"No se puede eliminar la categoría '{nombre_categoria}' porque está "
                f"siendo utilizada por los siguientes productos terminados: {', '.join(nombres_productos_protegidos)}. "
                "Por favor, reasigne o elimine estos productos primero."
            )
            messages.error(request, mensaje_error)
            logger.warning(
                f"Intento fallido de eliminar CategoriaProductoTerminado ID {self.object.id} ('{nombre_categoria}') debido a ProtectedError: {e}"
            )

            # Redirigir de vuelta a la página de detalle de la categoría
            # o a la confirmación de borrado para que el usuario vea el mensaje.
            # En este caso, volvemos a la página de detalle donde el usuario puede ver los productos.
            return redirect("App_LUMINOVA:categoria_pt_detail", pk=self.object.pk)
            # Alternativa: volver a mostrar la página de confirmación (necesitaría pasar el contexto de nuevo)
            # context = self.get_context_data(object=self.object)
            # return self.render_to_response(context)
