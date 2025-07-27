from django.urls import path
from . import views

urlpatterns = [
    path('produccion/', views.produccion_lista_op_view, name='produccion_lista_op'),
    path('planificacion/', views.planificacion_produccion_view, name='planificacion_produccion'),
    path('produccion/<int:op_id>/solicitar-insumos/', views.solicitar_insumos_op_view, name='solicitar_insumos_op'),
    path('produccion/<int:op_id>/', views.produccion_detalle_op_view, name='produccion_detalle_op'),
    path('reportes/', views.reportes_produccion_view, name='reportes_produccion'),
    path('reportes/crear/<int:op_id>/', views.crear_reporte_produccion_view, name='crear_reporte_produccion'),
]
