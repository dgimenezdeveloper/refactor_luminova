#!/usr/bin/env python
"""
Script de Migración SQLite a PostgreSQL - LUMINOVA ERP
========================================================

Este script automatiza el proceso de migración de datos desde SQLite a PostgreSQL.

NOTA: Este script fue creado durante la migración inicial el 14/01/2026.
      Para nuevas migraciones, se recomienda seguir la guía en:
      docs/arquitectura/MIGRACION_POSTGRESQL.md

Uso:
    1. Asegúrate de tener PostgreSQL instalado y corriendo
    2. Crea la base de datos y usuario en PostgreSQL (ver instrucciones abajo)
    3. Configura las variables en el archivo .env
    4. Ejecuta: python scripts/migrate_to_postgresql.py

Comandos PostgreSQL necesarios (ejecutar como superusuario postgres):
    sudo -u postgres psql
    CREATE DATABASE luminova_db;
    CREATE USER luminova_user WITH PASSWORD 'luminova_password_2026';
    ALTER ROLE luminova_user SET client_encoding TO 'utf8';
    ALTER ROLE luminova_user SET default_transaction_isolation TO 'read committed';
    ALTER ROLE luminova_user SET timezone TO 'America/Argentina/Buenos_Aires';
    GRANT ALL PRIVILEGES ON DATABASE luminova_db TO luminova_user;
    
    -- Para PostgreSQL 15+:
    \\c luminova_db
    GRANT ALL ON SCHEMA public TO luminova_user;
    \\q
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')


class MigrationManager:
    """Gestor de migración de SQLite a PostgreSQL"""
    
    def __init__(self):
        self.base_dir = BASE_DIR
        self.sqlite_db = self.base_dir / 'db.sqlite3'
        self.backup_dir = self.base_dir / 'backups'
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def print_header(self, message):
        """Imprime un encabezado formateado"""
        print("\n" + "=" * 60)
        print(f"  {message}")
        print("=" * 60)
        
    def print_step(self, step_num, message):
        """Imprime un paso numerado"""
        print(f"\n[Paso {step_num}] {message}")
        print("-" * 40)
        
    def print_success(self, message):
        """Imprime un mensaje de éxito"""
        print(f"✅ {message}")
        
    def print_error(self, message):
        """Imprime un mensaje de error"""
        print(f"❌ {message}")
        
    def print_info(self, message):
        """Imprime un mensaje informativo"""
        print(f"ℹ️  {message}")
        
    def check_prerequisites(self):
        """Verifica los prerequisitos para la migración"""
        self.print_step(1, "Verificando prerequisitos")
        
        # Verificar que existe la base de datos SQLite
        if not self.sqlite_db.exists():
            self.print_error(f"No se encontró la base de datos SQLite: {self.sqlite_db}")
            return False
        self.print_success(f"Base de datos SQLite encontrada: {self.sqlite_db}")
        
        # Verificar variables de entorno para PostgreSQL
        required_vars = ['DB_ENGINE', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            self.print_error(f"Variables de entorno faltantes: {', '.join(missing_vars)}")
            self.print_info("Configura el archivo .env con las credenciales de PostgreSQL")
            return False
        self.print_success("Variables de entorno configuradas correctamente")
        
        # Verificar que el motor es PostgreSQL
        db_engine = os.environ.get('DB_ENGINE', '')
        if 'postgresql' not in db_engine:
            self.print_error(f"DB_ENGINE debe ser 'django.db.backends.postgresql', actual: {db_engine}")
            return False
        self.print_success("Motor de base de datos configurado para PostgreSQL")
        
        return True
        
    def create_backup_dir(self):
        """Crea el directorio de backups si no existe"""
        self.backup_dir.mkdir(exist_ok=True)
        self.print_success(f"Directorio de backups: {self.backup_dir}")
        
    def export_data_from_sqlite(self):
        """Exporta los datos de SQLite usando dumpdata"""
        self.print_step(2, "Exportando datos de SQLite")
        
        # Crear backup del dump
        dump_file = self.backup_dir / f'luminova_data_{self.timestamp}.json'
        
        self.print_info("Ejecutando dumpdata desde SQLite...")
        
        # Crear un script temporal que force SQLite
        temp_script = self.base_dir / 'temp_export_sqlite.py'
        
        script_content = '''#!/usr/bin/env python
import os
import sys
import django

# Forzar SQLite eliminando variables de PostgreSQL
for var in ['DB_ENGINE', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']:
    os.environ.pop(var, None)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from django.core.management import call_command

dump_file = sys.argv[1]
call_command(
    'dumpdata',
    '--exclude', 'contenttypes',
    '--exclude', 'auth.permission', 
    '--indent', '2',
    '--output', dump_file
)
print(f"Exportado a: {dump_file}")
'''
        
        try:
            # Escribir script temporal
            with open(temp_script, 'w') as f:
                f.write(script_content)
            
            # Crear un entorno limpio sin las variables de PostgreSQL
            clean_env = os.environ.copy()
            pg_vars = ['DB_ENGINE', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']
            for var in pg_vars:
                clean_env.pop(var, None)
            
            # Ejecutar el script temporal
            result = subprocess.run(
                [sys.executable, str(temp_script), str(dump_file)],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                env=clean_env
            )
            
            if result.returncode != 0:
                self.print_error(f"Error al exportar datos: {result.stderr}")
                return None
            
            if not dump_file.exists():
                self.print_error("El archivo de exportación no se creó")
                return None
                
            self.print_success(f"Datos exportados a: {dump_file}")
            
            # Verificar tamaño del archivo
            file_size = dump_file.stat().st_size / 1024  # KB
            self.print_info(f"Tamaño del archivo: {file_size:.2f} KB")
            
            return dump_file
            
        except Exception as e:
            self.print_error(f"Error durante la exportación: {e}")
            return None
        finally:
            # Limpiar script temporal
            if temp_script.exists():
                temp_script.unlink()
                    
    def test_postgresql_connection(self):
        """Prueba la conexión a PostgreSQL"""
        self.print_step(3, "Probando conexión a PostgreSQL")
        
        try:
            import psycopg2
            
            conn = psycopg2.connect(
                dbname=os.environ.get('DB_NAME'),
                user=os.environ.get('DB_USER'),
                password=os.environ.get('DB_PASSWORD'),
                host=os.environ.get('DB_HOST'),
                port=os.environ.get('DB_PORT')
            )
            
            cursor = conn.cursor()
            cursor.execute('SELECT version();')
            version = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            self.print_success(f"Conexión exitosa a PostgreSQL")
            self.print_info(f"Versión: {version[:50]}...")
            return True
            
        except Exception as e:
            self.print_error(f"Error al conectar a PostgreSQL: {e}")
            self.print_info("Asegúrate de haber creado la base de datos y el usuario.")
            self.print_info("Ejecuta los comandos SQL indicados en la documentación.")
            return False
            
    def run_migrations(self):
        """Ejecuta las migraciones en PostgreSQL"""
        self.print_step(4, "Ejecutando migraciones en PostgreSQL")
        
        self.print_info("Aplicando migraciones...")
        
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', '--verbosity', '1'],
            cwd=str(self.base_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            self.print_error(f"Error al ejecutar migraciones: {result.stderr}")
            return False
            
        self.print_success("Migraciones aplicadas correctamente")
        print(result.stdout)
        return True
        
    def load_data_to_postgresql(self, dump_file):
        """Carga los datos en PostgreSQL"""
        self.print_step(5, "Cargando datos en PostgreSQL")
        
        if not dump_file or not dump_file.exists():
            self.print_error("No se encontró el archivo de datos")
            return False
            
        self.print_info(f"Cargando datos desde: {dump_file}")
        
        result = subprocess.run(
            [sys.executable, 'manage.py', 'loaddata', str(dump_file)],
            cwd=str(self.base_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            self.print_error(f"Error al cargar datos: {result.stderr}")
            # Intentar mostrar más detalles del error
            if 'IntegrityError' in result.stderr:
                self.print_info("Posible conflicto de integridad. Los datos pueden ya existir.")
            return False
            
        self.print_success("Datos cargados correctamente")
        print(result.stdout)
        return True
        
    def verify_migration(self):
        """Verifica que la migración fue exitosa"""
        self.print_step(6, "Verificando migración")
        
        # Configurar Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
        import django
        django.setup()
        
        from django.contrib.auth.models import User
        from App_LUMINOVA.models import Empresa, Deposito, ProductoTerminado, Insumo
        
        counts = {
            'Usuarios': User.objects.count(),
            'Empresas': Empresa.objects.count(),
            'Depósitos': Deposito.objects.count(),
            'Productos': ProductoTerminado.objects.count(),
            'Insumos': Insumo.objects.count(),
        }
        
        print("\nConteo de registros en PostgreSQL:")
        print("-" * 30)
        for model, count in counts.items():
            print(f"  {model}: {count}")
            
        total = sum(counts.values())
        if total > 0:
            self.print_success(f"Total de registros migrados: {total}")
            return True
        else:
            self.print_error("No se encontraron registros en la base de datos")
            return False
            
    def run_full_migration(self):
        """Ejecuta el proceso completo de migración"""
        self.print_header("MIGRACIÓN LUMINOVA: SQLite → PostgreSQL")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Paso 1: Verificar prerequisitos
        if not self.check_prerequisites():
            return False
            
        # Crear directorio de backups
        self.create_backup_dir()
        
        # Paso 2: Exportar datos de SQLite
        dump_file = self.export_data_from_sqlite()
        if not dump_file:
            return False
            
        # Paso 3: Probar conexión a PostgreSQL
        if not self.test_postgresql_connection():
            return False
            
        # Paso 4: Ejecutar migraciones
        if not self.run_migrations():
            return False
            
        # Paso 5: Cargar datos
        if not self.load_data_to_postgresql(dump_file):
            return False
            
        # Paso 6: Verificar migración
        if not self.verify_migration():
            return False
            
        self.print_header("¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
        print("""
Próximos pasos:
1. Verifica que la aplicación funcione correctamente
2. Ejecuta: python manage.py runserver
3. Prueba las funcionalidades principales
4. Si todo está bien, puedes eliminar db.sqlite3 (recomendado mantener backup)

Archivo de backup: {}
        """.format(dump_file))
        
        return True


def print_setup_instructions():
    """Imprime las instrucciones de configuración de PostgreSQL"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         INSTRUCCIONES DE CONFIGURACIÓN DE POSTGRESQL                 ║
╚══════════════════════════════════════════════════════════════════════╝

Antes de ejecutar la migración, necesitas crear la base de datos y el usuario.

1. Abre una terminal y ejecuta:
   sudo -u postgres psql

2. Dentro de PostgreSQL, ejecuta estos comandos:

   CREATE DATABASE luminova_db;
   CREATE USER luminova_user WITH PASSWORD 'luminova_password_2026';
   ALTER ROLE luminova_user SET client_encoding TO 'utf8';
   ALTER ROLE luminova_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE luminova_user SET timezone TO 'America/Argentina/Buenos_Aires';
   GRANT ALL PRIVILEGES ON DATABASE luminova_db TO luminova_user;
   
   -- Para PostgreSQL 15+, también necesitas:
   \\c luminova_db
   GRANT ALL ON SCHEMA public TO luminova_user;
   
   \\q

3. Verifica que el archivo .env tenga las credenciales correctas:
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=luminova_db
   DB_USER=luminova_user
   DB_PASSWORD=luminova_password_2026
   DB_HOST=localhost
   DB_PORT=5432

4. Ejecuta nuevamente este script:
   python scripts/migrate_to_postgresql.py

""")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrar LUMINOVA de SQLite a PostgreSQL'
    )
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Mostrar instrucciones de configuración de PostgreSQL'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Solo verificar prerequisitos sin migrar'
    )
    
    args = parser.parse_args()
    
    if args.setup:
        print_setup_instructions()
        sys.exit(0)
        
    manager = MigrationManager()
    
    if args.check:
        success = manager.check_prerequisites()
        sys.exit(0 if success else 1)
    
    success = manager.run_full_migration()
    sys.exit(0 if success else 1)
