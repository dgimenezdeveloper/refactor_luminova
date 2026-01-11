"""Thread-local helpers para exponer la empresa actual fuera del request."""
from threading import local


_locals = local()


def set_current_empresa(empresa):
    """Guarda la empresa activa del request en curso."""
    _locals.empresa_actual = empresa


def get_current_empresa():
    """Devuelve la empresa activa disponible para modelos/señales."""
    return getattr(_locals, "empresa_actual", None)