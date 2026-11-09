from django.shortcuts import render

from ..models import Sucursal


def inicio(request):
    """Página pública: presenta el servicio e invita a iniciar sesión.

    No muestra datos operacionales (envíos, KPIs, usuarios); solo
    información que la empresa publicaría en su sitio web.
    """
    sucursales = Sucursal.objects.filter(activa=True).only('nombre', 'ciudad', 'direccion')
    return render(request, 'courier/publico/inicio.html', {'sucursales': sucursales})
