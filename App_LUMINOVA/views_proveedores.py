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
from .empresa_filters import filter_proveedores_por_empresa

logger = logging.getLogger(__name__)


class ProveedorListView(ListView):
    model = Proveedor
    template_name = "ventas/proveedores/proveedor_list.html"
    context_object_name = "proveedores"
    
    def get_queryset(self):
        # FILTRO POR EMPRESA: Solo proveedores con OCs a la empresa
        return filter_proveedores_por_empresa(self.request)


class ProveedorDetailView(DetailView):
    model = Proveedor
    template_name = "ventas/proveedores/proveedor_detail.html"
    context_object_name = "proveedor"


class ProveedorUpdateView(UpdateView):
    model = Proveedor
    template_name = "ventas/proveedores/proveedor_editar.html"
    form_class = ProveedorForm
    context_object_name = "proveedor"
    success_url = reverse_lazy("App_LUMINOVA:proveedor_list")


class ProveedorDeleteView(DeleteView):
    model = Proveedor
    template_name = "ventas/proveedores/proveedor_confirm_delete.html"
    context_object_name = "proveedor"
    success_url = reverse_lazy("App_LUMINOVA:proveedor_list")
