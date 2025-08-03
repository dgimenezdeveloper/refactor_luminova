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
    InsumoForm,
    InsumoCreateForm,
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


# Funciones para el CRUD de Insumos
class InsumosListView(ListView):
    model = Insumo
    template_name = "deposito/insumos_list.html"
    context_object_name = "insumos"

    def get_queryset(self):
        deposito_id = self.request.session.get("deposito_seleccionado")
        queryset = super().get_queryset()
        if deposito_id:
            queryset = queryset.filter(deposito_id=deposito_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import Deposito
        context["depositos"] = Deposito.objects.all()
        context["deposito_seleccionado"] = self.request.GET.get("deposito", "")
        return context


class InsumoDetailView(DetailView):
    model = Insumo
    template_name = "deposito/insumo_detail.html"
    context_object_name = "insumo"


class InsumoCreateView(CreateView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        deposito_id = self.request.session.get("deposito_seleccionado")
        if deposito_id:
            from .models import Deposito
            try:
                deposito = Deposito.objects.get(id=deposito_id)
                # Si es GET, setear initial; si es POST, inyectar en data
                if self.request.method == "POST":
                    data = kwargs.get("data", self.request.POST).copy()
                    data["deposito"] = deposito.id
                    kwargs["data"] = data
                else:
                    initial = kwargs.get("initial", {}).copy()
                    initial["deposito"] = deposito.id
                    kwargs["initial"] = initial
            except Deposito.DoesNotExist:
                pass
        return kwargs
    model = Insumo
    template_name = "deposito/insumo_crear.html"
    form_class = InsumoCreateForm  # Usar formulario específico para creación

    def form_valid(self, form):
        deposito_id = self.request.session.get("deposito_seleccionado")
        if deposito_id:
            from .models import Deposito
            deposito = Deposito.objects.get(id=deposito_id)
            form.instance.deposito = deposito
        messages.success(
            self.request, f"Insumo '{form.instance.descripcion}' creado exitosamente."
        )
        logger.info(
            f"Insumo creado: {form.instance.descripcion} (ID: {form.instance.id}) por usuario {self.request.user.username}"
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(
            f"InsumoCreateView - Formulario inválido: {form.errors.as_json()}"
        )
        messages.error(
            self.request,
            "Error al crear el insumo. Por favor, revise los campos marcados.",
        )
        return super().form_invalid(form)

    def get_initial(self):
        initial = super().get_initial()
        categoria_id = self.request.GET.get("categoria")
        if categoria_id:
            try:
                initial["categoria"] = CategoriaInsumo.objects.get(pk=categoria_id)
            except CategoriaInsumo.DoesNotExist:
                messages.warning(
                    self.request,
                    "La categoría preseleccionada para el insumo no es válida.",
                )
        return initial

    def get_success_url(self):
        # Redirigir al detalle de la categoría del insumo creado, o a la vista principal de depósito
        if hasattr(self.object, "categoria") and self.object.categoria:
            return reverse_lazy(
                "App_LUMINOVA:categoria_i_detail",
                kwargs={"pk": self.object.categoria.pk},
            )
        return reverse_lazy("App_LUMINOVA:deposito_view")


class InsumoUpdateView(UpdateView):
    model = Insumo
    template_name = "deposito/insumo_editar.html"
    form_class = InsumoForm  # Usar formulario para edición (sin campo depósito)
    context_object_name = "insumo"

    def form_valid(self, form):
        # PRESERVAR SIEMPRE el depósito original - NO CAMBIAR NUNCA
        original_deposito = self.object.deposito
        response = super().form_valid(form)
        
        # Asegurar que el depósito no cambió
        if self.object.deposito != original_deposito:
            self.object.deposito = original_deposito
            self.object.save(update_fields=['deposito'])
        
        messages.success(
            self.request,
            f"Insumo '{self.object.descripcion}' actualizado exitosamente.",
        )
        logger.info(
            f"InsumoUpdateView: Insumo {self.object.id} actualizado. Depósito preservado: {self.object.deposito}"
        )
        return response

    def get_success_url(self):
        if hasattr(self.object, "categoria") and self.object.categoria:
            return reverse_lazy(
                "App_LUMINOVA:categoria_i_detail",
                kwargs={"pk": self.object.categoria.pk},
            )
        return reverse_lazy("App_LUMINOVA:deposito_view")  # Fallback

    def form_invalid(self, form):
        logger.warning(
            f"InsumoUpdateView: Formulario inválido para insumo ID {self.object.id if self.object else 'Nuevo'}. Errores: {form.errors.as_json()}"
        )
        messages.error(
            self.request,
            "Hubo errores al intentar guardar el insumo. Por favor, revise los campos.",
        )
        return super().form_invalid(form)


class InsumoDeleteView(DeleteView):
    model = Insumo
    template_name = "deposito/insumo_confirm_delete.html"
    context_object_name = "insumo"
    # success_url = reverse_lazy('App_LUMINOVA:deposito_view') # success_url se maneja en get_success_url

    def get_success_url(self):
        # Redirigir al detalle de la categoría del insumo eliminado, o a la vista principal de depósito
        if (
            hasattr(self.object, "categoria") and self.object.categoria
        ):  # self.object es el insumo borrado
            return reverse_lazy(
                "App_LUMINOVA:categoria_i_detail",
                kwargs={"pk": self.object.categoria.pk},
            )
        return reverse_lazy("App_LUMINOVA:deposito_view")

    def form_valid(self, form):
        # Este método se llama DESPUÉS de que la eliminación fue exitosa (si no hay ProtectedError)
        # Aquí se guarda el nombre para usarlo en el mensaje ANTES de que self.object se elimine completamente.
        insumo_descripcion = self.object.descripcion
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El insumo '{insumo_descripcion}' ha sido eliminado exitosamente.",
        )
        return response

    def post(self, request, *args, **kwargs):
        self.object = (
            self.get_object()
        )  # Cargar el objeto para tener acceso a él en caso de error
        try:
            # Intenta llamar al método delete de la clase base, que es lo que realmente borra
            # y donde se podría lanzar ProtectedError.
            # Si la eliminación es exitosa, se llamará a form_valid y luego a get_success_url.
            return super().delete(request, *args, **kwargs)
        except ProtectedError as e:
            # Construir un mensaje más detallado sobre qué está protegiendo la eliminación
            protecting_objects = []
            if hasattr(
                e, "protected_objects"
            ):  # e.protected_objects contiene los objetos que causan la protección
                for obj in e.protected_objects:
                    if isinstance(obj, ComponenteProducto):
                        protecting_objects.append(
                            f"el producto terminado '{obj.producto_terminado.descripcion}' (usa {obj.cantidad_necesaria} unidades)"
                        )
                    else:
                        protecting_objects.append(str(obj))  # Representación genérica

            error_message = f"No se puede eliminar el insumo '{self.object.descripcion}' porque está referenciado y protegido."
            if protecting_objects:
                error_message += (
                    " Específicamente, es usado por: "
                    + ", ".join(protecting_objects)
                    + "."
                )
            error_message += (
                " Por favor, primero elimine o modifique estas referencias."
            )

            messages.error(request, error_message)
            # Redirigir de vuelta a la página de confirmación de borrado o a una página relevante
            # Podrías redirigir al detalle del insumo o a la lista donde el usuario pueda ver el error
            # o incluso a la página desde donde vino.
            # Para simplificar, redirigimos a donde iría si la eliminación fuera exitosa (ej. la categoría o depósito)
            # para que vea el mensaje de error allí.
            if hasattr(self.object, "categoria") and self.object.categoria:
                return redirect(
                    reverse_lazy(
                        "App_LUMINOVA:categoria_i_detail",
                        kwargs={"pk": self.object.categoria.pk},
                    )
                )
            return redirect(reverse_lazy("App_LUMINOVA:deposito_view"))

