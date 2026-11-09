"""Mantenedores (CRUD) de las entidades del caso Music Pro Courier.

Todas las vistas están protegidas con ``@login_required``: si alguien escribe
la URL sin haber iniciado sesión, Django lo redirige al login.
Las consultas y modificaciones se realizan con el ORM de Django.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from ..forms import (
    ConductorForm, EnvioForm, IncidenciaForm, NotificacionForm, PaqueteForm,
    SucursalForm, TipoVehiculoForm, VehiculoForm, ViajeForm,
)
from ..models import (
    Conductor, Envio, Incidencia, Notificacion, Paquete, Sucursal,
    TipoVehiculo, Vehiculo, Viaje,
)
from .utils import eliminar_crud, formulario_crud, paginar, parametros_sin_pagina

__all__ = [
    'sucursal_lista', 'sucursal_crear', 'sucursal_editar', 'sucursal_eliminar',
    'paquete_lista', 'paquete_crear', 'paquete_editar', 'paquete_eliminar',
    'envio_lista', 'envio_crear', 'envio_editar', 'envio_eliminar', 'envio_detalle',
    'incidencia_lista', 'incidencia_crear', 'incidencia_editar', 'incidencia_eliminar',
    'notificacion_lista', 'notificacion_crear', 'notificacion_editar', 'notificacion_eliminar',
    'tipo_vehiculo_lista', 'tipo_vehiculo_crear', 'tipo_vehiculo_editar', 'tipo_vehiculo_eliminar',
    'vehiculo_lista', 'vehiculo_crear', 'vehiculo_editar', 'vehiculo_eliminar',
    'conductor_lista', 'conductor_crear', 'conductor_editar', 'conductor_eliminar',
    'viaje_lista', 'viaje_crear', 'viaje_editar', 'viaje_eliminar', 'viaje_detalle',
]


def _contexto_lista(request, titulo, pagina, **extra):
    contexto = {
        'titulo': titulo,
        'pagina': pagina,
        'q': request.GET.get('q', '').strip(),
        'params': parametros_sin_pagina(request),
    }
    contexto.update(extra)
    return contexto


# ===========================================================================
# Sucursales
# ===========================================================================


@login_required
def sucursal_lista(request):
    sucursales = Sucursal.objects.annotate(
        envios_enviados=Count('envios_origen', distinct=True),
        envios_recibidos=Count('envios_destino', distinct=True),
    ).order_by('nombre')
    q = request.GET.get('q', '').strip()
    if q:
        sucursales = sucursales.filter(Q(nombre__icontains=q) | Q(ciudad__icontains=q) | Q(direccion__icontains=q))
    estado = request.GET.get('estado', '')
    if estado in ('activa', 'inactiva'):
        sucursales = sucursales.filter(activa=(estado == 'activa'))
    return render(request, 'courier/gestion/sucursales.html',
                  _contexto_lista(request, 'Sucursales', paginar(request, sucursales), estado=estado))


@login_required
def sucursal_crear(request):
    return formulario_crud(request, form_class=SucursalForm, titulo='Nueva sucursal',
                           url_lista='courier:sucursal_lista', icono='fa-store')


@login_required
def sucursal_editar(request, pk):
    return formulario_crud(request, form_class=SucursalForm, titulo='Editar sucursal',
                           url_lista='courier:sucursal_lista', icono='fa-store',
                           instancia=get_object_or_404(Sucursal, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def sucursal_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Sucursal, pk=pk),
                         url_lista='courier:sucursal_lista', titulo='Eliminar sucursal',
                         advertencia='Si la sucursal tiene envíos asociados no podrá eliminarse; '
                                     'en ese caso márquela como inactiva.')


# ===========================================================================
# Paquetes
# ===========================================================================


@login_required
def paquete_lista(request):
    paquetes = Paquete.objects.annotate(total_envios=Count('envios')).order_by('-fecha_creacion')
    q = request.GET.get('q', '').strip()
    if q:
        paquetes = paquetes.filter(Q(codigo__icontains=q) | Q(descripcion__icontains=q))
    estado = request.GET.get('estado', '')
    if estado:
        paquetes = paquetes.filter(estado=estado)
    return render(request, 'courier/gestion/paquetes.html', _contexto_lista(
        request, 'Paquetes', paginar(request, paquetes), estado=estado, estados=Paquete.ESTADO_CHOICES))


@login_required
def paquete_crear(request):
    return formulario_crud(request, form_class=PaqueteForm, titulo='Nuevo paquete',
                           url_lista='courier:paquete_lista', icono='fa-box')


@login_required
def paquete_editar(request, pk):
    return formulario_crud(request, form_class=PaqueteForm, titulo='Editar paquete',
                           url_lista='courier:paquete_lista', icono='fa-box',
                           instancia=get_object_or_404(Paquete, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def paquete_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Paquete, pk=pk),
                         url_lista='courier:paquete_lista', titulo='Eliminar paquete')


# ===========================================================================
# Envíos
# ===========================================================================


@login_required
def envio_lista(request):
    envios = Envio.objects.select_related(
        'sucursal_origen', 'sucursal_destino', 'paquete', 'viaje__vehiculo', 'viaje__conductor',
    ).order_by('-id')
    q = request.GET.get('q', '').strip()
    if q:
        envios = envios.filter(
            Q(numero_envio__icontains=q) | Q(paquete__descripcion__icontains=q)
            | Q(sucursal_destino__ciudad__icontains=q) | Q(viaje__conductor__nombre__icontains=q)
        )
    estado = request.GET.get('estado', '')
    if estado:
        envios = envios.filter(estado=estado)
    prioridad = request.GET.get('prioridad', '')
    if prioridad:
        envios = envios.filter(prioridad=prioridad)
    return render(request, 'courier/gestion/envios.html', _contexto_lista(
        request, 'Envíos', paginar(request, envios), estado=estado, prioridad=prioridad,
        estados=Envio.ESTADO_CHOICES, prioridades=Envio.PRIORIDAD_CHOICES))


def _registrar_creador(request):
    def asignar(envio):
        if envio.creado_por_id is None:
            envio.creado_por = request.user  # usuario identificado por la sesión
    return asignar


@login_required
def envio_crear(request):
    return formulario_crud(request, form_class=EnvioForm, titulo='Nuevo envío',
                           url_lista='courier:envio_lista', icono='fa-truck-fast',
                           antes_de_guardar=_registrar_creador(request))


@login_required
def envio_editar(request, pk):
    return formulario_crud(request, form_class=EnvioForm, titulo='Editar envío',
                           url_lista='courier:envio_lista', icono='fa-truck-fast',
                           instancia=get_object_or_404(Envio, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def envio_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Envio, pk=pk),
                         url_lista='courier:envio_lista', titulo='Eliminar envío',
                         advertencia='También se eliminarán sus incidencias y notificaciones.')


@login_required
def envio_detalle(request, pk):
    envio = get_object_or_404(
        Envio.objects.select_related('sucursal_origen', 'sucursal_destino', 'paquete', 'creado_por',
                                     'viaje__vehiculo__tipo_vehiculo', 'viaje__conductor'),
        pk=pk,
    )
    return render(request, 'courier/gestion/envio_detalle.html', {
        'titulo': f'Envío {envio.numero_envio}',
        'envio': envio,
        'incidencias': envio.incidencias.select_related('reportada_por'),
        'notificaciones': envio.notificaciones.all(),
    })


# ===========================================================================
# Incidencias
# ===========================================================================


@login_required
def incidencia_lista(request):
    incidencias = Incidencia.objects.select_related('envio', 'reportada_por').order_by('resuelta', '-fecha')
    q = request.GET.get('q', '').strip()
    if q:
        incidencias = incidencias.filter(Q(envio__numero_envio__icontains=q) | Q(descripcion__icontains=q))
    tipo = request.GET.get('tipo', '')
    if tipo:
        incidencias = incidencias.filter(tipo=tipo)
    estado = request.GET.get('estado', '')
    if estado in ('abierta', 'resuelta'):
        incidencias = incidencias.filter(resuelta=(estado == 'resuelta'))
    return render(request, 'courier/gestion/incidencias.html', _contexto_lista(
        request, 'Incidencias', paginar(request, incidencias), tipo=tipo, estado=estado,
        tipos=Incidencia.TIPO_CHOICES))


@login_required
def incidencia_crear(request):
    def asignar_autor(incidencia):
        incidencia.reportada_por = request.user

    return formulario_crud(request, form_class=IncidenciaForm, titulo='Nueva incidencia',
                           url_lista='courier:incidencia_lista', icono='fa-triangle-exclamation',
                           antes_de_guardar=asignar_autor)


@login_required
def incidencia_editar(request, pk):
    return formulario_crud(request, form_class=IncidenciaForm, titulo='Editar incidencia',
                           url_lista='courier:incidencia_lista', icono='fa-triangle-exclamation',
                           instancia=get_object_or_404(Incidencia, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def incidencia_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Incidencia, pk=pk),
                         url_lista='courier:incidencia_lista', titulo='Eliminar incidencia')


# ===========================================================================
# Notificaciones
# ===========================================================================


@login_required
def notificacion_lista(request):
    notificaciones = Notificacion.objects.select_related('envio').order_by('-fecha_envio')
    q = request.GET.get('q', '').strip()
    if q:
        notificaciones = notificaciones.filter(Q(envio__numero_envio__icontains=q) | Q(mensaje__icontains=q))
    canal = request.GET.get('canal', '')
    if canal:
        notificaciones = notificaciones.filter(canal=canal)
    return render(request, 'courier/gestion/notificaciones.html', _contexto_lista(
        request, 'Notificaciones', paginar(request, notificaciones), canal=canal,
        canales=Notificacion.CANAL_CHOICES))


@login_required
def notificacion_crear(request):
    return formulario_crud(request, form_class=NotificacionForm, titulo='Nueva notificación',
                           url_lista='courier:notificacion_lista', icono='fa-bell')


@login_required
def notificacion_editar(request, pk):
    return formulario_crud(request, form_class=NotificacionForm, titulo='Editar notificación',
                           url_lista='courier:notificacion_lista', icono='fa-bell',
                           instancia=get_object_or_404(Notificacion, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def notificacion_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Notificacion, pk=pk),
                         url_lista='courier:notificacion_lista', titulo='Eliminar notificación')


# ===========================================================================
# Tipos de vehículo
# ===========================================================================


@login_required
def tipo_vehiculo_lista(request):
    tipos = TipoVehiculo.objects.annotate(total_vehiculos=Count('vehiculos')).order_by('nombre')
    q = request.GET.get('q', '').strip()
    if q:
        tipos = tipos.filter(nombre__icontains=q)
    return render(request, 'courier/gestion/tipos_vehiculo.html',
                  _contexto_lista(request, 'Tipos de vehículo', paginar(request, tipos)))


@login_required
def tipo_vehiculo_crear(request):
    return formulario_crud(request, form_class=TipoVehiculoForm, titulo='Nuevo tipo de vehículo',
                           url_lista='courier:tipo_vehiculo_lista', icono='fa-layer-group')


@login_required
def tipo_vehiculo_editar(request, pk):
    return formulario_crud(request, form_class=TipoVehiculoForm, titulo='Editar tipo de vehículo',
                           url_lista='courier:tipo_vehiculo_lista', icono='fa-layer-group',
                           instancia=get_object_or_404(TipoVehiculo, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def tipo_vehiculo_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(TipoVehiculo, pk=pk),
                         url_lista='courier:tipo_vehiculo_lista', titulo='Eliminar tipo de vehículo',
                         advertencia='No se puede eliminar un tipo que tenga vehículos asociados.')


# ===========================================================================
# Vehículos
# ===========================================================================


@login_required
def vehiculo_lista(request):
    vehiculos = (Vehiculo.objects.select_related('tipo_vehiculo')
                 .annotate(total_viajes=Count('viajes')).order_by('patente'))
    q = request.GET.get('q', '').strip()
    if q:
        vehiculos = vehiculos.filter(Q(patente__icontains=q) | Q(marca__icontains=q) | Q(modelo__icontains=q))
    tipo = request.GET.get('tipo', '')
    if tipo.isdigit():
        vehiculos = vehiculos.filter(tipo_vehiculo_id=int(tipo))
    disponible = request.GET.get('disponible', '')
    if disponible in ('si', 'no'):
        vehiculos = vehiculos.filter(disponible=(disponible == 'si'))
    return render(request, 'courier/gestion/vehiculos.html', _contexto_lista(
        request, 'Vehículos', paginar(request, vehiculos), tipo=tipo, disponible=disponible,
        tipos=TipoVehiculo.objects.all()))


@login_required
def vehiculo_crear(request):
    return formulario_crud(request, form_class=VehiculoForm, titulo='Nuevo vehículo',
                           url_lista='courier:vehiculo_lista', icono='fa-truck')


@login_required
def vehiculo_editar(request, pk):
    return formulario_crud(request, form_class=VehiculoForm, titulo='Editar vehículo',
                           url_lista='courier:vehiculo_lista', icono='fa-truck',
                           instancia=get_object_or_404(Vehiculo, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def vehiculo_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Vehiculo, pk=pk),
                         url_lista='courier:vehiculo_lista', titulo='Eliminar vehículo',
                         advertencia='Un vehículo con viajes registrados no puede eliminarse; '
                                     'cámbielo a "Fuera de servicio".')


# ===========================================================================
# Conductores
# ===========================================================================


@login_required
def conductor_lista(request):
    conductores = Conductor.objects.annotate(
        total_viajes=Count('viajes'),
        viajes_finalizados=Count('viajes', filter=Q(viajes__estado='finalizado')),
    ).order_by('nombre')
    q = request.GET.get('q', '').strip()
    if q:
        conductores = conductores.filter(Q(nombre__icontains=q) | Q(rut__icontains=q) | Q(licencia__icontains=q))
    estado = request.GET.get('estado', '')
    if estado in ('activo', 'inactivo'):
        conductores = conductores.filter(activo=(estado == 'activo'))
    return render(request, 'courier/gestion/conductores.html', _contexto_lista(
        request, 'Conductores', paginar(request, conductores), estado=estado))


@login_required
def conductor_crear(request):
    return formulario_crud(request, form_class=ConductorForm, titulo='Nuevo conductor',
                           url_lista='courier:conductor_lista', icono='fa-id-card')


@login_required
def conductor_editar(request, pk):
    return formulario_crud(request, form_class=ConductorForm, titulo='Editar conductor',
                           url_lista='courier:conductor_lista', icono='fa-id-card',
                           instancia=get_object_or_404(Conductor, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def conductor_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Conductor, pk=pk),
                         url_lista='courier:conductor_lista', titulo='Eliminar conductor',
                         advertencia='Un conductor con viajes registrados no puede eliminarse; '
                                     'márquelo como inactivo.')


# ===========================================================================
# Viajes
# ===========================================================================


@login_required
def viaje_lista(request):
    viajes = (Viaje.objects.select_related('vehiculo__tipo_vehiculo', 'conductor')
              .annotate(total_envios=Count('envios')).order_by('-fecha_salida'))
    q = request.GET.get('q', '').strip()
    if q:
        viajes = viajes.filter(
            Q(origen__icontains=q) | Q(destino__icontains=q)
            | Q(vehiculo__patente__icontains=q) | Q(conductor__nombre__icontains=q)
        )
    estado = request.GET.get('estado', '')
    if estado:
        viajes = viajes.filter(estado=estado)
    return render(request, 'courier/gestion/viajes.html', _contexto_lista(
        request, 'Viajes', paginar(request, viajes), estado=estado, estados=Viaje.ESTADO_CHOICES))


def _contexto_viaje():
    ciudades = Sucursal.objects.order_by('ciudad').values_list('ciudad', flat=True).distinct()
    return {'ciudades': list(ciudades)}


@login_required
def viaje_crear(request):
    return formulario_crud(request, form_class=ViajeForm, titulo='Nuevo viaje',
                           url_lista='courier:viaje_lista', icono='fa-route', extra=_contexto_viaje())


@login_required
def viaje_editar(request, pk):
    return formulario_crud(request, form_class=ViajeForm, titulo='Editar viaje',
                           url_lista='courier:viaje_lista', icono='fa-route', extra=_contexto_viaje(),
                           instancia=get_object_or_404(Viaje, pk=pk))


@login_required
@require_http_methods(['GET', 'POST'])
def viaje_eliminar(request, pk):
    return eliminar_crud(request, instancia=get_object_or_404(Viaje, pk=pk),
                         url_lista='courier:viaje_lista', titulo='Eliminar viaje',
                         advertencia='Los envíos asociados quedarán sin viaje asignado.')


@login_required
def viaje_detalle(request, pk):
    viaje = get_object_or_404(Viaje.objects.select_related('vehiculo__tipo_vehiculo', 'conductor'), pk=pk)
    return render(request, 'courier/gestion/viaje_detalle.html', {
        'titulo': f'Viaje {viaje.codigo}',
        'viaje': viaje,
        'envios': viaje.envios.select_related('paquete', 'sucursal_destino'),
    })
