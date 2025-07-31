from django.urls import path
from App_LUMINOVA.views_transferencias import historial_transferencias_view

urlpatterns = [
    path('historial/', historial_transferencias_view, name='historial_transferencias'),
]
