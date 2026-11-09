"""Evaluación 3 - Parte 2: consultas con Django ORM (proyecto Transporte).

Cada función responde una de las 20 preguntas del informe usando
**exclusivamente el ORM de Django** (sin SQL escrito a mano) y devuelve un
``Resultado`` con columnas y filas listas para mostrarse en la página de
reportes. La página muestra además el código fuente de cada función como
evidencia de la consulta ejecutada.

Parámetros disponibles (``p``): ``tipo``, ``vehiculo``, ``conductor``,
``inicio``/``fin`` (datetimes con zona horaria) y ``anio``.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from .models import Conductor, TipoVehiculo, Vehiculo, Viaje

ESTADOS_VIAJE = dict(Viaje.ESTADO_CHOICES)
MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


@dataclass
class Resultado:
    columnas: list
    filas: list
    resumen: str = ''
    # {'tipo': 'segmentos' | 'ranking' | 'columnas', 'etiquetas': [...], 'valores': [...]}
    grafico: dict = field(default_factory=dict)


@dataclass
class Reporte:
    numero: int
    nivel: str
    pregunta: str
    funcion: object
    parametros: tuple = ()
    # Rango por defecto, en días relativos a hoy: (desde, hasta)
    rango_por_defecto: tuple = (-30, 0)


REPORTES = {}


def reporte(numero, nivel, pregunta, parametros=(), rango_por_defecto=(-30, 0)):
    """Registra una función como reporte del informe."""

    def registrar(funcion):
        REPORTES[numero] = Reporte(numero, nivel, pregunta, funcion, parametros, rango_por_defecto)
        return funcion

    return registrar


# ---------------------------------------------------------------------------
# Funciones auxiliares (formato de datos, no consultan la base de datos)
# ---------------------------------------------------------------------------


def _fecha(valor):
    return timezone.localtime(valor).strftime('%d/%m/%Y %H:%M') if valor else '—'


def _duracion(td):
    if td is None:
        return '—'
    total_minutos = int(td.total_seconds() // 60)
    horas, minutos = divmod(total_minutos, 60)
    return f'{horas} h {minutos:02d} min'


def _filas_viajes(viajes):
    return [
        [v.codigo, v.vehiculo.patente, v.conductor.nombre, v.origen, v.destino,
         _fecha(v.fecha_salida), _fecha(v.fecha_llegada), v.get_estado_display()]
        for v in viajes
    ]


COLUMNAS_VIAJES = ['N.º viaje', 'Vehículo', 'Conductor', 'Origen', 'Destino', 'Salida', 'Llegada', 'Estado']
COLUMNAS_VEHICULOS = ['Patente', 'Tipo', 'Marca', 'Modelo', 'Año', 'Estado', 'Disponible']


def _filas_vehiculos(vehiculos):
    return [
        [v.patente, v.tipo_vehiculo.nombre, v.marca, v.modelo, v.anio,
         v.get_estado_display(), 'Sí' if v.disponible else 'No']
        for v in vehiculos
    ]


def _porcentaje(parte, total):
    return round(parte * 100 / total, 1) if total else 0


# ===========================================================================
# Nivel básico
# ===========================================================================


@reporte(1, 'Básico', '¿Cuáles son todos los vehículos registrados en el sistema?')
def vehiculos_registrados(p):
    vehiculos = Vehiculo.objects.select_related('tipo_vehiculo').order_by('patente')
    return Resultado(COLUMNAS_VEHICULOS, _filas_vehiculos(vehiculos),
                     f'{len(vehiculos)} vehículos registrados.')


@reporte(2, 'Básico', '¿Qué vehículos pertenecen a un tipo seleccionado?', parametros=('tipo',))
def vehiculos_por_tipo(p):
    vehiculos = (Vehiculo.objects.select_related('tipo_vehiculo')
                 .filter(tipo_vehiculo=p['tipo'])
                 .order_by('patente'))
    return Resultado(COLUMNAS_VEHICULOS, _filas_vehiculos(vehiculos),
                     f'{len(vehiculos)} vehículos del tipo "{p["tipo"]}".')


@reporte(3, 'Básico', '¿Cuáles son los vehículos que se encuentran disponibles?')
def vehiculos_disponibles(p):
    vehiculos = (Vehiculo.objects.select_related('tipo_vehiculo')
                 .filter(disponible=True)
                 .order_by('tipo_vehiculo__nombre', 'patente'))
    return Resultado(COLUMNAS_VEHICULOS, _filas_vehiculos(vehiculos),
                     f'{len(vehiculos)} vehículos disponibles.')


@reporte(4, 'Básico', '¿Cuáles son los 10 vehículos más antiguos de la empresa?')
def vehiculos_mas_antiguos(p):
    vehiculos = Vehiculo.objects.select_related('tipo_vehiculo').order_by('anio', 'patente')[:10]
    anio = timezone.localdate().year
    filas = [fila + [f'{anio - v.anio} años'] for fila, v in zip(_filas_vehiculos(vehiculos), vehiculos)]
    return Resultado(COLUMNAS_VEHICULOS + ['Antigüedad'], filas)


@reporte(5, 'Básico', '¿Cuántos conductores están registrados en el sistema?')
def total_conductores(p):
    totales = Conductor.objects.aggregate(
        total=Count('id'),
        activos=Count('id', filter=Q(activo=True)),
        inactivos=Count('id', filter=Q(activo=False)),
    )
    filas = [['Total registrados', totales['total']],
             ['Activos', totales['activos']],
             ['Inactivos', totales['inactivos']]]
    return Resultado(['Indicador', 'Cantidad'], filas,
                     f'Hay {totales["total"]} conductores registrados.')


# ===========================================================================
# Nivel intermedio
# ===========================================================================


@reporte(6, 'Intermedio', '¿Cuáles son los viajes realizados por un vehículo específico?',
         parametros=('vehiculo',))
def viajes_por_vehiculo(p):
    viajes = (Viaje.objects.select_related('vehiculo', 'conductor')
              .filter(vehiculo=p['vehiculo'])
              .order_by('-fecha_salida'))
    return Resultado(COLUMNAS_VIAJES, _filas_viajes(viajes),
                     f'{len(viajes)} viajes del vehículo {p["vehiculo"].patente}.')


@reporte(7, 'Intermedio', '¿Qué viajes tiene asignados un conductor seleccionado?',
         parametros=('conductor',))
def viajes_por_conductor(p):
    viajes = (Viaje.objects.select_related('vehiculo', 'conductor')
              .filter(conductor=p['conductor'])
              .order_by('-fecha_salida'))
    return Resultado(COLUMNAS_VIAJES, _filas_viajes(viajes),
                     f'{len(viajes)} viajes asignados a {p["conductor"].nombre}.')


@reporte(8, 'Intermedio', '¿Cuántos viajes se encuentran programados, en curso, finalizados o cancelados?')
def viajes_por_estado(p):
    conteo = dict(Viaje.objects.values_list('estado').annotate(total=Count('id')))
    filas = [[nombre, conteo.get(clave, 0)] for clave, nombre in Viaje.ESTADO_CHOICES]
    return Resultado(['Estado', 'Viajes'], filas,
                     f'Total: {sum(conteo.values())} viajes.',
                     {'tipo': 'segmentos', 'etiquetas': [f[0] for f in filas], 'valores': [f[1] for f in filas],
                      'claves': [clave for clave, _ in Viaje.ESTADO_CHOICES]})


@reporte(9, 'Intermedio', '¿Cuáles son los viajes programados durante un rango de fechas?',
         parametros=('rango',), rango_por_defecto=(-7, 30))
def viajes_en_rango(p):
    viajes = (Viaje.objects.select_related('vehiculo', 'conductor')
              .filter(fecha_salida__gte=p['inicio'], fecha_salida__lt=p['fin'])
              .order_by('fecha_salida'))
    return Resultado(COLUMNAS_VIAJES, _filas_viajes(viajes),
                     f'{len(viajes)} viajes con salida en el período.')


@reporte(10, 'Intermedio', '¿Qué vehículos no tienen viajes registrados?')
def vehiculos_sin_viajes(p):
    vehiculos = (Vehiculo.objects.select_related('tipo_vehiculo')
                 .filter(viajes__isnull=True)
                 .order_by('patente'))
    return Resultado(COLUMNAS_VEHICULOS, _filas_vehiculos(vehiculos),
                     f'{len(vehiculos)} vehículos sin viajes.')


@reporte(11, 'Intermedio', '¿Cuáles son los cinco conductores que han realizado más viajes?')
def top_conductores(p):
    conductores = (Conductor.objects
                   .annotate(total_viajes=Count('viajes'))
                   .order_by('-total_viajes', 'nombre')[:5])
    total = Viaje.objects.count()
    filas = [[i, c.nombre, c.rut, c.total_viajes, f'{_porcentaje(c.total_viajes, total)} %']
             for i, c in enumerate(conductores, start=1)]
    return Resultado(['#', 'Conductor', 'RUT', 'Viajes', '% participación'], filas,
                     grafico={'tipo': 'ranking', 'etiquetas': [f[1] for f in filas], 'valores': [f[3] for f in filas]})


@reporte(12, 'Intermedio', '¿Cuáles son los cinco vehículos que han participado en más viajes?')
def top_vehiculos(p):
    vehiculos = (Vehiculo.objects.select_related('tipo_vehiculo')
                 .annotate(total_viajes=Count('viajes'))
                 .order_by('-total_viajes', 'patente')[:5])
    filas = [[i, v.patente, v.tipo_vehiculo.nombre, f'{v.marca} {v.modelo}', v.total_viajes]
             for i, v in enumerate(vehiculos, start=1)]
    return Resultado(['#', 'Patente', 'Tipo', 'Vehículo', 'Viajes'], filas,
                     grafico={'tipo': 'ranking', 'etiquetas': [f[1] for f in filas], 'valores': [f[4] for f in filas]})


# ===========================================================================
# Nivel avanzado
# ===========================================================================


@reporte(13, 'Avanzado', '¿Cuántos viajes ha realizado cada conductor durante el último mes?')
def viajes_conductor_ultimo_mes(p):
    hace_un_mes = timezone.now() - timedelta(days=30)
    conductores = (Conductor.objects
                   .annotate(viajes_mes=Count('viajes', filter=Q(viajes__fecha_salida__gte=hace_un_mes,
                                                                  viajes__fecha_salida__lte=timezone.now())))
                   .order_by('-viajes_mes', 'nombre'))
    filas = [[c.nombre, c.rut, 'Activo' if c.activo else 'Inactivo', c.viajes_mes] for c in conductores]
    return Resultado(['Conductor', 'RUT', 'Estado', 'Viajes (últimos 30 días)'], filas,
                     f'Desde {_fecha(hace_un_mes)} hasta hoy.')


@reporte(14, 'Avanzado', '¿Qué tipos de vehículos se utilizan con mayor frecuencia en los viajes?')
def tipos_mas_utilizados(p):
    tipos = (TipoVehiculo.objects
             .annotate(total_viajes=Count('vehiculos__viajes'),
                       vehiculos_distintos=Count('vehiculos', distinct=True))
             .order_by('-total_viajes', 'nombre'))
    filas = [[t.nombre, t.vehiculos_distintos, t.total_viajes] for t in tipos]
    return Resultado(['Tipo de vehículo', 'Vehículos', 'Viajes'], filas,
                     grafico={'tipo': 'ranking', 'etiquetas': [f[0] for f in filas], 'valores': [f[2] for f in filas]})


@reporte(15, 'Avanzado', '¿Cuántos viajes se han realizado hacia cada destino?')
def viajes_por_destino(p):
    destinos = (Viaje.objects
                .exclude(estado='cancelado')
                .values('destino')
                .annotate(total=Count('id'), finalizados=Count('id', filter=Q(estado='finalizado')))
                .order_by('-total', 'destino'))
    filas = [[d['destino'], d['total'], d['finalizados']] for d in destinos]
    return Resultado(['Destino', 'Viajes (sin cancelados)', 'Finalizados'], filas,
                     grafico={'tipo': 'ranking', 'etiquetas': [f[0] for f in filas], 'valores': [f[1] for f in filas]})


@reporte(16, 'Avanzado', '¿Qué conductores no han realizado viajes durante un período seleccionado?',
         parametros=('rango',))
def conductores_sin_viajes_periodo(p):
    con_viajes = Viaje.objects.filter(
        fecha_salida__gte=p['inicio'], fecha_salida__lt=p['fin'],
    ).values('conductor_id')
    conductores = Conductor.objects.exclude(id__in=con_viajes).order_by('nombre')
    filas = [[c.nombre, c.rut, c.licencia, 'Activo' if c.activo else 'Inactivo'] for c in conductores]
    return Resultado(['Conductor', 'RUT', 'Licencia', 'Estado'], filas,
                     f'{len(filas)} conductores sin viajes en el período.')


@reporte(17, 'Avanzado', '¿Cuál es la duración promedio de los viajes finalizados?')
def duracion_promedio(p):
    finalizados = Viaje.objects.filter(estado='finalizado', fecha_llegada__isnull=False)
    datos = finalizados.aggregate(
        promedio=Avg(F('fecha_llegada') - F('fecha_salida')),
        cantidad=Count('id'),
    )
    por_tipo = (finalizados
                .values('vehiculo__tipo_vehiculo__nombre')
                .annotate(promedio=Avg(F('fecha_llegada') - F('fecha_salida')), cantidad=Count('id'))
                .order_by('vehiculo__tipo_vehiculo__nombre'))
    filas = [['Todos los viajes finalizados', datos['cantidad'], _duracion(datos['promedio'])]]
    filas += [[f'Tipo: {t["vehiculo__tipo_vehiculo__nombre"]}', t['cantidad'], _duracion(t['promedio'])]
              for t in por_tipo]
    return Resultado(['Grupo', 'Viajes', 'Duración promedio'], filas,
                     f'Duración promedio general: {_duracion(datos["promedio"])}.')


# ===========================================================================
# Nivel análisis
# ===========================================================================


@reporte(18, 'Análisis', '¿Qué conductor ha acumulado la mayor cantidad de viajes finalizados durante el año?',
         parametros=('anio',))
def conductor_del_anio(p):
    ranking = (Conductor.objects
               .annotate(finalizados=Count('viajes', filter=Q(viajes__estado='finalizado',
                                                              viajes__fecha_salida__year=p['anio'])))
               .filter(finalizados__gt=0)
               .order_by('-finalizados', 'nombre')[:5])
    filas = [[i, c.nombre, c.rut, c.finalizados] for i, c in enumerate(ranking, start=1)]
    resumen = (f'{filas[0][1]} lidera {p["anio"]} con {filas[0][3]} viajes finalizados.'
               if filas else f'No hay viajes finalizados en {p["anio"]}.')
    return Resultado(['#', 'Conductor', 'RUT', 'Viajes finalizados'], filas, resumen)


@reporte(19, 'Análisis', '¿Qué porcentaje de los viajes registrados se encuentra finalizado, cancelado o pendiente?')
def porcentaje_por_estado(p):
    totales = Viaje.objects.aggregate(
        total=Count('id'),
        finalizados=Count('id', filter=Q(estado='finalizado')),
        cancelados=Count('id', filter=Q(estado='cancelado')),
        pendientes=Count('id', filter=Q(estado__in=['programado', 'en_curso'])),
    )
    total = totales['total']
    filas = [
        ['Finalizados', totales['finalizados'], f"{_porcentaje(totales['finalizados'], total)} %"],
        ['Cancelados', totales['cancelados'], f"{_porcentaje(totales['cancelados'], total)} %"],
        ['Pendientes (programados + en curso)', totales['pendientes'],
         f"{_porcentaje(totales['pendientes'], total)} %"],
    ]
    return Resultado(['Estado', 'Viajes', 'Porcentaje'], filas, f'Total de viajes: {total}.',
                     {'tipo': 'segmentos', 'etiquetas': ['Finalizados', 'Cancelados', 'Pendientes'],
                      'valores': [f[1] for f in filas], 'claves': ['finalizado', 'cancelado', 'pendiente']})


@reporte(20, 'Análisis', '¿Cómo se distribuye la cantidad de viajes realizados por mes durante el año seleccionado?',
         parametros=('anio',))
def viajes_por_mes(p):
    anio = p['anio']
    zona = timezone.get_current_timezone()
    # Se calcula el inicio de cada mes en la zona horaria local y se cuenta con
    # una sola consulta usando agregación condicional (Count + filter).
    limites = [timezone.make_aware(datetime(anio, mes, 1), zona) for mes in range(1, 13)]
    limites.append(timezone.make_aware(datetime(anio + 1, 1, 1), zona))
    conteos = Viaje.objects.exclude(estado='cancelado').aggregate(**{
        f'mes_{mes}': Count('id', filter=Q(fecha_salida__gte=limites[mes - 1], fecha_salida__lt=limites[mes]))
        for mes in range(1, 13)
    })
    filas = [[MESES[mes - 1], conteos[f'mes_{mes}']] for mes in range(1, 13)]
    return Resultado(['Mes', 'Viajes (sin cancelados)'], filas,
                     f'Total {anio}: {sum(f[1] for f in filas)} viajes.',
                     {'tipo': 'columnas', 'etiquetas': [f[0] for f in filas], 'valores': [f[1] for f in filas]})
