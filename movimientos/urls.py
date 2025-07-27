from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_movimientos, name='lista_movimientos'),
    path('nuevo/', views.crear_movimiento, name='crear_movimiento'),
]
