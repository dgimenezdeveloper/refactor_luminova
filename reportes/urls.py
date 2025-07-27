from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_reportes, name='lista_reportes'),
    path('nuevo/', views.crear_reporte, name='crear_reporte'),
]
