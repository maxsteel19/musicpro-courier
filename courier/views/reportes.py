"""Página de reportes: ejecuta las consultas ORM de ``courier/reportes.py``."""
import inspect
from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Max, Min
from django.http import Http404
from django.shortcuts import render
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from .. import graficos
from ..entradas import ParametrosReporte
from ..models import Conductor, TipoVehiculo, Vehiculo, Viaje
from ..reportes import REPORTES

NIVELES = ['Básico', 'Intermedio', 'Avanzado', 'Análisis']


@login_required
def reportes_indice(request):
    grupos = [(nivel, [r for r in REPORTES.values() if r.nivel == nivel]) for nivel in NIVELES]
    return render(request, 'courier/reportes/indice.html', {
        'titulo': 'Reportes ORM - Transporte',
        'grupos': grupos,
        'total': len(REPORTES),
    })


def _valores_por_defecto(reporte):
    """Valores iniciales razonables para los parámetros de cada reporte."""
    hoy = timezone.localdate()
    desde_dias, hasta_dias = reporte.rango_por_defecto
    return {
        'tipo': TipoVehiculo.objects.order_by('nombre').first(),
        'vehiculo': (Vehiculo.objects.filter(viajes__isnull=False).order_by('patente').first()
                     or Vehiculo.objects.order_by('patente').first()),
        'conductor': (Conductor.objects.filter(viajes__isnull=False).order_by('nombre').first()
                      or Conductor.objects.order_by('nombre').first()),
        'desde': hoy + timedelta(days=desde_dias),
        'hasta': hoy + timedelta(days=hasta_dias),
        'anio': hoy.year,
    }


def _anios_disponibles():
    """Años entre el primer y el último viaje registrado (para el selector)."""
    rango = Viaje.objects.aggregate(primero=Min('fecha_salida'), ultimo=Max('fecha_salida'))
    if not rango['primero']:
        return [timezone.localdate().year]
    return list(range(timezone.localtime(rango['primero']).year,
                      timezone.localtime(rango['ultimo']).year + 1))


@login_required
def reporte_detalle(request, numero):
    reporte = REPORTES.get(numero)
    if reporte is None:
        raise Http404('Reporte no encontrado')

    iniciales = _valores_por_defecto(reporte)
    if request.GET:
        form = ParametrosReporte(request.GET, initial=iniciales)
        enviados = form.cleaned_data if form.is_valid() else None
    else:
        form = ParametrosReporte(initial=iniciales)
        enviados = {}

    resultado = None
    consultas = []
    if enviados is not None:
        # Parámetros enviados por el usuario o, si no los hay, los valores por defecto.
        p = {clave: enviados.get(clave) or valor for clave, valor in iniciales.items()}
        # Las fechas se convierten a datetimes locales [desde 00:00, hasta+1 día 00:00)
        # para que el día final quede incluido completo.
        p['inicio'] = timezone.make_aware(datetime.combine(p['desde'], time.min))
        p['fin'] = timezone.make_aware(datetime.combine(p['hasta'] + timedelta(days=1), time.min))

        faltan_datos = any(p.get(nombre) is None for nombre in reporte.parametros
                           if nombre in ('tipo', 'vehiculo', 'conductor'))
        if not faltan_datos:
            # Se capturan las sentencias SQL que genera el ORM como evidencia.
            with CaptureQueriesContext(connection) as capturadas:
                resultado = reporte.funcion(p)
            consultas = [q['sql'] for q in capturadas.captured_queries]

    campos_visibles = []
    for nombre in reporte.parametros:
        campos_visibles += ['desde', 'hasta'] if nombre == 'rango' else [nombre]

    return render(request, 'courier/reportes/detalle.html', {
        'titulo': f'Reporte {numero}',
        'reporte': reporte,
        'form': form,
        'campos_visibles': [form[nombre] for nombre in campos_visibles],
        'resultado': resultado,
        'grafico': graficos.desde_resultado(resultado.grafico) if resultado else None,
        'codigo': inspect.getsource(reporte.funcion),
        'consultas': consultas,
        'anios': _anios_disponibles(),
        'anterior': REPORTES.get(numero - 1),
        'siguiente': REPORTES.get(numero + 1),
    })
