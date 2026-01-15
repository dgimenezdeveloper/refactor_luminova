# Arquitectura de LUMINOVA ERP - Fase 2: Modularización

## 📋 Resumen

La Fase 2 del proyecto LUMINOVA ERP introduce una arquitectura modular tanto en el backend (Django) como en el frontend (React), siguiendo patrones de diseño empresariales para mejorar la mantenibilidad, escalabilidad y testabilidad del sistema.

## 🏗️ Estructura del Backend

### Apps Django por Dominio

```
apps/
├── core/                    # Funcionalidades centrales compartidas
│   ├── base.py              # Clases base: BaseRepository, BaseService, ServiceResult
│   └── apps.py              # Configuración de la app
│
├── inventory/               # Gestión de inventario
│   ├── repositories/        # Capa de acceso a datos
│   │   └── inventory_repository.py
│   ├── services/            # Lógica de negocio
│   │   └── inventory_service.py
│   └── apps.py
│
├── sales/                   # Gestión de ventas
│   ├── repositories/
│   │   └── sales_repository.py
│   ├── services/
│   │   └── sales_service.py
│   └── apps.py
│
├── production/              # Gestión de producción
│   ├── repositories/
│   │   └── production_repository.py
│   ├── services/
│   │   └── production_service.py
│   └── apps.py
│
├── purchasing/              # Gestión de compras
│   ├── repositories/
│   │   └── purchasing_repository.py
│   ├── services/
│   │   └── purchasing_service.py
│   └── apps.py
│
└── notifications/           # Sistema de notificaciones
    └── apps.py
```

### Patrón Repository

El patrón Repository abstrae la capa de acceso a datos, proporcionando una interfaz limpia para operaciones CRUD y queries complejas.

```python
from apps.core.base import BaseRepository
from App_LUMINOVA.models import ProductoTerminado

class ProductoRepository(BaseRepository[ProductoTerminado]):
    """
    Repositorio para operaciones de datos de productos.
    """
    model = ProductoTerminado
    
    def get_productos_stock_bajo(self, empresa: Empresa) -> QuerySet:
        """Obtiene productos con stock por debajo del mínimo."""
        return self.get_queryset(empresa).filter(
            stock__lt=F('stock_minimo')
        )
```

### Patrón Service Layer

El Service Layer contiene la lógica de negocio y orquesta las operaciones entre repositorios.

```python
from apps.core.base import BaseService, ServiceResult

class InventoryService(BaseService):
    """
    Servicio de inventario - Lógica de negocio.
    """
    def __init__(self, empresa):
        super().__init__(empresa)
        self.producto_repo = ProductoRepository()
        
    def ajustar_stock_producto(
        self, producto_id: int, cantidad: int, motivo: str
    ) -> ServiceResult:
        """
        Ajusta el stock de un producto (entrada/salida).
        """
        try:
            producto = self.producto_repo.get_by_id(producto_id, self.empresa)
            if cantidad < 0 and producto.stock + cantidad < 0:
                return ServiceResult.error("Stock insuficiente")
            
            producto.stock += cantidad
            producto.save()
            
            return ServiceResult.success(
                data=producto,
                message=f"Stock ajustado: {cantidad:+d} unidades"
            )
        except Exception as e:
            return ServiceResult.error(str(e))
```

### ServiceResult

Patrón para estandarizar respuestas de servicios:

```python
@dataclass
class ServiceResult:
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    
    @classmethod
    def ok(cls, data=None, message=None):
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error(cls, message, errors=None):
        return cls(success=False, message=message, errors=errors or [message])
```

## 🎨 Estructura del Frontend

### Organización de Directorios

```
frontend/src/
├── components/              # Componentes React reutilizables
│   ├── common/              # Componentes genéricos
│   │   ├── DataTable.tsx    # Tabla de datos con paginación
│   │   ├── GlobalSnackbar.tsx
│   │   ├── LoadingSpinner.tsx
│   │   ├── PageHeader.tsx
│   │   └── StatCard.tsx
│   └── layout/              # Componentes de layout
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── MainLayout.tsx
│
├── hooks/                   # Custom hooks
│   └── index.ts             # useAppDispatch, useAuth, useNotify, etc.
│
├── pages/                   # Páginas/Vistas
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── inventory/           # Páginas de inventario
│   │   ├── ProductosListPage.tsx
│   │   └── InsumosListPage.tsx
│   └── sales/               # Páginas de ventas
│       └── OrdenesVentaListPage.tsx
│
├── store/                   # Estado global (Redux Toolkit)
│   ├── index.ts             # Configuración del store
│   ├── api/                 # RTK Query para API
│   │   └── luminovaApi.ts
│   └── slices/              # Slices de estado
│       ├── authSlice.ts
│       └── uiSlice.ts
│
├── types/                   # Definiciones TypeScript
│   └── index.ts             # Interfaces y tipos
│
├── App.tsx                  # Componente principal
└── theme.ts                 # Configuración Material-UI
```

### Stack Tecnológico

- **React 18** con TypeScript
- **Vite** para bundling y desarrollo
- **Material-UI (MUI)** para componentes UI
- **Redux Toolkit** con RTK Query para estado y API
- **React Router** para navegación

### RTK Query

Gestión centralizada de llamadas API con caché automático:

```typescript
export const luminovaApi = createApi({
  reducerPath: 'luminovaApi',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['Producto', 'Insumo', 'OrdenVenta', ...],
  endpoints: (builder) => ({
    getProductos: builder.query<PaginatedResponse<Producto>, QueryParams>({
      query: ({ page, search }) => `/productos/?page=${page}&search=${search}`,
      providesTags: ['Producto'],
    }),
    // ...más endpoints
  }),
});

// Hooks generados automáticamente
export const { useGetProductosQuery, useCreateProductoMutation } = luminovaApi;
```

## 🔌 Integración Backend-Frontend

### Proxy de Desarrollo

Vite proxy configurado en `vite.config.ts`:

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
    '/media': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  },
}
```

### Autenticación JWT

- Login genera tokens JWT (access + refresh)
- Token refresh automático en caso de expiración
- Logout limpia tokens del localStorage

## 📊 Diagrama de Flujo de Datos

```
┌──────────────┐    HTTP/JSON    ┌──────────────┐
│   Frontend   │ ◄──────────────► │   Backend    │
│   (React)    │                  │   (Django)   │
└──────────────┘                  └──────────────┘
       │                                 │
       ▼                                 ▼
┌──────────────┐                  ┌──────────────┐
│ Redux Store  │                  │   Services   │
│ (RTK Query)  │                  │    Layer     │
└──────────────┘                  └──────────────┘
       │                                 │
       ▼                                 ▼
┌──────────────┐                  ┌──────────────┐
│  Components  │                  │ Repositories │
│    (UI)      │                  │    Layer     │
└──────────────┘                  └──────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │   Database   │
                                 │ (PostgreSQL) │
                                 └──────────────┘
```

## 🚀 Comandos de Desarrollo

### Backend (Django)
```bash
# Activar entorno virtual
source env/bin/activate

# Iniciar servidor
python manage.py runserver

# Migraciones
python manage.py makemigrations
python manage.py migrate
```

### Frontend (React)
```bash
cd frontend

# Instalar dependencias
npm install

# Desarrollo
npm run dev

# Build producción
npm run build

# Verificar tipos
npx tsc --noEmit
```

## 📝 Próximos Pasos (Pendientes)

1. **APIs REST completas** - Exponer servicios como endpoints REST
2. **Formularios de CRUD** - Crear/Editar para todas las entidades
3. **Tests unitarios** - Cobertura de servicios y componentes
4. **Documentación API** - Swagger/OpenAPI
5. **CI/CD** - Pipeline de despliegue automatizado

## 📚 Referencias

- [Django REST Framework](https://www.django-rest-framework.org/)
- [Redux Toolkit](https://redux-toolkit.js.org/)
- [RTK Query](https://redux-toolkit.js.org/rtk-query/overview)
- [Material-UI](https://mui.com/)
- [Vite](https://vitejs.dev/)
