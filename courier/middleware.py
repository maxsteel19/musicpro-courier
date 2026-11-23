from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

from .models import PerfilUsuario


class SinCacheParaUsuariosAutenticadosMiddleware:
    """Agrega cabeceras ``Cache-Control: no-cache, no-store`` a las respuestas
    de usuarios autenticados.

    Sin esto, después de cerrar sesión el navegador podría mostrar una página
    privada guardada en caché al presionar "Atrás".
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            add_never_cache_headers(response)
        return response


class ControlDeCuentaMiddleware:
    """Antes de usar el sistema, cada usuario autenticado debe:

    1. Aceptar la versión vigente del acuerdo de uso de datos.
    2. Cambiar su contraseña si es temporal (creada o restablecida por un
       administrador).

    Mientras no lo haga, cualquier página privada lo redirige al paso pendiente.
    """

    VISTAS_PERMITIDAS = {
        'login', 'logout', 'password_cambiar',
        'courier:acuerdo_datos', 'courier:privacidad', 'courier:inicio',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return None
        coincidencia = request.resolver_match
        if coincidencia is not None and coincidencia.view_name in self.VISTAS_PERMITIDAS:
            return None
        perfil = PerfilUsuario.de(user)
        if not perfil.acepto_acuerdo_vigente:
            url = reverse('courier:acuerdo_datos')
            return redirect(f'{url}?{urlencode({"next": request.get_full_path()})}')
        if perfil.debe_cambiar_password:
            messages.warning(request, 'Su contraseña es temporal. Debe cambiarla antes de continuar.')
            return redirect('password_cambiar')
        return None
