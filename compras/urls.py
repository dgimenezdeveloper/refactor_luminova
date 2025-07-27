from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_compras, name='lista_compras'),
    path('nuevo/', views.crear_compra, name='crear_compra'),
]
