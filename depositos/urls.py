from django.urls import path
from . import views
urlpatterns = [
    path('selector/', views.deposito_selector_view, name='deposito_selector'),
    path('enviar-insumos-op/<int:op_id>/', views.deposito_enviar_insumos_op_view, name='deposito_enviar_insumos_op'),
    path('solicitudes-insumos/', views.deposito_solicitudes_insumos_view, name='deposito_solicitudes_insumos'),
    path('deposito/', views.deposito_view, name='deposito_view'),
    path('recepcion-pedidos/', views.recepcion_pedidos_view, name='deposito_recepcion_pedidos'),
    path('recibir-pedido-oc/<int:oc_id>/', views.recibir_pedido_oc_view, name='deposito_recibir_pedido_oc'),
path("stock/<int:deposito_id>/", views.deposito_stock_view, name="stock_por_deposito"),
]

app_name = "depositos"

urlpatterns = [
path("stock/<int:deposito_id>/", views.deposito_stock_view, name="stock_por_deposito"),
]
