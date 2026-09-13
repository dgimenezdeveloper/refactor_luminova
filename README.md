# 📦 Luminova ERP — Industrial Multi-Tenant ERP & Warehouse Management System

[![Framework](https://img.shields.io/badge/Framework-Django%205.2%20%7C%20Python%203.12-092E20?logo=django&logoColor=white)](#)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016%20%28Schema%20Isolated%29-336791?logo=postgresql&logoColor=white)](#)
[![Multi-Tenancy](https://img.shields.io/badge/Multi--Tenant-django--tenants%203.9-blue)](#)
[![API](https://img.shields.io/badge/API-Django%20REST%20Framework%20%7C%20OpenAPI%203.0-red?logo=fastapi&logoColor=white)](#)
[![Auth](https://img.shields.io/badge/Auth-Simple%20JWT%20(Token%20Rotation)-orange?logo=jsonwebtokens&logoColor=white)](#)
[![ETL](https://img.shields.io/badge/ETL-Pandas%20%7C%20OpenPyXL-150458?logo=pandas&logoColor=white)](#)
[![Reporting](https://img.shields.io/badge/Reporting-ReportLab%20PDF-brightgreen)](#)

> Enterprise-grade ERP platform refactored from a legacy monolithic architecture into a scalable multi-tenant SaaS. Features PostgreSQL schema-level isolation, a decoupled Django REST Framework API with JWT authentication, a flexible bulk ETL ingestion engine, Bill of Materials (BOM) management, Make-to-Order (MTO) and Make-to-Stock (MTS) production workflows, and strict multi-warehouse permission auditing inspired by industrial quality assurance standards.
>
> 🌐 **Quick Navigation / Navegación Rápida:** [English Documentation](#-english-documentation) | [Documentación en Español](#-documentación-en-español)

---

## 🌐 English Documentation

### 1. Executive Summary & System Overview
Originating as a comprehensive software audit and refactoring initiative of a legacy industrial management system, **Luminova ERP** is an enterprise resource planning solution engineered for manufacturing plants, multi-warehouse logistics networks, and industrial production facilities (e.g., lighting manufacturing, concrete batching plants, and chemical processing).

#### The Engineering Challenge
The original legacy codebase suffered from severe database denormalization (dual sources of truth for inventory counts), tight coupling between business logic and template rendering, global uniqueness constraints that prevented multi-company operations, and absence of standardized API integrations.

#### The Architectural Transformation
The system underwent an end-to-end refactoring roadmap documented in `docs/arquitectura/`:
1. **Three-Phase Database Normalization:** Eliminated volatile hardcoded stock counters and manual total fields in favor of dynamic relational models and optimized database-level queries.
2. **PostgreSQL Schema Multi-Tenancy:** Implemented `django-tenants` to partition tenant datasets into dedicated PostgreSQL schemas, preventing data leakage across companies while sharing a single unified codebase.
3. **Decoupled RESTful API Layer:** Engineered complete ViewSets with Django REST Framework (DRF), secured with asymmetric JWT authentication and documented via OpenAPI 3.0 (drf-spectacular).
4. **Universal Bulk Ingestion Engine:** Designed an ETL import subsystem using Pandas and OpenPyXL capable of parsing supplier catalogs, raw materials, and inventory balances with dynamic column alias mapping.

---

### 2. Industrial Quality Assurance & Traceability Origins
The architecture reflects rigorous standards derived from industrial quality assurance (drawing experience from pharmaceutical and chemical manufacturing traceability):

- **Zero Calculation Drift:** Inventory quantities (`Insumo.stock`, `ProductoTerminado.stock`) and commercial monetary totals (`OrdenVenta.total_ov`, `Orden.total_orden_compra`) are computed dynamically via database aggregates and model properties, eliminating silent desynchronization.
- **Granular Warehouse RBAC (`UsuarioDeposito`):** Warehouse operators have distinct, auditable capability flags (`puede_transferir`, `puede_entradas`, `puede_salidas`) partitioned per physical location.
- **Bi-Directional Batch Traceability:** Every manufacturing batch (`LoteProductoTerminado`) links back to the originating Production Order (`OrdenProduccion`), Bill of Materials (BOM), consumed supplies (`ConsumoMaterial`), and the client Sales Order (`OrdenVenta`).
- **Full Security Audit Trail (`AuditoriaAcceso`):** Real-time IP address and User-Agent logging for all system authentications, session expirations, and mandatory first-login password updates (`PasswordChangeRequired`).

---

### 3. Core Business Modules

```
Luminova ERP Modules
├── 🛒 Sales & Invoicing (Ventas)
│   ├── Sales Orders (OrdenVenta) with multi-item line breakdown
│   ├── Automated transactional invoice generation with ReportLab PDF export
│   └── Bi-directional state propagation linked to factory assembly lines
├── 🏭 Production & BOM (Producción)
│   ├── Dual dispatch modes: Make to Order (MTO) & Make to Stock (MTS)
│   ├── Parametric Bill of Materials (ComponenteProducto) linking raw materials
│   └── Shopfloor incident management (Reportes) with downtime resolution
├── 📦 Warehouse & Stock Logistics (Depósito)
│   ├── Multi-warehouse transfer engine with atomic transactions
│   ├── Automated stock replenishing triggers based on minimum safety thresholds
│   └── Physical receiving validation for inbound freight shipments
├── 🚚 Procurement & Sourcing (Compras)
│   ├── Multi-supplier quotation comparison (OfertaProveedor)
│   ├── Purchase Order workflow: Draft -> Approved -> In Transit -> Completed
│   └── Automatic supplier delivery tracking number integration
└── 📥 Bulk ETL Ingestion (Carga Masiva)
    ├── Automated CSV and Excel parsing with encoding detection (UTF-8 / Latin-1)
    ├── Dynamic column alias mapping for raw materials, finished goods, and suppliers
    └── Execution ledger with error reporting (HistorialImportacion)
```

---

### 4. Technical Stack Specification

| Layer / Subsystem | Technology | Version | Architectural Responsibility |
| :--- | :--- | :--- | :--- |
| **Core Framework** | Django | `5.2.1` | Web framework, ORM, migration engine, and session management |
| **Language Runtime**| Python | `3.12+` | Strongly-typed backend execution environment |
| **Primary Database**| PostgreSQL | `16.x` | Relational persistence with isolated schema multi-tenancy |
| **Multi-Tenancy** | django-tenants | `3.9.0` | Tenant routing via subdomains and schema search path isolation |
| **REST Framework** | DRF | `3.14.0` | Serialization pipeline, ViewSets, and content negotiation |
| **Authentication** | Simple JWT | `5.3.1` | Stateless authentication, token rotation, and blacklist tracking |
| **API Documentation**| drf-spectacular | `0.27.0` | Automated OpenAPI 3.0 schema generation, Swagger & ReDoc |
| **Data Processing** | Pandas / OpenPyXL | `2.3.3` / `3.1.5` | High-performance tabular data ingestion and Excel generation |
| **PDF Generation** | ReportLab | `4.4.1` | Vector-drawn transactional commercial invoices |
| **Frontend UI** | Django MTV + Bootstrap | `5.2.3` | Responsive server-side rendered dashboard with Bootstrap Icons |

---

### 5. REST API & OpenAPI Documentation

Luminova exposes a versioned, multi-tenant scoped RESTful API (`/api/v1/`). All database queries executed through the API automatically restrict their scope to the tenant linked to the requesting authenticated user.

#### Authentication Workflow (JWT)
```bash
# 1. Obtain JWT Access and Refresh Tokens
curl -X POST http://localhost:8000/api/v1/auth/jwt/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "warehouse_admin", "password": "your_password"}'

# Response:
# {
#   "access": "eyJhbGciOiJIUzI1NiIsIn...",
#   "refresh": "eyJhbGciOiJIUzI1NiIsIn..."
# }

# 2. Query Scoped Products using Bearer Token
curl -X GET http://localhost:8000/api/v1/productos/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

#### Interactive Documentation Interfaces
- **Swagger UI (Interactive API explorer):** `http://localhost:8000/api/docs/`
- **ReDoc (Human-readable technical reference):** `http://localhost:8000/api/redoc/`
- **Raw OpenAPI 3.0 Schema:** `http://localhost:8000/api/schema/`

---

### 6. Local Setup & Quick Start

#### Prerequisites
- Python 3.12+ installed.
- PostgreSQL 16+ running locally or inside Docker.

#### Installation Steps
```bash
# 1. Clone the repository
git clone https://github.com/dgimenezdeveloper/refactor_luminova.git
cd refactor_luminova

# 2. Create and activate virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your PostgreSQL credentials:
# DB_NAME=luminova_db
# DB_USER=luminova_user
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432

# 5. Apply multi-tenant schema migrations
python manage.py migrate_schemas --shared
python manage.py migrate_schemas

# 6. (Optional) Run verification suite
python scripts/verificar_multitenancy.py

# 7. Start the development server
python manage.py runserver
```

Access the system at `http://localhost:8000`.

---

## 🇪🇸 Documentación en Español

### 1. Resumen Ejecutivo y Alcance del Sistema
Nacido de un diagnóstico exhaustivo de auditoría y refactorización sobre un sistema de gestión empresarial legado, **Luminova ERP** es una plataforma integral de planificación de recursos empresariales concebida para fábricas, plantas manufactureras y redes logísticas con múltiples depósitos.

#### El Desafío de Ingeniería
El código monolítico inicial presentaba desnormalización de stock (duplicidad de fuentes de verdad), acoplamiento entre la lógica de negocio y las vistas, restricciones de unicidad globales que impedían el uso multi-empresa y ausencia de APIs estándar.

#### La Transformación Arquitectónica
El sistema fue refactorizado siguiendo la hoja de ruta documentada en `docs/arquitectura/`:
1. **Normalización en 3 Fases:** Eliminación de campos de stock redundantes y totales manuales; implementación de propiedades relacionales calculadas y 43 índices compuestos de alto rendimiento.
2. **Multi-Tenancy por Esquemas (PostgreSQL):** Implementación de `django-tenants` para aislar los datos de cada empresa en esquemas independientes de PostgreSQL, garantizando confidencialidad y escalabilidad.
3. **Capa de API REST Desacoplada:** Desarrollo de ViewSets con Django REST Framework, autenticación stateless con JWT (rotación y lista negra de tokens) y documentación OpenAPI 3.0.
4. **Motor Universal de Carga Masiva (ETL):** Módulo de ingesta con Pandas y OpenPyXL para importar catálogos de insumos, productos, clientes y proveedores mediante mapeo flexible de alias.

---

### 2. Rigor de Calidad y Trazabilidad Industrial
La arquitectura adopta estándares de calidad propios de la industria química y farmacéutica (control de procesos, rigor metodológico y auditoría):

- **Cero Deriva en Cálculos:** El inventario y los totales monetarios se calculan en tiempo real desde la base de datos relacional, impidiendo desfasajes contables.
- **Permisos Granulares por Depósito (`UsuarioDeposito`):** Control estricto sobre las acciones que cada operario puede realizar (`puede_transferir`, `puede_entradas`, `puede_salidas`) por cada ubicación física.
- **Trazabilidad de Lotes de Producción:** Cada lote elaborado (`LoteProductoTerminado`) mantiene la trazabilidad hacia su orden de producción, lista de materiales (BOM), consumos reales y orden de venta origen.
- **Auditoría de Accesos (`AuditoriaAcceso`):** Registro inmutable de direcciones IP y navegadores en inicios de sesión, cambios obligatorios de clave y cierre de sesiones.

---

### 3. Módulos Principales del Negocio
- **Ventas y Facturación:** Gestión de órdenes de venta con emisión de facturas en PDF generadas vectorialmente con ReportLab.
- **Producción y BOM:** Fabricación bajo demanda (MTO) y para stock (MTS), listas de materiales y reporte de incidentes en planta.
- **Depósitos y Logística:** Transferencias atómicas entre depósitos, alarmas automáticas por quiebre de stock y control de recepción de mercadería.
- **Compras y Proveedores:** Comparativa de ofertas por insumo, seguimiento de órdenes de compra y control de números de guía/tracking.
- **Importación Masiva:** Procesamiento de archivos Excel y CSV con validación de tipos y registro histórico de ejecuciones.

---

### 4. Puesta en Marcha Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/dgimenezdeveloper/refactor_luminova.git
cd refactor_luminova

# 2. Crear y activar entorno virtual
python -m venv env
source env/bin/activate  # En Windows: env\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (.env)
cp .env.example .env

# 5. Aplicar migraciones multi-tenant
python manage.py migrate_schemas --shared
python manage.py migrate_schemas

# 6. Iniciar servidor
python manage.py runserver
```

---

## 👥 Authors & Engineering Leadership

- **Darío Giménez** — *Software Architect, Full-Stack Developer & Technical Auditor*  
  [GitHub](https://github.com/dgimenezdeveloper) • [LinkedIn](https://www.linkedin.com/in/daseg/) • [Portfolio](https://portafolio-daseg.vercel.app/)

---

## 📄 License
This project is licensed under the **MIT License**. See repository settings for details.
