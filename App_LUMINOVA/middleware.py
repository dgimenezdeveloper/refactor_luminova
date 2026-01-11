from django.shortcuts import redirect
from django.urls import reverse

from .models import PasswordChangeRequired
from .threadlocals import set_current_empresa


class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_paths = [
            reverse("App_LUMINOVA:change_password"),
            reverse("App_LUMINOVA:logout"),
        ]

    def __call__(self, request):
        # Primero, procesamos la solicitud para obtener la respuesta.
        # Esto permite que otras partes de Django (como la sesión) se carguen.
        response = self.get_response(request)

        # El middleware solo actúa si el usuario está autenticado y no es superusuario
        # (los superusuarios pueden necesitar acceso total para depurar)
        if not request.user.is_authenticated or request.user.is_superuser:
            return response

        # Ignorar peticiones para archivos estáticos/media y para el panel de admin de Django
        if request.path_info.startswith(("/static/", "/media/", "/admin/")):
            return response

        # Si el usuario está en una de las páginas permitidas, no hacemos nada más
        if request.path_info in self.allowed_paths:
            return response

        # La comprobación clave: ¿Necesita cambiar la contraseña?
        if PasswordChangeRequired.objects.filter(user=request.user).exists():
            # Si está aquí, significa que intentó acceder a una página no permitida.
            # Lo redirigimos forzosamente.
            return redirect("App_LUMINOVA:change_password")

        # Si no se cumple ninguna de las condiciones de redirección, devolvemos la respuesta original.
        return response


class EmpresaMiddleware:
    """
    Middleware para gestionar la empresa actual del usuario.
    Agrega request.empresa_actual para acceso fácil en vistas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .models import Empresa, PerfilUsuario
        
        request.empresa_actual = None
        
        if request.user.is_authenticated:
            # Obtener empresa desde sesión o perfil del usuario
            empresa_id = request.session.get('empresa_actual_id')
            
            if empresa_id:
                try:
                    request.empresa_actual = Empresa.objects.get(id=empresa_id, activa=True)
                except Empresa.DoesNotExist:
                    empresa_id = None
            
            # Si no hay empresa en sesión, obtener del perfil del usuario
            if not empresa_id:
                try:
                    perfil = PerfilUsuario.objects.select_related('empresa').get(user=request.user)
                    request.empresa_actual = perfil.empresa
                    request.session['empresa_actual_id'] = perfil.empresa.id
                except PerfilUsuario.DoesNotExist:
                    # Si el usuario no tiene perfil, asignar empresa por defecto
                    empresa_default = Empresa.objects.filter(activa=True).first()
                    if empresa_default:
                        request.empresa_actual = empresa_default
                        request.session['empresa_actual_id'] = empresa_default.id
        set_current_empresa(request.empresa_actual)
        try:
            response = self.get_response(request)
        finally:
            set_current_empresa(None)
        return response
