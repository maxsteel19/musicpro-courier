from django.utils import timezone

from .decorators import es_administrador


def datos_generales(request):
    """Variables disponibles en todas las plantillas."""
    return {
        'empresa': 'Music Pro Tour',
        'anio_actual': timezone.localdate().year,
        'es_admin': es_administrador(request.user) if hasattr(request, 'user') else False,
    }
