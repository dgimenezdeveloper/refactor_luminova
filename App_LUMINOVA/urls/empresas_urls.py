# App_LUMINOVA/urls/empresas_urls.py
from django.urls import path
from App_LUMINOVA import views_empresas

urlpatterns = [
    # Cambiar empresa actual
    path('cambiar/<int:empresa_id>/', views_empresas.cambiar_empresa, name='cambiar_empresa'),
    
    # Administración de empresas (solo superusuarios)
    path('admin/', views_empresas.admin_empresas, name='admin_empresas'),
    path('admin/crear/', views_empresas.admin_crear_empresa, name='admin_crear_empresa'),
    path('admin/editar/<int:empresa_id>/', views_empresas.admin_editar_empresa, name='admin_editar_empresa'),
    path('admin/toggle/<int:empresa_id>/', views_empresas.admin_toggle_empresa, name='admin_toggle_empresa'),
    path('admin/detalle/<int:empresa_id>/', views_empresas.admin_detalle_empresa, name='admin_detalle_empresa'),
]
