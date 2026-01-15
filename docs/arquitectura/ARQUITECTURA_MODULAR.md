# Arquitectura Modular de LUMINOVA

## Resumen

LUMINOVA ha sido refactorizado a una arquitectura modular que separa responsabilidades en diferentes apps de Django, manteniendo compatibilidad con el código existente mediante un patrón de re-exportación.

## Estructura de Apps

```
TP_LUMINOVA/
├── App_LUMINOVA/              # App principal (mantiene todos los modelos)
│   ├── models.py              # Modelos originales - FUENTE DE VERDAD
│   ├── views_*.py             # Vistas existentes
│   ├── forms.py               # Formularios
│   └── ...
│
├── apps/                      # Nuevas apps modulares
│   ├── core/                  # Infraestructura base
│   │   ├── models.py          # Re-exporta modelos de tenant/base
│   │   ├── base.py            # BaseRepository, clases base
│   │   └── services/          # Servicios de core
│   │
│   ├── inventory/             # Gestión de inventario
│   │   ├── models.py          # Re-exporta ProductoTerminado, Insumo, Stock, etc.
│   │   ├── repositories/      # Repositorios de inventario
│   │   └── services/          # Servicios de inventario
│   │
│   ├── sales/                 # Gestión de ventas
│   │   ├── models.py          # Re-exporta Cliente, OrdenVenta, Factura, etc.
│   │   ├── repositories/      # Repositorios de ventas
│   │   └── services/          # Servicios de ventas
│   │
│   ├── production/            # Gestión de producción
│   │   ├── models.py          # Re-exporta OrdenProduccion, Reportes, etc.
│   │   ├── repositories/      # Repositorios de producción
│   │   └── services/          # Servicios de producción
│   │
│   ├── purchasing/            # Gestión de compras
│   │   ├── models.py          # Re-exporta Proveedor, Orden (OC), etc.
│   │   ├── repositories/      # Repositorios de compras
│   │   └── services/          # Servicios de compras
│   │
│   └── notifications/         # Sistema de notificaciones
│       ├── models.py          # Re-exporta NotificacionSistema
│       └── services/          # Servicios de notificaciones
│
└── Proyecto_LUMINOVA/
    └── settings.py            # Configuración con nuevas apps
```

## Patrón de Re-exportación

Los modelos se mantienen en `App_LUMINOVA/models.py` como **fuente única de verdad**. Las nuevas apps simplemente re-exportan estos modelos para facilitar una migración gradual.

### Ejemplo

```python
# apps/inventory/models.py
from App_LUMINOVA.models import (
    ProductoTerminado,
    Insumo,
    StockInsumo,
    # ...
)

__all__ = ['ProductoTerminado', 'Insumo', 'StockInsumo', ...]
```

### Ventajas

1. **Sin cambios de base de datos**: Las tablas permanecen en el mismo lugar
2. **Compatibilidad total**: Código existente sigue funcionando
3. **Migración gradual**: Nuevas features pueden usar nuevos imports
4. **Cero downtime**: No requiere migraciones complejas

## Capas de la Arquitectura

### 1. Capa de Modelos (Data Layer)
- **App_LUMINOVA/models.py**: Definición de todos los modelos
- **apps/*/models.py**: Re-exportación por dominio

### 2. Capa de Repositorios (Data Access Layer)
Ubicación: `apps/*/repositories/`

```python
from apps.inventory.repositories import ProductoRepository, InsumoRepository
from apps.sales.repositories import ClienteRepository, OrdenVentaRepository
```

Los repositorios proporcionan:
- Abstracción sobre el ORM de Django
- Queries optimizadas por dominio
- Filtrado automático por empresa (multi-tenancy)

### 3. Capa de Servicios (Business Logic Layer)
Ubicación: `apps/*/services/`

Los servicios encapsulan:
- Lógica de negocio compleja
- Transacciones entre múltiples modelos
- Validaciones de negocio

### 4. Capa de Vistas (Presentation Layer)
- **Existente**: `App_LUMINOVA/views_*.py`
- **API REST**: `App_LUMINOVA/api/`

## Mapeo de Modelos por App

### apps.core
| Modelo | Descripción |
|--------|-------------|
| Empresa | Tenant principal (multi-tenancy) |
| Domain | Dominio asociado al tenant |
| Deposito | Almacén/depósito físico |
| UsuarioDeposito | Permisos usuario-depósito |
| RolEmpresa | Roles personalizados por empresa |
| PerfilUsuario | Perfil extendido del usuario |
| AuditoriaAcceso | Log de accesos |
| HistorialImportacion | Historial de importaciones |
| EmpresaScopedModel | Base abstracta para aislamiento |

### apps.inventory
| Modelo | Descripción |
|--------|-------------|
| ProductoTerminado | Producto final para venta |
| Insumo | Materia prima/componente |
| CategoriaProductoTerminado | Categoría de productos |
| CategoriaInsumo | Categoría de insumos |
| ComponenteProducto | BOM (Bill of Materials) |
| StockInsumo | Stock por depósito de insumos |
| StockProductoTerminado | Stock por depósito de productos |
| MovimientoStock | Histórico de movimientos |
| Fabricante | Fabricantes de insumos |

### apps.sales
| Modelo | Descripción |
|--------|-------------|
| Cliente | Clientes de la empresa |
| OrdenVenta | Órdenes de venta |
| ItemOrdenVenta | Items de OV |
| Factura | Facturas emitidas |
| HistorialOV | Histórico de cambios en OV |

### apps.production
| Modelo | Descripción |
|--------|-------------|
| OrdenProduccion | Órdenes de producción |
| EstadoOrden | Estados de OP |
| SectorAsignado | Sectores de producción |
| Reportes | Reportes de incidencias |
| LoteProductoTerminado | Lotes producidos |

### apps.purchasing
| Modelo | Descripción |
|--------|-------------|
| Proveedor | Proveedores de insumos |
| OfertaProveedor | Ofertas de precios |
| Orden | Órdenes de compra |

### apps.notifications
| Modelo | Descripción |
|--------|-------------|
| NotificacionSistema | Notificaciones internas |

## Uso Recomendado

### Para código nuevo
```python
# Usar imports desde las nuevas apps
from apps.inventory.models import ProductoTerminado
from apps.sales.models import Cliente
from apps.core.models import Empresa

# Usar repositorios para acceso a datos
from apps.inventory.repositories import ProductoRepository

class MiVista:
    def get_productos(self, request):
        repo = ProductoRepository(empresa=request.user.perfil.empresa)
        return repo.get_all()
```

### Para código existente (compatibilidad)
```python
# Sigue funcionando sin cambios
from App_LUMINOVA.models import ProductoTerminado, Cliente, Empresa
```

## Multi-tenancy

El sistema usa `django-tenants` para aislamiento de datos:

1. **Empresa** es el modelo de tenant
2. **EmpresaScopedModel** filtra automáticamente por empresa
3. Los repositorios reciben `empresa` en el constructor
4. TENANT_MODEL y TENANT_DOMAIN_MODEL están en App_LUMINOVA

## Próximos Pasos (Fase 3)

1. [ ] Migrar vistas existentes para usar repositorios
2. [ ] Implementar servicios de negocio
3. [ ] Añadir tests unitarios por app
4. [ ] Crear APIs REST en las nuevas apps
5. [ ] Documentar APIs con OpenAPI/Swagger

## Notas Técnicas

- **Django version**: 5.2.1
- **Python version**: 3.12
- **Multi-tenancy**: django-tenants
- **API**: Django REST Framework + drf-spectacular
