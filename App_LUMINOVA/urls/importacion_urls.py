# App_LUMINOVA/urls/importacion_urls.py
from django.urls import path
from App_LUMINOVA import views_importacion

urlpatterns = [
    # Página principal de importación
    path('', views_importacion.importacion_principal, name='importacion_principal'),
    
    # Descargar plantillas
    path('plantilla/insumos/', views_importacion.descargar_plantilla_insumos, name='descargar_plantilla_insumos'),
    path('plantilla/productos/', views_importacion.descargar_plantilla_productos, name='descargar_plantilla_productos'),
    path('plantilla/clientes/', views_importacion.descargar_plantilla_clientes, name='descargar_plantilla_clientes'),
    path('plantilla/proveedores/', views_importacion.descargar_plantilla_proveedores, name='descargar_plantilla_proveedores'),
    
    # Importar datos
    path('importar/insumos/', views_importacion.importar_insumos, name='importar_insumos'),
    path('importar/productos/', views_importacion.importar_productos, name='importar_productos'),
    path('importar/clientes/', views_importacion.importar_clientes, name='importar_clientes'),
    path('importar/proveedores/', views_importacion.importar_proveedores, name='importar_proveedores'),
    
    # Historial de importaciones
    path('historial/', views_importacion.historial_importaciones, name='historial_importaciones'),
]
