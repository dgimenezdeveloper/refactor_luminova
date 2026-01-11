import logging

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm

# Django Contrib Imports
from django.contrib.auth.models import Group, Permission, User
from django.db import IntegrityError as DjangoIntegrityError
from django.db import transaction


# Django Core Imports
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from Proyecto_LUMINOVA import settings

# Local Application Imports (Forms)
from .forms import (
    RolForm,
)

# Local Application Imports (Models)
from .models import (
    AuditoriaAcceso,
    PasswordChangeRequired,
    RolDescripcion,
    RolEmpresa,
)

from .utils import es_admin

logger = logging.getLogger(__name__)
# --- ADMINISTRATOR VIEWS ---
@login_required
@user_passes_test(es_admin)
def lista_usuarios(request):
    from .models import Deposito, UsuarioDeposito, RolEmpresa
    
    from .models import PerfilUsuario
    empresa_actual = getattr(request, 'empresa_actual', None)
    if not empresa_actual:
        messages.error(request, "No se pudo determinar la empresa actual del usuario.")
        return redirect("App_LUMINOVA:dashboard")

    usuarios = (
        User.objects.filter(
            is_superuser=False,
            perfil__empresa=empresa_actual,
            perfil__isnull=False
        )
        .prefetch_related("groups", "depositos_asignados")
        .order_by("id")
    )

    # Filtrar roles por empresa actual
    roles_empresa = RolEmpresa.objects.filter(empresa=empresa_actual).select_related('group')

    # Agregar información de depósitos asignados a cada usuario
    for usuario in usuarios:
        usuario.depositos_asignados_ids = list(
            UsuarioDeposito.objects.filter(usuario=usuario).values_list('deposito_id', flat=True)
        )

    depositos = Deposito.objects.filter(empresa=empresa_actual).order_by('nombre')

    context = {
        "usuarios": usuarios,
        "depositos": depositos,
        "roles_empresa": roles_empresa,
        "titulo_seccion": "Gestión de Usuarios"
    }
    return render(request, "admin/usuarios.html", context)


@login_required
@user_passes_test(es_admin)
@transaction.atomic
def crear_usuario(request):
    from .models import RolEmpresa, Deposito, UsuarioDeposito, PerfilUsuario
    empresa_actual = getattr(request, 'empresa_actual', None)
    if not empresa_actual:
        messages.error(request, "No se pudo determinar la empresa actual del usuario.")
        return redirect("App_LUMINOVA:dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        rol_empresa_id = request.POST.get("rol_empresa")
        estado_str = request.POST.get("estado")
        depositos_seleccionados = request.POST.getlist("depositos")
        password = settings.DEFAULT_PASSWORD_FOR_NEW_USERS

        if User.objects.filter(username=username).exists():
            messages.error(request, f"El nombre de usuario '{username}' ya está en uso.")
            return redirect("App_LUMINOVA:lista_usuarios")

        if not username or not email or not rol_empresa_id or not estado_str:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect("App_LUMINOVA:lista_usuarios")

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_active = estado_str == "Activo"

            # Asignar el rol (grupo) usando RolEmpresa
            try:
                rol_empresa = RolEmpresa.objects.get(id=rol_empresa_id, empresa=empresa_actual)
                user.groups.add(rol_empresa.group)
            except RolEmpresa.DoesNotExist:
                messages.error(request, f"El rol seleccionado no existe para esta empresa. No se pudo crear el usuario.")
                raise Exception("RolEmpresa no existente")

            user.save()
            PerfilUsuario.objects.create(user=user, empresa=empresa_actual)

            # Asignar depósitos según el rol y la selección
            if rol_empresa.group.name == "Depósito":
                if depositos_seleccionados:
                    for deposito_id in depositos_seleccionados:
                        try:
                            deposito = Deposito.objects.get(id=deposito_id, empresa=empresa_actual)
                            UsuarioDeposito.objects.get_or_create(
                                usuario=user,
                                deposito=deposito,
                                defaults={
                                    "puede_transferir": True,
                                    "puede_entradas": True,
                                    "puede_salidas": True,
                                }
                            )
                        except Deposito.DoesNotExist:
                            continue
                else:
                    deposito = Deposito.objects.filter(empresa=empresa_actual).first()
                    if deposito:
                        UsuarioDeposito.objects.get_or_create(
                            usuario=user,
                            deposito=deposito,
                            defaults={
                                "puede_transferir": True,
                                "puede_entradas": True,
                                "puede_salidas": True,
                            }
                        )

            PasswordChangeRequired.objects.create(user=user)

            depositos_info = ""
            if rol_empresa.group.name == "Depósito" and depositos_seleccionados:
                depositos_nombres = []
                for deposito_id in depositos_seleccionados:
                    try:
                        deposito = Deposito.objects.get(id=deposito_id, empresa=empresa_actual)
                        depositos_nombres.append(deposito.nombre)
                    except Deposito.DoesNotExist:
                        continue
                if depositos_nombres:
                    depositos_info = f" con acceso a: {', '.join(depositos_nombres)}"

            messages.success(
                request,
                f"Usuario '{user.username}' creado exitosamente{depositos_info}. La contraseña por defecto es: '{password}'",
            )

        except DjangoIntegrityError as e:
            messages.error(
                request,
                f"Error de integridad al crear el usuario. Es posible que el email ya esté en uso. Detalle: {e}",
            )
        except Exception as e:
            if "RolEmpresa no existente" not in str(e):
                messages.error(request, f"Error inesperado al crear usuario: {e}")

    return redirect("App_LUMINOVA:lista_usuarios")


@login_required
def change_password_view(request):
    """
    Vista para que el usuario cambie su contraseña.
    Es forzado por el middleware si es su primer login.
    """
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            PasswordChangeRequired.objects.filter(user=request.user).delete()

            messages.success(
                request,
                "¡Tu contraseña ha sido actualizada exitosamente! Ya puedes navegar por el sitio.",
            )
            return redirect("App_LUMINOVA:dashboard")
        else:
            # --- CAMBIO AQUÍ: También modificar el form con errores ---
            form.fields["old_password"].widget.attrs[
                "autocomplete"
            ] = "current-password"
            form.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
            form.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"
            messages.error(request, "Por favor, corrige los errores a continuación.")
    else:
        if not PasswordChangeRequired.objects.filter(user=request.user).exists():
            return redirect("App_LUMINOVA:dashboard")

        form = PasswordChangeForm(request.user)
        # --- CAMBIO AQUÍ: Modificar el form antes de renderizarlo ---
        form.fields["old_password"].widget.attrs["autocomplete"] = "current-password"
        form.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
        form.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"

    context = {"form": form}
    return render(request, "change_password.html", context)


@login_required
@user_passes_test(es_admin)
@transaction.atomic
@require_POST
def editar_usuario(request, id):
    from .models import RolEmpresa, Deposito, UsuarioDeposito, PerfilUsuario
    usuario = get_object_or_404(User, id=id)
    empresa_actual = getattr(request, 'empresa_actual', None)
    if not empresa_actual:
        messages.error(request, "No se pudo determinar la empresa actual del usuario.")
        return redirect("App_LUMINOVA:dashboard")
    if request.method == "POST":
        usuario.username = request.POST.get("username", usuario.username)
        usuario.email = request.POST.get("email", usuario.email)
        depositos_seleccionados = request.POST.getlist("depositos")

        # Actualizar rol usando RolEmpresa
        rol_empresa_id = request.POST.get("rol_empresa")
        usuario.groups.clear()
        rol_empresa = None
        if rol_empresa_id:
            try:
                rol_empresa = RolEmpresa.objects.get(id=rol_empresa_id, empresa=empresa_actual)
                usuario.groups.add(rol_empresa.group)
            except RolEmpresa.DoesNotExist:
                messages.error(request, "El rol seleccionado no existe para esta empresa.")

        # Actualizar estado
        estado_str = request.POST.get("estado")
        if estado_str:
            usuario.is_active = estado_str == "Activo"

        usuario.save()

        # Gestionar asignaciones de depósitos
        UsuarioDeposito.objects.filter(usuario=usuario).delete()
        # Si el nuevo rol es Depósito, crear nuevas asignaciones
        if rol_empresa and rol_empresa.group.name == "Depósito":
            if depositos_seleccionados:
                for deposito_id in depositos_seleccionados:
                    try:
                        deposito = Deposito.objects.get(id=deposito_id, empresa=empresa_actual)
                        UsuarioDeposito.objects.create(
                            usuario=usuario,
                            deposito=deposito,
                            puede_transferir=True,
                            puede_entradas=True,
                            puede_salidas=True,
                        )
                    except Deposito.DoesNotExist:
                        continue
            else:
                deposito = Deposito.objects.filter(empresa=empresa_actual).first()
                if deposito:
                    UsuarioDeposito.objects.create(
                        usuario=usuario,
                        deposito=deposito,
                        puede_transferir=True,
                        puede_entradas=True,
                        puede_salidas=True,
                    )

        depositos_info = ""
        if rol_empresa and rol_empresa.group.name == "Depósito" and depositos_seleccionados:
            depositos_nombres = []
            for deposito_id in depositos_seleccionados:
                try:
                    deposito = Deposito.objects.get(id=deposito_id, empresa=empresa_actual)
                    depositos_nombres.append(deposito.nombre)
                except Deposito.DoesNotExist:
                    continue
            if depositos_nombres:
                depositos_info = f" con acceso actualizado a: {', '.join(depositos_nombres)}"

        messages.success(
            request, f"Usuario '{usuario.username}' actualizado exitosamente{depositos_info}."
        )
        return redirect("App_LUMINOVA:lista_usuarios")
    return redirect("App_LUMINOVA:lista_usuarios")  # Si no es POST


@login_required
@user_passes_test(es_admin)
@transaction.atomic
@require_POST
def eliminar_usuario(request, id):
    usuario = get_object_or_404(User, id=id)
    if usuario == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
        return redirect("App_LUMINOVA:lista_usuarios")
    try:
        nombre_usuario = usuario.username
        usuario.delete()
        messages.success(request, f"Usuario '{nombre_usuario}' eliminado exitosamente.")
    except Exception as e:
        messages.error(request, f"Error al eliminar usuario: {str(e)}")
    return redirect("App_LUMINOVA:lista_usuarios")


@login_required
def roles_permisos_view(request):
    empresa_actual = getattr(request, 'empresa_actual', None)
    roles_empresa = []
    if empresa_actual:
        roles_empresa = (
            RolEmpresa.objects.filter(empresa=empresa_actual)
            .select_related('group')
            .order_by('group__name')
        )
    context = {"roles_empresa": roles_empresa, "titulo_seccion": "Gestión de Roles y Permisos"}
    return render(request, "admin/roles_permisos.html", context)


@login_required
def auditoria_view(request):
    auditorias = AuditoriaAcceso.objects.select_related("usuario").order_by(
        "-fecha_hora"
    )

    from django.core.paginator import Paginator

    paginator = Paginator(auditorias, 25)  # 25 registros por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "auditorias": auditorias,  # O 'page_obj': page_obj si usas paginación
        "titulo_seccion": "Auditoría de Acceso",
    }
    return render(request, "admin/auditoria.html", context)


# --- AJAX VIEWS FOR ROLES & PERMISSIONS ---
@login_required
@user_passes_test(es_admin)
@require_POST
def crear_rol_ajax(request):
    form = RolForm(request.POST)
    empresa_actual = getattr(request, 'empresa_actual', None)
    if not empresa_actual:
        return JsonResponse({"success": False, "errors": {"__all__": ["Empresa no determinada."]}}, status=400)
    if form.is_valid():
        nombre_logico = form.cleaned_data["nombre"].strip()
        descripcion_rol = form.cleaned_data["descripcion"].strip()
        # Verificar unicidad lógica por empresa
        from .models import RolEmpresa
        if RolEmpresa.objects.filter(empresa=empresa_actual, nombre=nombre_logico).exists():
            return JsonResponse({"success": False, "errors": {"nombre": ["Ya existe un rol con ese nombre en esta empresa."]}}, status=400)
        try:
            with transaction.atomic():
                # Nombre físico del grupo para evitar colisión global
                nombre_grupo = f"{empresa_actual.id}__{nombre_logico}"
                nuevo_grupo = Group.objects.create(name=nombre_grupo)
                rol_empresa = RolEmpresa.objects.create(
                    empresa=empresa_actual,
                    group=nuevo_grupo,
                    nombre=nombre_logico,
                    descripcion=descripcion_rol
                )
                if descripcion_rol:
                    RolDescripcion.objects.create(group=nuevo_grupo, descripcion=descripcion_rol)
                return JsonResponse({
                    "success": True,
                    "rol": {
                        "id": rol_empresa.id,
                        "group_id": nuevo_grupo.id,
                        "nombre": rol_empresa.nombre,
                        "descripcion": rol_empresa.descripcion,
                    }
                })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"__all__": [str(e)]}}, status=500)
    else:
        return JsonResponse({"success": False, "errors": form.errors}, status=400)


@login_required
@user_passes_test(es_admin)
@require_GET
def get_rol_data_ajax(request):
    rol_id = request.GET.get("rol_id")
    try:
        grupo = Group.objects.get(id=rol_id)
        descripcion_extendida = ""
        if hasattr(grupo, "descripcion_extendida") and grupo.descripcion_extendida:
            descripcion_extendida = grupo.descripcion_extendida.descripcion

        return JsonResponse(
            {
                "success": True,
                "rol": {
                    "id": grupo.id,
                    "nombre": grupo.name,
                    "descripcion": descripcion_extendida,
                },
            }
        )
    except Group.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Rol no encontrado."}, status=404
        )


@login_required
@user_passes_test(es_admin)
@require_POST
def editar_rol_ajax(request):
    rol_empresa_id = request.POST.get("rol_id")
    empresa_actual = getattr(request, 'empresa_actual', None)
    from .models import RolEmpresa
    try:
        rol_empresa = RolEmpresa.objects.select_related('group').get(id=rol_empresa_id, empresa=empresa_actual)
    except RolEmpresa.DoesNotExist:
        return JsonResponse({"success": False, "errors": {"__all__": ["Rol no encontrado para esta empresa."]}}, status=404)

    form = RolForm(request.POST, initial={"rol_id": rol_empresa_id})
    if form.is_valid():
        nuevo_nombre_logico = form.cleaned_data["nombre"].strip()
        nueva_descripcion = form.cleaned_data["descripcion"].strip()
        # Unicidad lógica
        if RolEmpresa.objects.filter(empresa=empresa_actual, nombre=nuevo_nombre_logico).exclude(id=rol_empresa.id).exists():
            return JsonResponse({"success": False, "errors": {"nombre": ["Ya existe otro rol con ese nombre en esta empresa."]}}, status=400)
        try:
            with transaction.atomic():
                # Actualizar nombre lógico y compuesto del grupo
                rol_empresa.nombre = nuevo_nombre_logico
                rol_empresa.descripcion = nueva_descripcion
                rol_empresa.save(update_fields=["nombre", "descripcion"])
                nombre_grupo_nuevo = f"{empresa_actual.id}__{nuevo_nombre_logico}"
                if rol_empresa.group.name != nombre_grupo_nuevo:
                    rol_empresa.group.name = nombre_grupo_nuevo
                    rol_empresa.group.save(update_fields=["name"])
                # Actualizar descripción extendida
                desc_obj, _ = RolDescripcion.objects.get_or_create(group=rol_empresa.group)
                desc_obj.descripcion = nueva_descripcion
                desc_obj.save(update_fields=["descripcion"])
            return JsonResponse({
                "success": True,
                "rol": {
                    "id": rol_empresa.id,
                    "group_id": rol_empresa.group.id,
                    "nombre": rol_empresa.nombre,
                    "descripcion": rol_empresa.descripcion,
                }
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"__all__": [str(e)]}}, status=500)
    else:
        return JsonResponse({"success": False, "errors": form.errors}, status=400)


@login_required
@require_POST
def eliminar_rol_ajax(request):
    import json

    try:
        data = json.loads(request.body)
        rol_id = data.get("rol_id")  # id de RolEmpresa
        empresa_actual = getattr(request, 'empresa_actual', None)
        from .models import RolEmpresa
        rol_empresa = RolEmpresa.objects.select_related('group').get(id=rol_id, empresa=empresa_actual)
        grupo = rol_empresa.group
        if grupo.user_set.exists():
            return JsonResponse({"success": False, "error": "No se puede eliminar el rol porque tiene usuarios asignados."}, status=400)
        rol_empresa.delete()  # elimina relación
        grupo.delete()  # elimina grupo físico
        return JsonResponse({"success": True})
    except RolEmpresa.DoesNotExist:
        return JsonResponse({"success": False, "error": "Rol no encontrado para esta empresa."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@user_passes_test(es_admin)
@require_GET
def get_permisos_rol_ajax(request):
    rol_id = request.GET.get("rol_id")
    try:
        rol = Group.objects.get(id=rol_id)
        permisos_del_rol_ids = list(rol.permissions.values_list("id", flat=True))

        todos_los_permisos = Permission.objects.select_related("content_type").all()
        permisos_data = []
        for perm in todos_los_permisos:
            permisos_data.append(
                {
                    "id": perm.id,
                    "name": perm.name,
                    "codename": perm.codename,
                    "content_type_app_label": perm.content_type.app_label,
                    "content_type_model": perm.content_type.model,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "todos_los_permisos": permisos_data,
                "permisos_del_rol": permisos_del_rol_ids,
            }
        )
    except Group.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Rol no encontrado."}, status=404
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@user_passes_test(es_admin)
@require_POST
def actualizar_permisos_rol_ajax(request):
    import json

    try:
        data = json.loads(request.body)
        rol_id = data.get("rol_id")
        permisos_ids_str = data.get("permisos_ids", [])  # Lista de IDs como strings
        permisos_ids = [int(pid) for pid in permisos_ids_str]

        rol = Group.objects.get(id=rol_id)

        # Actualizar permisos
        rol.permissions.set(permisos_ids)  # set() maneja agregar y quitar

        return JsonResponse({"success": True, "message": "Permisos actualizados."})
    except Group.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Rol no encontrado."}, status=404
        )
    except Permission.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Uno o más permisos no son válidos."},
            status=400,
        )
    except ValueError:
        return JsonResponse(
            {"success": False, "error": "IDs de permisos inválidos."}, status=400
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Datos JSON inválidos."}, status=400
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

