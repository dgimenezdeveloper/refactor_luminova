from django.urls import path
from . import views

urlpatterns = [
    path('compras/', views.compras_lista_oc_view, name='compras_lista_oc_view'),
    path('compras/desglose/', views.compras_desglose_view, name='compras_desglose_view'),
    path('compras/seguimiento/', views.compras_seguimiento_view, name='compras_seguimiento_view'),
    path('compras/tracking/<int:oc_id>/', views.compras_tracking_pedido_view, name='compras_tracking_pedido_view'),
    path('compras/desglose/<str:numero_orden_desglose>/', views.compras_desglose_detalle_oc_view, name='compras_desglose_detalle_oc_view'),
    path('compras/seleccionar-proveedor/<int:insumo_id>/', views.compras_seleccionar_proveedor_para_insumo_view, name='compras_seleccionar_proveedor_para_insumo'),
    path('compras/detalle/<int:oc_id>/', views.compras_detalle_oc_view, name='compras_detalle_oc_view'),
    path('compras/crear/', views.compras_crear_oc_view, name='compras_crear_oc_view'),
]
