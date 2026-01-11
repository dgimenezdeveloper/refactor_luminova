# Alternancia y Rollback entre SQLite y PostgreSQL en LUMINOVA

## Alternar entre motores de base de datos

La configuración dinámica en `settings.py` permite alternar entre SQLite y PostgreSQL modificando el archivo `.env`:

- Para usar **PostgreSQL**:
  - Completa los campos en `.env`:
    ```
    DB_ENGINE=django.db.backends.postgresql
    DB_NAME=luminova_db
    DB_USER=luminova_user
    DB_PASSWORD=luminova-pass
    DB_HOST=localhost
    DB_PORT=5432
    ```
- Para usar **SQLite** (rollback):
  - Borra o comenta las variables anteriores en `.env`.
  - Django usará automáticamente `db.sqlite3` como base de datos.

## Rollback seguro

1. Antes de migrar, realiza un backup de `db.sqlite3` y de la base PostgreSQL:
   - SQLite: `cp db.sqlite3 db.sqlite3.bak`
   - PostgreSQL: `pg_dump luminova_db > luminova_db.bak.sql`
2. Para volver a SQLite, restaura el archivo y borra las variables de PostgreSQL en `.env`.
3. Para volver a PostgreSQL, restaura el dump y completa las variables en `.env`.

## Recomendaciones
- No borres la base SQLite hasta validar que todo funciona en PostgreSQL.
- Mantén los dumps actualizados antes de cualquier migración.
- Si usas `loaddata`, valida los datos y relaciones antes de operar en producción.

---
**Última actualización:** 2 de octubre de 2025
