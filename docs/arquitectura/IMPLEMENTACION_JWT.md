# Implementación de Autenticación JWT

**Fecha de Implementación**: 14 de enero de 2026  
**Estado**: ✅ Completado  
**Dependencias**: djangorestframework-simplejwt==5.3.1, PyJWT==2.10.1

---

## 📋 Resumen

Se implementó autenticación JWT (JSON Web Tokens) para la API REST utilizando **djangorestframework-simplejwt**. Esto permite autenticación stateless, ideal para aplicaciones SPA y móviles.

---

## 🔐 Endpoints de Autenticación

### JWT Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/jwt/token/` | Obtener access + refresh tokens |
| POST | `/api/v1/auth/jwt/token/refresh/` | Refrescar access token |
| POST | `/api/v1/auth/jwt/token/verify/` | Verificar si token es válido |
| POST | `/api/v1/auth/jwt/token/blacklist/` | Invalidar refresh token (logout) |

### Legacy Token (compatibilidad)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/token/` | Token DRF tradicional |

---

## 🛠️ Configuración

### settings.py

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',  # Legacy
        'rest_framework.authentication.SessionAuthentication',
    ],
    # ...
}

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
}
```

---

## 📝 Uso de la API

### 1. Obtener Tokens

```bash
# Request
curl -X POST http://localhost:8000/api/v1/auth/jwt/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# Response
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Usar Access Token

```bash
curl -X GET http://localhost:8000/api/v1/productos/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Refrescar Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/jwt/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'

# Response
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Nuevo refresh
}
```

### 4. Logout (Blacklist Token)

```bash
curl -X POST http://localhost:8000/api/v1/auth/jwt/token/blacklist/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

---

## 🔄 Flujo de Autenticación

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUJO JWT LUMINOVA                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Login                                                       │
│     POST /api/v1/auth/jwt/token/                                │
│     {username, password} ──► {access_token, refresh_token}      │
│                                                                 │
│  2. API Requests                                                │
│     GET /api/v1/productos/                                      │
│     Header: Authorization: Bearer {access_token}                │
│                                                                 │
│  3. Token Expired (401)                                         │
│     POST /api/v1/auth/jwt/token/refresh/                        │
│     {refresh_token} ──► {new_access_token, new_refresh_token}   │
│                                                                 │
│  4. Logout                                                      │
│     POST /api/v1/auth/jwt/token/blacklist/                      │
│     {refresh_token} ──► Token invalidado                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔒 Seguridad

### Token Rotation

- Cada vez que se refresca el access token, se genera un nuevo refresh token
- El refresh token antiguo se agrega al blacklist
- Previene reutilización de tokens comprometidos

### Blacklist

- Tabla `token_blacklist_outstandingtoken` almacena tokens emitidos
- Tabla `token_blacklist_blacklistedtoken` almacena tokens invalidados
- Permite logout efectivo (invalidar refresh tokens)

### Tiempos de Expiración

| Token Type | Duración | Propósito |
|------------|----------|-----------|
| Access Token | 60 minutos | Autenticación de requests |
| Refresh Token | 7 días | Obtener nuevos access tokens |

---

## 🧪 Testing

### Generar Tokens Manualmente

```python
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

user = User.objects.get(username='admin')
refresh = RefreshToken.for_user(user)

print(f'Refresh Token: {refresh}')
print(f'Access Token: {refresh.access_token}')
```

### Decodificar Token

```python
import jwt
from django.conf import settings

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
print(decoded)
# {'token_type': 'access', 'exp': 1736880522, 'user_id': 1, ...}
```

---

## 📊 Comparación con Token DRF

| Característica | JWT (Simple JWT) | Token DRF |
|----------------|------------------|-----------|
| Stateless | ✅ Sí | ❌ No (BD lookup) |
| Expiración | ✅ Automática | ❌ Manual |
| Rotación | ✅ Automática | ❌ No |
| Blacklist | ✅ Soportado | ❌ Eliminar de BD |
| Escalabilidad | ✅ Alta | ⚠️ Media |
| Info en Token | ✅ Payload custom | ❌ Solo key |

---

## 📚 Referencias

- [Simple JWT Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)
- [JWT.io](https://jwt.io/) - Debugger de tokens
- [RFC 7519 - JSON Web Token](https://datatracker.ietf.org/doc/html/rfc7519)
