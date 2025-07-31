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
    ProductoTerminadoForm,
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


# Funciones para el CRUD de Productos Terminados
class ProductoTerminadosListView(ListView):
    model = ProductoTerminado
    template_name = "deposito/productoterminados_list.html"
    context_object_name = "productos_terminados"

    def get_queryset(self):
        deposito_id = self.request.session.get("deposito_seleccionado")
        queryset = super().get_queryset()
        if deposito_id:
            queryset = queryset.filter(deposito_id=deposito_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import Deposito
        deposito_id = self.request.session.get("deposito_seleccionado")
        context["depositos"] = Deposito.objects.all()
        context["deposito_seleccionado"] = deposito_id
        return context


class ProductoTerminadoDetailView(DetailView):
    model = ProductoTerminado
    template_name = "deposito/productoterminado_detail.html"
    context_object_name = "producto_terminado"


class ProductoTerminadoCreateView(CreateView):
    model = ProductoTerminado
    template_name = "deposito/productoterminado_crear.html"
    form_class = ProductoTerminadoForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        deposito_id = self.request.session.get("deposito_seleccionado")
        if deposito_id:
            kwargs["deposito"] = deposito_id
        return kwargs


class ProductoTerminadoUpdateView(UpdateView):
    model = ProductoTerminado
    template_name = "deposito/productoterminado_editar.html"
    form_class = ProductoTerminadoForm
    context_object_name = "producto_terminado"

    success_url = reverse_lazy("App_LUMINOVA:deposito_view")


class ProductoTerminadoDeleteView(DeleteView):
    model = ProductoTerminado
    template_name = "deposito/productoterminado_confirm_delete.html"
    context_object_name = "producto_terminado"
    # success_url = reverse_lazy('App_LUMINOVA:deposito_view') # Se manejará con get_success_url

    def get_success_url(self):
        # Redirigir al detalle de la categoría del producto, o a la vista principal de depósito
        if hasattr(self.object, "categoria") and self.object.categoria:
            return reverse_lazy(
                "App_LUMINOVA:categoria_pt_detail",
                kwargs={"pk": self.object.categoria.pk},
            )
        return reverse_lazy("App_LUMINOVA:deposito_view")

    def form_valid(self, form):
        # Guardar descripción para el mensaje antes de borrar
        producto_descripcion = self.object.descripcion
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El producto terminado '{producto_descripcion}' ha sido eliminado exitosamente.",
        )
        return response

    def post(self, request, *args, **kwargs):
        self.object = (
            self.get_object()
        )  # Cargar el objeto para tener acceso a él en caso de error
        try:
            return super().delete(request, *args, **kwargs)
        except ProtectedError as e:
            protecting_objects_details = []
            if hasattr(e, "protected_objects"):
                for obj in e.protected_objects:
                    if isinstance(obj, ItemOrdenVenta):
                        protecting_objects_details.append(
                            f"la Orden de Venta N° {obj.orden_venta.numero_ov}"
                        )
                    elif isinstance(obj, OrdenProduccion):
                        protecting_objects_details.append(
                            f"la Orden de Producción N° {obj.numero_op}"
                        )
                    # Añade más 'elif isinstance' si ProductoTerminado es FK en otros modelos con PROTECT
                    else:
                        protecting_objects_details.append(
                            f"un registro del tipo '{obj.__class__.__name__}'"
                        )

            error_message = f"No se puede eliminar el producto terminado '{self.object.descripcion}' porque está referenciado y protegido."
            if protecting_objects_details:
                error_message += (
                    " Específicamente, es usado por: "
                    + ", ".join(protecting_objects_details)
                    + "."
                )
            error_message += (
                " Por favor, primero elimine o modifique estas referencias."
            )

            messages.error(request, error_message)
            # Redirigir de vuelta a una página relevante donde se muestre el mensaje
            if hasattr(self.object, "categoria") and self.object.categoria:
                return redirect(
                    reverse_lazy(
                        "App_LUMINOVA:categoria_pt_detail",
                        kwargs={"pk": self.object.categoria.pk},
                    )
                )
            return redirect(reverse_lazy("App_LUMINOVA:deposito_view"))

