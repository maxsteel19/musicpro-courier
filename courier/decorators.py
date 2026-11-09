"""Decoradores de control de acceso usados por las vistas del sistema."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def es_administrador(usuario):
    """Un usuario administra el sistema si es staff o superusuario."""
    return usuario.is_authenticated and (usuario.is_staff or usuario.is_superuser)


def administrador_requerido(vista):
    """Exige sesión iniciada **y** rol de administrador.

    - Sin sesión: ``login_required`` redirige al formulario de login.
    - Con sesión pero sin rol de administrador: responde 403 (acceso denegado).
    """

    @wraps(vista)
    @login_required
    def _vista_protegida(request, *args, **kwargs):
        if not es_administrador(request.user):
            raise PermissionDenied('Solo los administradores pueden acceder a esta sección.')
        return vista(request, *args, **kwargs)

    return _vista_protegida
