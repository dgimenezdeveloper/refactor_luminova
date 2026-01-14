# Migración de SQLite a PostgreSQL - LUMINOVA ERP

**Fecha de implementación**: 14 de enero de 2026  
**Estado**: ✅ Completado  
**Versión de PostgreSQL**: 16.x  
**Versión de Django**: 5.2.1

---

## 📋 Resumen Ejecutivo

Este documento detalla el proceso de migración de la base de datos LUMINOVA desde SQLite a PostgreSQL, un paso fundamental en la transformación hacia un sistema SaaS multi-empresarial escalable.

### ¿Por qué migrar a PostgreSQL?

1. **Escalabilidad**: SQLite no soporta conexiones concurrentes múltiples
2. **Multi-tenancy**: `django-tenants` requiere PostgreSQL (usa esquemas)
3. **Performance**: Los 43 índices creados en Fase 3 funcionan mejor en PostgreSQL
4. **Features avanzadas**: Soporte para JSON, arrays, búsqueda full-text, particionado
5. **Producción**: SQLite no es recomendado para entornos de producción

---

## 🔧 Cambios Realizados

### 1. Dependencias Añadidas

```txt
# requirements.txt
psycopg2-binary==2.9.11  # Driver PostgreSQL para Python
```

### 2. Configuración de Variables de Entorno

Se creó/actualizó el archivo `.env` con soporte dual SQLite/PostgreSQL:

```env
# DATABASE - PostgreSQL (Producción)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=luminova_db
DB_USER=luminova_user
DB_PASSWORD=luminova_password_2026
DB_HOST=localhost
DB_PORT=5432
```

### 3. Script de Migración

Se creó `scripts/migrate_to_postgresql.py` que automatiza:
- Verificación de prerequisitos
- Exportación de datos desde SQLite
- Prueba de conexión a PostgreSQL
- Ejecución de migraciones
- Carga de datos
- Verificación de integridad

---

## 📝 Proceso de Migración Paso a Paso

### Paso 1: Instalar PostgreSQL (si no está instalado)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Verificar instalación
psql --version
```

### Paso 2: Crear Base de Datos y Usuario

```bash
# Acceder como usuario postgres
sudo -u postgres psql

# Dentro de PostgreSQL:
CREATE DATABASE luminova_db;
CREATE USER luminova_user WITH PASSWORD 'luminova_password_2026';
ALTER ROLE luminova_user SET client_encoding TO 'utf8';
ALTER ROLE luminova_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE luminova_user SET timezone TO 'America/Argentina/Buenos_Aires';
GRANT ALL PRIVILEGES ON DATABASE luminova_db TO luminova_user;

-- Para PostgreSQL 15+:
\c luminova_db
GRANT ALL ON SCHEMA public TO luminova_user;

\q
```

### Paso 3: Configurar Variables de Entorno

Editar el archivo `.env` en la raíz del proyecto:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=luminova_db
DB_USER=luminova_user
DB_PASSWORD=tu_contraseña_segura
DB_HOST=localhost
DB_PORT=5432
```

### Paso 4: Exportar Datos de SQLite

```bash
# Primero, comentar temporalmente las variables de PostgreSQL en .env
# Luego ejecutar:
source env/bin/activate
python manage.py dumpdata --exclude contenttypes --exclude auth.permission --indent 2 --output backups/luminova_data.json
```

### Paso 5: Aplicar Migraciones en PostgreSQL

```bash
# Descomentar las variables de PostgreSQL en .env
source env/bin/activate
python manage.py migrate
```

### Paso 6: Cargar Datos

```bash
# Si hay signals que interfieren, desconectarlos temporalmente:
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
import django
django.setup()

from django.db.models.signals import post_save
from App_LUMINOVA.signals import sync_stock_insumo
from App_LUMINOVA.models import Insumo

post_save.disconnect(sync_stock_insumo, sender=Insumo)

from django.core.management import call_command
call_command('loaddata', 'backups/luminova_data.json')
"
```

### Paso 7: Verificar Migración

```bash
python manage.py runserver
# Acceder a http://127.0.0.1:8000 y verificar funcionalidad
```

---

## 📊 Resultados de la Migración

### Datos Migrados

| Modelo | Registros |
|--------|-----------|
| Usuarios | 6 |
| Empresas | 2 |
| Depósitos | 6 |
| Productos | 11 |
| Insumos | 67 |
| Clientes | 3 |
| Proveedores | 9 |
| Órdenes de Venta | 63 |
| Órdenes de Compra | 22 |
| Órdenes de Producción | 73 |
| **TOTAL** | **1823 objetos** |

### Configuración Final

```python
# settings.py - Configuración dinámica de base de datos
db_engine = os.environ.get("DB_ENGINE")
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_host = os.environ.get("DB_HOST")
db_port = os.environ.get("DB_PORT")

if db_engine and db_name and db_user and db_password and db_host and db_port:
    DATABASES = {
        "default": {
            "ENGINE": db_engine,
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
        }
    }
else:
    # Fallback a SQLite para desarrollo
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
```

---

## 🔒 Consideraciones de Seguridad

1. **No versionar `.env`**: Ya incluido en `.gitignore`
2. **Usar contraseñas fuertes**: En producción, usar contraseñas generadas
3. **SSL en producción**: Configurar `DB_SSL_MODE=require` para conexiones seguras
4. **Backups automáticos**: Configurar `pg_dump` para backups periódicos

---

## 🔄 Cómo Alternar entre SQLite y PostgreSQL

### Usar SQLite (Desarrollo)
```bash
# Comentar o eliminar estas líneas en .env:
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=luminova_db
# ...
```

### Usar PostgreSQL (Producción/Staging)
```bash
# Descomentar estas líneas en .env:
DB_ENGINE=django.db.backends.postgresql
DB_NAME=luminova_db
DB_USER=luminova_user
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
```

---

## ⚠️ Problemas Conocidos y Soluciones

### 1. Error de cursor durante dumpdata

**Problema**: `cursor "_django_curs_XXX_sync_1" does not exist`

**Solución**: Asegurarse de que las variables de PostgreSQL NO estén activas durante la exportación de SQLite.

### 2. Signals interfieren durante loaddata

**Problema**: `Deposito matching query does not exist`

**Solución**: Desconectar temporalmente los signals antes de cargar datos (ver Paso 6).

### 3. IntegrityError al cargar datos

**Problema**: Conflictos de integridad referencial

**Solución**: Cargar datos excluyendo `contenttypes` y `auth.permission`.

---

## 📁 Archivos Creados/Modificados

| Archivo | Descripción |
|---------|-------------|
| `.env` | Variables de entorno con configuración PostgreSQL |
| `.env.example` | Plantilla de ejemplo para nuevos desarrolladores |
| `requirements.txt` | Añadido `psycopg2-binary==2.9.11` |
| `scripts/migrate_to_postgresql.py` | Script de migración automatizada |
| `backups/luminova_data_sqlite.json` | Backup de datos SQLite (570KB) |

---

## 🚀 Próximos Pasos

1. **django-tenants**: Implementar multi-tenancy real con esquemas PostgreSQL
2. **Autenticación JWT**: Agregar `djangorestframework-simplejwt`
3. **Redis**: Configurar cache distribuido para sesiones y datos frecuentes
4. **Backups automatizados**: Configurar `pg_dump` en cron

---

## 📚 Referencias

- [Django Database Backends](https://docs.djangoproject.com/en/5.0/ref/databases/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/current/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [django-tenants](https://django-tenants.readthedocs.io/)
