from django.urls import path
from .views import deposito_stock_view

app_name = "depositos"

urlpatterns = [
    path("stock/<int:deposito_id>/", deposito_stock_view, name="stock_por_deposito"),
]
