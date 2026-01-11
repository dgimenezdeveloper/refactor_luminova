# Documentación de LUMINOVA

Sistema ERP Multi-depósito Multi-Tenant - Documentación Técnica y Funcional

---

## Estructura de Documentación

### [Arquitectura](arquitectura/)
Documentación técnica sobre la arquitectura del sistema, planes de refactorización y mejoras propuestas.

| Documento | Descripción |
|-----------|-------------|
| [Análisis y Crítica Constructiva](arquitectura/ANALISIS_CRITICA_CONSTRUCTIVA.md) | Evaluación completa del sistema actual |
| [Plan de Refactorización](arquitectura/ANALISIS_REFACTORIZACION.md) | Roadmap de mejoras técnicas |
| [Arquitectura Multi-Tenancy](arquitectura/ARQUITECTURA_MULTITENANCY.md) | Diseño para SaaS multi-empresa |
| [Diagnóstico y Propuesta de Mejora](arquitectura/DIAGNOSTICO_PROPUESTA_MEJORA.md) | Estado actual y recomendaciones |

### [Funcionalidades](funcionalidades/)
Documentación de funcionalidades específicas implementadas o en desarrollo.

| Documento | Descripción |
|-----------|-------------|
| [Gestión de Usuarios y Depósitos](funcionalidades/USUARIO_DEPOSITO.md) | Sistema de permisos por depósito |
| [Producción para Stock](funcionalidades/PRODUCCION_STOCK.md) | Sistema de producción automatizada |
| [Transferencias](funcionalidades/TRANSFERENCIAS_MEJORAS.md) | Sistema de transferencias entre depósitos |
| [Resumen de Implementación](funcionalidades/RESUMEN_IMPLEMENTACION.md) | Estado general de implementaciones |

### [Soluciones Verticales](soluciones/)
Adaptaciones del sistema para industrias específicas.

| Documento | Descripción |
|-----------|-------------|
| [Solución Hormigonera](soluciones/SOLUCION_HORMIGONERA.md) | Adaptación para plantas de hormigón |
| [Análisis Hormigonera](soluciones/CRITICA_HORMIGONERA.md) | Evaluación de requerimientos |
| [Filtros por Empresa](soluciones/SOLUCION_FILTROS_EMPRESA.md) | Implementación de filtros multi-tenant |

### [Guías de Uso](guias/)
Guías prácticas para usuarios y administradores.

| Documento | Descripción |
|-----------|-------------|
| [Inicio Rápido](guias/INICIO_RAPIDO.md) | Guía de inicio rápido |
| [Migración de Base de Datos](guias/README_DB_MIGRACION.md) | Guía para migrar la BD |
| [Importación de Datos](guias/README_IMPORTACION.md) | Guía para importar datos |

---

## Enlaces Rápidos

- [README Principal](../README.md) - Instrucciones de instalación y uso
- [Código Fuente](../App_LUMINOVA/) - Aplicación principal Django
- [Configuración](../Proyecto_LUMINOVA/settings.py) - Settings de Django
- [Scripts de Utilidad](../scripts/) - Scripts auxiliares

---

## Estado del Proyecto

| Componente | Estado |
|------------|--------|
| Multi-tenancy | Implementado |
| Gestión de Depósitos | Implementado |
| Producción | Implementado |
| Compras | Implementado |
| Ventas | Implementado |
| Control de Calidad | Implementado |

---

*Última actualización: Enero 2026*
