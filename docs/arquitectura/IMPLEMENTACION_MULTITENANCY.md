# Implementación de Multi-Tenancy con Django-Tenants

**Fecha de Implementación**: 14 de enero de 2026  
**Estado**: ✅ Completado  
**Dependencias**: django-tenants==3.9.0, PostgreSQL 16.x

---

## 📋 Resumen

Se implementó multi-tenancy real utilizando **django-tenants**, que proporciona aislamiento de datos a nivel de esquemas PostgreSQL. Cada empresa (tenant) tiene su propio schema en la base de datos, garantizando seguridad y aislamiento total de los datos.

---

## 🏗️ Arquitectura Implementada

### Modelo de Tenant

```python
# App_LUMINOVA/models.py
from django_tenants.models import TenantMixin, DomainMixin

class Empresa(TenantMixin):
    """
    Modelo de Tenant para multi-tenancy con django-tenants.
    Cada Empresa tiene su propio schema en PostgreSQL.
    """
    nombre = models.CharField(max_length=150, unique=True)
    razon_social = models.CharField(max_length=255, blank=True)
    cuit = models.CharField(max_length=20, blank=True)
    # ... otros campos
    
    auto_create_schema = True  # Crear schema automáticamente
    auto_drop_schema = True   # Eliminar schema al borrar empresa

class Domain(DomainMixin):
    """
    Modelo de Domain para mapear dominios/subdominios a tenants.
    """
    pass
```

### Configuración en settings.py

```python
# DJANGO-TENANTS CONFIGURATION
SHARED_APPS = [
    'django_tenants',  # Debe ir primero
    'App_LUMINOVA',    # App con el modelo Tenant
    'django.contrib.contenttypes',
    'django.contrib.auth',
    # ... apps compartidas
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'App_LUMINOVA',  # Datos específicos por tenant
]

TENANT_MODEL = "App_LUMINOVA.Empresa"
TENANT_DOMAIN_MODEL = "App_LUMINOVA.Domain"
PUBLIC_SCHEMA_NAME = 'public'

# Middleware
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # PRIMERO
    # ... otros middlewares
]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        # ... configuración PostgreSQL
    }
}

DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']
```

---

## 🌐 Esquema de Dominios

### Estructura de URLs por Tenant

| Dominio | Tenant | Schema |
|---------|--------|--------|
| `localhost` | Luminova ERP | `public` |
| `sabores_del_valle.localhost` | Sabores del Valle | `sabores_del_valle` |
| `{schema}.localhost` | Nuevo Tenant | `{schema}` |

### Cómo Funciona

1. El middleware `TenantMainMiddleware` intercepta cada request
2. Lee el dominio de la petición HTTP
3. Busca el Domain correspondiente en la BD
4. Establece el search_path de PostgreSQL al schema del tenant
5. Todas las queries se ejecutan en el schema correcto

---

## 📦 Migraciones

### Comandos Importantes

```bash
# Migrar solo el schema público (compartido)
python manage.py migrate_schemas --shared

# Migrar todos los tenants
python manage.py migrate_schemas

# Migrar un tenant específico
python manage.py migrate_schemas --tenant=sabores_del_valle
```

### Crear Nuevo Tenant

```python
from App_LUMINOVA.models import Empresa, Domain

# Crear empresa/tenant
empresa = Empresa.objects.create(
    schema_name='nuevo_cliente',
    nombre='Nuevo Cliente S.A.',
    razon_social='Nuevo Cliente S.A.',
    activa=True
)

# Crear dominio
Domain.objects.create(
    domain='nuevo_cliente.localhost',
    tenant=empresa,
    is_primary=True
)
```

---

## 🔒 Seguridad

### Aislamiento de Datos

- **Nivel de base de datos**: Cada tenant tiene su propio schema PostgreSQL
- **Sin filtrado en código**: No hay necesidad de filtrar por empresa en cada query
- **Imposible acceder a datos de otros tenants**: PostgreSQL garantiza el aislamiento

### Schema Context

```python
from django_tenants.utils import schema_context

# Ejecutar código en un schema específico
with schema_context('sabores_del_valle'):
    productos = ProductoTerminado.objects.all()  # Solo del tenant
```

---

## 📊 Estado Actual

### Tenants Configurados

| ID | Nombre | Schema | Dominio |
|----|--------|--------|---------|
| 1 | Luminova ERP | `public` | `localhost` |
| 2 | Sabores del Valle | `sabores_del_valle` | `sabores_del_valle.localhost` |

### Próximos Pasos

1. **Crear panel de administración** para gestión de tenants
2. **Implementar onboarding** automatizado para nuevos clientes
3. **Configurar subdominos reales** en producción
4. **Agregar planes de suscripción** por tenant

---

## 🧪 Testing

```python
# Probar que django-tenants funciona
python manage.py shell
>>> from App_LUMINOVA.models import Empresa, Domain
>>> Empresa.objects.all()
<QuerySet [<Empresa: Luminova ERP>, <Empresa: Sabores del Valle>]>

>>> Domain.objects.all()  
<QuerySet [<Domain: localhost>, <Domain: sabores_del_valle.localhost>]>
```

---

## 📚 Referencias

- [Django-Tenants Documentation](https://django-tenants.readthedocs.io/)
- [PostgreSQL Schemas](https://www.postgresql.org/docs/current/ddl-schemas.html)
