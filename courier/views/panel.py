"""Panel principal, seguimiento, perfil y endpoints JSON (todos protegidos)."""
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Case, Count, F, IntegerField, Q, Sum, Value, When
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .. import graficos
from ..models import Conductor, Envio, Incidencia, Paquete, Sucursal, TipoVehiculo, Vehiculo, Viaje
from ..reportes import MESES


# Orden lógico de prioridad (urgente primero) en vez del orden alfabético.
ORDEN_PRIORIDAD = Case(
    When(prioridad='urgente', then=Value(0)),
    When(prioridad='alta', then=Value(1)),
    When(prioridad='media', then=Value(2)),
    default=Value(3),
    output_field=IntegerField(),
)


def _inicio_de_mes(fecha, meses_atras=0):
    """Primer instante (con zona horaria local) del mes ``meses_atras`` antes de ``fecha``."""
    anio, mes = fecha.year, fecha.month - meses_atras
    while mes <= 0:
        mes += 12
        anio -= 1
    while mes > 12:
        mes -= 12
        anio += 1
    return timezone.make_aware(datetime(anio, mes, 1))


def _medianoche(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


def calcular_kpis():
    """Indicadores generales (sin período) usados por el endpoint JSON."""
    envios = Envio.objects.aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='pendiente')),
        en_ruta=Count('id', filter=Q(estado='en_ruta')),
        entregados=Count('id', filter=Q(estado='entregado')),
        a_tiempo=Count('id', filter=Q(estado='entregado', fecha_entrega_real__lte=F('fecha_entrega_estimada'))),
    )
    viajes = Viaje.objects.aggregate(
        total=Count('id'),
        programados=Count('id', filter=Q(estado='programado')),
        en_curso=Count('id', filter=Q(estado='en_curso')),
        finalizados=Count('id', filter=Q(estado='finalizado')),
    )
    return {
        'envios': envios,
        'viajes': viajes,
        'cumplimiento_sla': round(envios['a_tiempo'] * 100 / envios['entregados'], 1) if envios['entregados'] else 0,
        'valor_declarado_total': Paquete.objects.aggregate(total=Sum('valor_declarado'))['total'] or 0,
        'sucursales_activas': Sucursal.objects.filter(activa=True).count(),
        'incidencias_abiertas': Incidencia.objects.filter(resuelta=False).count(),
        'vehiculos': Vehiculo.objects.count(),
        'conductores_activos': Conductor.objects.filter(activo=True).count(),
    }


# ---------------------------------------------------------------------------
# Panel de control con selector de período
# ---------------------------------------------------------------------------

PERIODOS = {
    '7': {'nombre': '7 días', 'tramo': 'día', 'cantidad': 7},
    '30': {'nombre': '30 días', 'tramo': 'día', 'cantidad': 30},
    '90': {'nombre': '90 días', 'tramo': 'semana', 'cantidad': 13},
    '365': {'nombre': '12 meses', 'tramo': 'mes', 'cantidad': 12},
}
PERIODO_POR_DEFECTO = '30'
ESTADOS_VALIDOS = ['programado', 'en_curso', 'finalizado']  # todo menos cancelado


def tramos_del_periodo(clave):
    """Divide el período en tramos (días, semanas o meses) que terminan hoy.

    Devuelve una lista de (etiqueta, inicio, fin) con datetimes locales. Se
    calculan en Python para no depender de las tablas de zona horaria de MySQL.
    """
    periodo = PERIODOS[clave]
    hoy = timezone.localdate()
    tramos = []
    for i in range(periodo['cantidad'] - 1, -1, -1):
        if periodo['tramo'] == 'día':
            dia = hoy - timedelta(days=i)
            tramos.append((dia.strftime('%d/%m'), _medianoche(dia), _medianoche(dia + timedelta(days=1))))
        elif periodo['tramo'] == 'semana':
            ultimo = hoy - timedelta(days=7 * i)
            primero = ultimo - timedelta(days=6)
            tramos.append((primero.strftime('%d/%m'), _medianoche(primero),
                           _medianoche(ultimo + timedelta(days=1))))
        else:
            inicio_mes = _inicio_de_mes(hoy, i)
            tramos.append((f'{MESES[inicio_mes.month - 1]} {inicio_mes:%y}', inicio_mes, _inicio_de_mes(hoy, i - 1)))
    return tramos


def contar_por_tramos(queryset, campo, tramos):
    """Cuenta registros por tramo en UNA consulta (agregación condicional)."""
    conteos = queryset.aggregate(**{
        f't{i}': Count('id', filter=Q(**{f'{campo}__gte': inicio, f'{campo}__lt': fin}))
        for i, (_, inicio, fin) in enumerate(tramos)
    })
    return [conteos[f't{i}'] for i in range(len(tramos))]


def _indicadores_envios(inicio, fin):
    datos = Envio.objects.filter(
        estado='entregado', fecha_entrega_real__gte=inicio, fecha_entrega_real__lt=fin,
    ).aggregate(
        entregados=Count('id'),
        a_tiempo=Count('id', filter=Q(fecha_entrega_real__lte=F('fecha_entrega_estimada'))),
        promedio=Avg(F('fecha_entrega_real') - F('fecha_despacho')),
    )
    datos['sla'] = round(datos['a_tiempo'] * 100 / datos['entregados'], 1) if datos['entregados'] else 0
    datos['horas'] = round(datos['promedio'].total_seconds() / 3600, 1) if datos['promedio'] else 0
    return datos


@login_required
def dashboard(request):
    clave = request.GET.get('periodo', PERIODO_POR_DEFECTO)
    if clave not in PERIODOS:
        clave = PERIODO_POR_DEFECTO
    tramos = tramos_del_periodo(clave)
    inicio, fin = tramos[0][1], tramos[-1][2]
    inicio_anterior = inicio - (fin - inicio)  # período anterior de igual duración
    ahora = timezone.now()

    en_periodo = Q(fecha_salida__gte=inicio, fecha_salida__lt=fin)
    en_anterior = Q(fecha_salida__gte=inicio_anterior, fecha_salida__lt=inicio)
    viajes_validos = Viaje.objects.filter(estado__in=ESTADOS_VALIDOS)

    # --- Indicadores (valor actual vs período anterior) ---
    finalizados = Viaje.objects.filter(estado='finalizado')
    realizados = finalizados.filter(en_periodo).count()
    realizados_antes = finalizados.filter(en_anterior).count()
    envios = _indicadores_envios(inicio, fin)
    envios_antes = _indicadores_envios(inicio_anterior, inicio)
    incidencias = Incidencia.objects.filter(fecha__gte=inicio, fecha__lt=fin).count()
    incidencias_antes = Incidencia.objects.filter(fecha__gte=inicio_anterior, fecha__lt=inicio).count()
    flota = Vehiculo.objects.aggregate(total=Count('id'), disponibles=Count('id', filter=Q(disponible=True)),
                                       en_mantencion=Count('id', filter=Q(estado='mantencion')))
    # distinct=True: el JOIN con viajes repite cada conductor una vez por viaje.
    conductores = Conductor.objects.aggregate(
        activos=Count('id', filter=Q(activo=True), distinct=True),
        con_viajes=Count('id', filter=Q(viajes__fecha_salida__gte=inicio, viajes__fecha_salida__lt=fin), distinct=True),
    )

    indicadores = [
        {'etiqueta': 'Viajes realizados', 'valor': realizados,
         'variacion': graficos.variacion(realizados, realizados_antes),
         'linea': graficos.sparkline(contar_por_tramos(finalizados, 'fecha_salida', tramos))},
        {'etiqueta': 'Viajes programados', 'valor': Viaje.objects.filter(estado='programado').count(),
         'detalle': 'pendientes de ejecución'},
        {'etiqueta': 'Envíos entregados', 'valor': envios['entregados'],
         'variacion': graficos.variacion(envios['entregados'], envios_antes['entregados']),
         'linea': graficos.sparkline(contar_por_tramos(
             Envio.objects.filter(estado='entregado'), 'fecha_entrega_real', tramos))},
        {'etiqueta': 'Entregas a tiempo', 'valor': f"{graficos.formato_numero(envios['sla'])} %",
         'variacion': graficos.variacion(envios['sla'], envios_antes['sla'], en_puntos=True),
         'detalle': f"{envios['a_tiempo']} de {envios['entregados']} entregas"},
        {'etiqueta': 'Vehículos', 'valor': flota['total'],
         'detalle': f"{flota['disponibles']} disponibles · {flota['en_mantencion']} en mantención"},
        {'etiqueta': 'Conductores activos', 'valor': conductores['activos'],
         'detalle': f"{conductores['con_viajes']} con viajes en el período"},
        {'etiqueta': 'Horas promedio de entrega', 'valor': graficos.formato_numero(envios['horas']),
         'variacion': graficos.variacion(envios['horas'], envios_antes['horas'], mayor_es_mejor=False)},
        {'etiqueta': 'Incidencias registradas', 'valor': incidencias,
         'variacion': graficos.variacion(incidencias, incidencias_antes, mayor_es_mejor=False),
         'detalle': f"{Incidencia.objects.filter(resuelta=False).count()} abiertas en total"},
    ]

    # --- Gráfico 1: reparto de viajes por estado (incluye los programados a futuro) ---
    conteo_estados = dict(Viaje.objects.filter(fecha_salida__gte=inicio)
                          .values_list('estado').annotate(total=Count('id')))
    por_estado = graficos.barra_segmentada(
        [nombre for _, nombre in Viaje.ESTADO_CHOICES],
        [conteo_estados.get(c, 0) for c, _ in Viaje.ESTADO_CHOICES],
        [c for c, _ in Viaje.ESTADO_CHOICES],
    )

    # --- Gráfico 2: viajes por tipo de vehículo (incluye tipos sin viajes) ---
    tipos = TipoVehiculo.objects.annotate(total=Count('vehiculos__viajes', filter=Q(
        vehiculos__viajes__fecha_salida__gte=inicio,
        vehiculos__viajes__fecha_salida__lt=fin,
        vehiculos__viajes__estado__in=ESTADOS_VALIDOS,
    )))
    por_tipo = graficos.barras_ranking([t.nombre for t in tipos], [t.total for t in tipos])

    # --- Gráfico 3: evolución de viajes por tramo ---
    evolucion = graficos.columnas([t[0] for t in tramos], contar_por_tramos(viajes_validos, 'fecha_salida', tramos),
                                  maximo_etiquetas=12 if PERIODOS[clave]['tramo'] == 'mes' else 8)

    # --- Ranking de conductores del período ---
    total_periodo = viajes_validos.filter(en_periodo).count()
    ranking = (Conductor.objects
               .annotate(total=Count('viajes', filter=Q(viajes__fecha_salida__gte=inicio,
                                                        viajes__fecha_salida__lt=fin,
                                                        viajes__estado__in=ESTADOS_VALIDOS)))
               .filter(total__gt=0).order_by('-total', 'nombre')[:5])
    top_conductores = graficos.barras_ranking([c.nombre for c in ranking], [c.total for c in ranking],
                                              detalles=[c.rut for c in ranking], total=total_periodo)

    ultimos_viajes = (Viaje.objects.select_related('vehiculo__tipo_vehiculo', 'conductor')
                      .filter(fecha_salida__lte=ahora).order_by('-fecha_salida')[:6])
    envios_activos = (Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete')
                      .filter(estado__in=['pendiente', 'en_ruta'])
                      .annotate(orden_prioridad=ORDEN_PRIORIDAD)
                      .order_by('estado', 'orden_prioridad', '-id')[:6])  # 'en_ruta' antes que 'pendiente'
    incidencias_abiertas = Incidencia.objects.select_related('envio').filter(resuelta=False)[:5]

    return render(request, 'courier/panel/dashboard.html', {
        'titulo': 'Panel de control',
        'periodos': [(c, p['nombre']) for c, p in PERIODOS.items()],
        'periodo': clave,
        'periodo_info': PERIODOS[clave],
        'inicio': inicio,
        'indicadores': indicadores,
        'por_estado': por_estado,
        'por_tipo': por_tipo,
        'evolucion': evolucion,
        'top_conductores': top_conductores,
        'total_periodo': total_periodo,
        'ultimos_viajes': ultimos_viajes,
        'envios_activos': envios_activos,
        'incidencias': incidencias_abiertas,
    })


@login_required
def seguimiento(request):
    """Busca un envío por número y muestra los envíos en curso."""
    numero = request.GET.get('numero', '').strip().upper()
    if numero:
        envio = Envio.objects.filter(numero_envio=numero).first()
        if envio:
            return redirect('courier:envio_detalle', pk=envio.pk)
        messages.warning(request, f'No existe un envío con número {numero}.')

    en_curso = (Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete',
                                             'viaje__conductor', 'viaje__vehiculo')
                .filter(estado__in=['pendiente', 'en_ruta'])
                .order_by('-progreso'))
    return render(request, 'courier/panel/seguimiento.html', {
        'titulo': 'Seguimiento de envíos',
        'envios': en_curso,
        'numero': numero,
    })


@login_required
def perfil(request):
    """Muestra los datos del usuario autenticado obtenidos desde la sesión."""
    sesion = request.session
    inicio = parse_datetime(sesion['inicio_sesion']) if sesion.get('inicio_sesion') else None
    anterior = parse_datetime(sesion['acceso_anterior']) if sesion.get('acceso_anterior') else None
    return render(request, 'courier/panel/perfil.html', {
        'titulo': 'Mi perfil y sesión',
        'inicio_sesion': inicio,
        'acceso_anterior': anterior,
        'expira': sesion.get_expiry_date(),
        'expira_al_cerrar': sesion.get_expire_at_browser_close(),
        'grupos': request.user.groups.values_list('name', flat=True),
    })


# ---------------------------------------------------------------------------
# Endpoints JSON (de la Evaluación 1), ahora protegidos con @login_required
# ---------------------------------------------------------------------------


@login_required
def api_envios(request):
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete',
                                          'viaje__conductor', 'viaje__vehiculo')
    payload = [{
        'id': envio.id,
        'numero_envio': envio.numero_envio,
        'estado': envio.estado,
        'prioridad': envio.prioridad,
        'conductor': envio.viaje.conductor.nombre if envio.viaje else None,
        'patente_vehiculo': envio.viaje.vehiculo.patente if envio.viaje else None,
        'progreso': envio.progreso,
        'sucursal_origen': envio.sucursal_origen.ciudad,
        'sucursal_destino': envio.sucursal_destino.ciudad,
        'paquete': envio.paquete.descripcion,
        'fecha_entrega_estimada': envio.fecha_entrega_estimada.isoformat() if envio.fecha_entrega_estimada else None,
    } for envio in envios]
    return JsonResponse({'envios': payload})


@login_required
def api_sucursales(request):
    sucursales = list(Sucursal.objects.values('id', 'nombre', 'ciudad', 'direccion', 'latitud', 'longitud', 'activa'))
    return JsonResponse({'sucursales': sucursales})


@login_required
def api_kpis(request):
    kpis = calcular_kpis()
    kpis['valor_declarado_total'] = float(kpis['valor_declarado_total'])
    return JsonResponse({'kpis': kpis})
