"""
Django settings for Proyecto_LUMINOVA project.

Configuración con django-tenants para multi-tenancy y JWT para autenticación.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/
"""

import os
from pathlib import Path
from datetime import timedelta

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure--y9eu$96r+*$ql($i(o+yhe8so&7p&h&j#)34o3zs$x*u^ijgq')
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,.localhost').split(',')


# =============================================================================
# DJANGO-TENANTS CONFIGURATION
# =============================================================================

# Apps compartidas entre todos los tenants (schema public)
SHARED_APPS = [
    'django_tenants',  # Debe ir primero
    'App_LUMINOVA',  # App con el modelo Tenant (Empresa)
    
    # Django core apps compartidas
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third-party apps compartidas
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'drf_spectacular',
    'django_bootstrap5',
]

# Apps específicas de cada tenant (se crean en cada schema)
TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    
    # La app principal con los modelos de negocio
    'App_LUMINOVA',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Modelo de Tenant y Domain
TENANT_MODEL = "App_LUMINOVA.Empresa"
TENANT_DOMAIN_MODEL = "App_LUMINOVA.Domain"

# Schema público por defecto
PUBLIC_SCHEMA_NAME = 'public'


# =============================================================================
# MIDDLEWARE - TenantMiddleware debe ir primero
# =============================================================================

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # DEBE SER PRIMERO
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'App_LUMINOVA.middleware.PasswordChangeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# =============================================================================
# DATABASE - PostgreSQL con django-tenants backend
# =============================================================================

# Cargar variables de entorno
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_host = os.environ.get("DB_HOST")
db_port = os.environ.get("DB_PORT")

# Verificar si usar django-tenants
USE_TENANTS = os.environ.get("USE_TENANTS", "True") == "True"

if db_name and db_user and db_password and db_host and db_port:
    DATABASES = {
        "default": {
            # Usar el backend de django-tenants para PostgreSQL
            "ENGINE": "django_tenants.postgresql_backend" if USE_TENANTS else "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }
else:
    # Fallback a SQLite (sin multi-tenancy)
    USE_TENANTS = False
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Router para django-tenants
if USE_TENANTS:
    DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']


# =============================================================================
# URL CONFIGURATION
# =============================================================================

ROOT_URLCONF = "Proyecto_LUMINOVA.urls"


# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "App_LUMINOVA", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",  # Requerido por django-tenants
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "App_LUMINOVA.context_processors.notificaciones_context",
                "App_LUMINOVA.context_processors.puede_ver_deposito_sidebar",
                "App_LUMINOVA.context_processors.empresa_actual_context",
            ],
        },
    },
]

WSGI_APPLICATION = "Proyecto_LUMINOVA.wsgi.application"


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "es-AR"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "App_LUMINOVA" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media/")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =============================================================================
# AUTHENTICATION
# =============================================================================

LOGIN_URL = "App_LUMINOVA:login"
LOGIN_REDIRECT_URL = "App_LUMINOVA:dashboard"
LOGOUT_REDIRECT_URL = "App_LUMINOVA:login"

DEFAULT_PASSWORD_FOR_NEW_USERS = "luminova.2025"


# =============================================================================
# DJANGO REST FRAMEWORK + JWT
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT primero
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Configuración de Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'JTI_CLAIM': 'jti',
}


# =============================================================================
# DRF-SPECTACULAR (API Documentation)
# =============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'LUMINOVA API',
    'DESCRIPTION': 'API REST para Sistema ERP Multi-depósito LUMINOVA con multi-tenancy',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}


# =============================================================================
# LOGGING (Debug)
# =============================================================================

if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django_tenants': {
                'handlers': ['console'],
                'level': 'INFO',
            },
        },
    }
