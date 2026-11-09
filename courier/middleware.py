from django.utils.cache import add_never_cache_headers


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
