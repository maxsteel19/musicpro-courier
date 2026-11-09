"""Panel principal, seguimiento, perfil y endpoints JSON (todos protegidos)."""
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Case, Count, F, IntegerField, Q, Sum, Value, When
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import Conductor, Envio, Incidencia, Paquete, Sucursal, Vehiculo, Viaje
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
    return timezone.make_aware(datetime(anio, mes, 1))


def calcular_kpis():
    """Indicadores del negocio calculados con agregaciones del ORM."""
    hoy = timezone.localdate()
    inicio_hoy = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
    fin_hoy = inicio_hoy + timedelta(days=1)

    envios = Envio.objects.aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='pendiente')),
        en_ruta=Count('id', filter=Q(estado='en_ruta')),
        entregados=Count('id', filter=Q(estado='entregado')),
        a_tiempo=Count('id', filter=Q(estado='entregado', fecha_entrega_real__lte=F('fecha_entrega_estimada'))),
        hoy=Count('id', filter=Q(fecha_despacho__gte=inicio_hoy, fecha_despacho__lt=fin_hoy)),
    )
    entrega = Envio.objects.filter(
        estado='entregado', fecha_entrega_real__isnull=False, fecha_despacho__isnull=False,
    ).aggregate(promedio=Avg(F('fecha_entrega_real') - F('fecha_despacho')))
    viajes = Viaje.objects.aggregate(
        total=Count('id'),
        programados=Count('id', filter=Q(estado='programado')),
        en_curso=Count('id', filter=Q(estado='en_curso')),
        finalizados=Count('id', filter=Q(estado='finalizado')),
    )
    promedio = entrega['promedio']
    return {
        'envios': envios,
        'viajes': viajes,
        'cumplimiento_sla': round(envios['a_tiempo'] * 100 / envios['entregados'], 1) if envios['entregados'] else 0,
        'horas_promedio_entrega': round(promedio.total_seconds() / 3600, 1) if promedio else 0,
        'valor_declarado_total': Paquete.objects.aggregate(total=Sum('valor_declarado'))['total'] or 0,
        'paquetes': Paquete.objects.count(),
        'sucursales_activas': Sucursal.objects.filter(activa=True).count(),
        'incidencias_abiertas': Incidencia.objects.filter(resuelta=False).count(),
        'vehiculos': Vehiculo.objects.count(),
        'vehiculos_disponibles': Vehiculo.objects.filter(disponible=True).count(),
        'conductores_activos': Conductor.objects.filter(activo=True).count(),
    }


@login_required
def dashboard(request):
    kpis = calcular_kpis()

    # Gráfico 1: viajes por estado
    conteo_estados = dict(Viaje.objects.values_list('estado').annotate(total=Count('id')))
    viajes_estado = {
        'etiquetas': [nombre for _, nombre in Viaje.ESTADO_CHOICES],
        'valores': [conteo_estados.get(clave, 0) for clave, _ in Viaje.ESTADO_CHOICES],
    }

    # Gráfico 2: viajes por tipo de vehículo
    por_tipo = (Viaje.objects.values('vehiculo__tipo_vehiculo__nombre')
                .annotate(total=Count('id')).order_by('-total'))
    viajes_tipo = {
        'etiquetas': [fila['vehiculo__tipo_vehiculo__nombre'] for fila in por_tipo],
        'valores': [fila['total'] for fila in por_tipo],
    }

    # Gráfico 3: viajes de los últimos 6 meses (agregación condicional)
    hoy = timezone.localdate()
    limites = [_inicio_de_mes(hoy, n) for n in range(5, -2, -1)]  # 7 límites = 6 meses
    conteo_meses = Viaje.objects.aggregate(**{
        f'm{i}': Count('id', filter=Q(fecha_salida__gte=limites[i], fecha_salida__lt=limites[i + 1]))
        for i in range(6)
    })
    viajes_mes = {
        'etiquetas': [f'{MESES[limites[i].month - 1]} {limites[i].year}' for i in range(6)],
        'valores': [conteo_meses[f'm{i}'] for i in range(6)],
    }

    top_conductores = (Conductor.objects.annotate(total=Count('viajes'))
                       .filter(total__gt=0).order_by('-total', 'nombre')[:5])
    ultimos_viajes = Viaje.objects.select_related('vehiculo__tipo_vehiculo', 'conductor').order_by('-fecha_salida')[:6]
    envios_activos = (Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete')
                      .filter(estado__in=['pendiente', 'en_ruta'])
                      .annotate(orden_prioridad=ORDEN_PRIORIDAD)
                      .order_by('estado', 'orden_prioridad', '-id')[:6])  # 'en_ruta' antes que 'pendiente'
    incidencias = Incidencia.objects.select_related('envio').filter(resuelta=False)[:5]

    return render(request, 'courier/panel/dashboard.html', {
        'titulo': 'Panel de control',
        'kpis': kpis,
        'viajes_estado': viajes_estado,
        'viajes_tipo': viajes_tipo,
        'viajes_mes': viajes_mes,
        'top_conductores': top_conductores,
        'total_viajes': kpis['viajes']['total'],
        'ultimos_viajes': ultimos_viajes,
        'envios_activos': envios_activos,
        'incidencias': incidencias,
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
