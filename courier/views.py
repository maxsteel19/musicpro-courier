from datetime import datetime

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render

from .models import Envio, Incidencia, Notificacion, Paquete, Sucursal


def _build_kpis(envios, paquetes, sucursales, incidencias):
    total_envios = envios.count()
    entregados = envios.filter(estado='entregado').count()
    transito = envios.filter(estado='en_ruta').count()
    pendientes = envios.filter(estado='pendiente').count()
    abiertas = incidencias.filter(resuelta=False).count()

    total_coste = paquetes.aggregate(total=Sum('valor_declarado'))['total'] or 0

    entregadas = envios.filter(
        estado='entregado',
        fecha_entrega_real__isnull=False,
        fecha_despacho__isnull=False,
    )
    horas_promedio = 0
    if entregadas.exists():
        diffs = []
        for envio in entregadas:
            if envio.fecha_despacho and envio.fecha_entrega_real:
                diff = envio.fecha_entrega_real - envio.fecha_despacho
                diffs.append(diff.total_seconds() / 3600)
        if diffs:
            horas_promedio = sum(diffs) / len(diffs)

    cumplimiento = 0
    if total_envios:
        cumplimiento = round((entregados / total_envios) * 100, 1)

    return {
        'envios_hoy': envios.filter(fecha_despacho__date=datetime.today().date()).count(),
        'envios_entregados': entregados,
        'envios_transito': transito,
        'envios_pendientes': pendientes,
        'tiempo_promedio_entrega': f'{horas_promedio:.1f} horas' if horas_promedio else '0.0 horas',
        'cumplimiento_sla': cumplimiento,
        'costo_total_transporte': int(total_coste),
        'paquetes_transportados': paquetes.count(),
        'sucursales_activas': sucursales.filter(activa=True).count(),
        'incidencias_abiertas': abiertas,
    }


def index(request):
    sucursales = Sucursal.objects.all()
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').order_by('-id')[:4]
    paquetes = Paquete.objects.all()
    incidencias = Incidencia.objects.select_related('envio').all()
    kpis = _build_kpis(Envio.objects.all(), paquetes, sucursales, incidencias)

    context = {
        'titulo': 'Courier (Proveedor - Cliente)',
        'empresa': 'Music Pro Tour',
        'ano': datetime.now().year,
        'sucursales': sucursales,
        'envios': envios,
        'kpis': kpis,
    }
    return render(request, 'courier/index.html', context)


def dashboard(request):
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').order_by('-id')
    incidencias = Incidencia.objects.select_related('envio').all()
    sucursales = Sucursal.objects.all()
    paquetes = Paquete.objects.all()
    kpis = _build_kpis(envios, paquetes, sucursales, incidencias)

    context = {
        'titulo': 'Dashboard de Courier',
        'empresa': 'Music Pro Tour',
        'envios': envios,
        'kpis': kpis,
        'incidencias': incidencias,
    }
    return render(request, 'courier/dashboard.html', context)


def seguimiento(request):
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').order_by('-id')
    envio_id = request.GET.get('envio_id')
    envio_seleccionado = envios.filter(id=envio_id).first() if envio_id else envios.first()
    if envio_seleccionado is None:
        envio_seleccionado = envios.first()

    context = {
        'titulo': 'Seguimiento en Tiempo Real',
        'empresa': 'Music Pro Tour',
        'envios': envios,
        'envio_seleccionado': envio_seleccionado,
    }
    return render(request, 'courier/seguimiento.html', context)


def sucursales_view(request):
    sucursales = Sucursal.objects.all()
    context = {
        'titulo': 'Sucursales y Franquicias',
        'empresa': 'Music Pro Tour',
        'sucursales': sucursales,
    }
    return render(request, 'courier/sucursales.html', context)


def envios_view(request):
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').order_by('-id')
    filtro_estado = request.GET.get('estado', 'todos')
    if filtro_estado != 'todos':
        envios = envios.filter(estado=filtro_estado)

    context = {
        'titulo': 'Gestión de Envíos',
        'empresa': 'Music Pro Tour',
        'envios': envios,
        'todos_envios': Envio.objects.all(),
        'filtro_estado': filtro_estado,
    }
    return render(request, 'courier/envios.html', context)


def paquetes_view(request):
    paquetes = Paquete.objects.all().order_by('-id')
    context = {
        'titulo': 'Gestión de Paquetes',
        'empresa': 'Music Pro Tour',
        'paquetes': paquetes,
    }
    return render(request, 'courier/paquetes.html', context)


def incidencias_view(request):
    incidencias = Incidencia.objects.select_related('envio').all().order_by('-id')
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').all()
    context = {
        'titulo': 'Incidencias',
        'empresa': 'Music Pro Tour',
        'incidencias': incidencias,
        'envios': envios,
    }
    return render(request, 'courier/incidencias.html', context)


def reportes_view(request):
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').order_by('-id')
    paquetes = Paquete.objects.all()
    sucursales = Sucursal.objects.all()
    incidencias = Incidencia.objects.select_related('envio').all()
    kpis = _build_kpis(envios, paquetes, sucursales, incidencias)

    context = {
        'titulo': 'Reportes y KPIs',
        'empresa': 'Music Pro Tour',
        'kpis': kpis,
        'envios': envios,
        'sucursales': sucursales,
        'paquetes': paquetes,
    }
    return render(request, 'courier/reportes.html', context)


def notificaciones_view(request):
    notificaciones = Notificacion.objects.select_related('envio').all().order_by('-id')
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').all()
    context = {
        'titulo': 'Notificaciones Multicanal',
        'empresa': 'Music Pro Tour',
        'notificaciones': notificaciones,
        'envios': envios,
    }
    return render(request, 'courier/notificaciones.html', context)


def api_envios(request):
    envios = Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete').all()
    payload = []
    for envio in envios:
        payload.append({
            'id': envio.id,
            'numero_envio': envio.numero_envio,
            'estado': envio.estado,
            'prioridad': envio.prioridad,
            'conductor': envio.conductor,
            'patente_vehiculo': envio.patente_vehiculo,
            'progreso': envio.progreso,
            'sucursal_origen': envio.sucursal_origen.ciudad,
            'sucursal_destino': envio.sucursal_destino.ciudad,
            'paquete': envio.paquete.descripcion,
            'fecha_entrega_estimada': envio.fecha_entrega_estimada.isoformat() if envio.fecha_entrega_estimada else None,
        })
    return JsonResponse({'envios': payload}, safe=False)


def api_sucursales(request):
    sucursales = list(Sucursal.objects.values('id', 'nombre', 'ciudad', 'direccion', 'latitud', 'longitud', 'activa'))
    return JsonResponse({'sucursales': sucursales}, safe=False)


def api_kpis(request):
    envios = Envio.objects.all()
    paquetes = Paquete.objects.all()
    sucursales = Sucursal.objects.all()
    incidencias = Incidencia.objects.all()
    return JsonResponse({'kpis': _build_kpis(envios, paquetes, sucursales, incidencias)})
