from django.urls import path, include
from . import admin_urls, ventas_urls, compras_urls, produccion_urls, deposito_urls, base_urls, control_calidad_urls, empresas_urls, importacion_urls

app_name = 'App_LUMINOVA'

urlpatterns = [
    # Delega las rutas a cada submódulo usando los módulos importados
    # en lugar de strings.
    path('admin/', include(admin_urls)),
    path('ventas/', include(ventas_urls)),
    path('compras/', include(compras_urls)),
    path('produccion/', include(produccion_urls)),
    path('deposito/', include(deposito_urls)),
    path('control_calidad/', include(control_calidad_urls)),
    path('empresas/', include(empresas_urls)),  # Nuevas URLs de empresas
    path('importacion/', include(importacion_urls)),  # URLs de importación masiva
    
    path('', include(base_urls)),
]