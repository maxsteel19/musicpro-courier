"""Carga datos de prueba realistas (Faker, configuración chilena).

Uso:
    python manage.py seed_courier            # agrega datos si la base está vacía
    python manage.py seed_courier --limpiar  # borra los datos del caso y vuelve a cargarlos

No crea usuarios: el primer administrador se crea con ``createsuperuser``.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from courier.models import (
    Conductor, Envio, Incidencia, Notificacion, Paquete, Sucursal,
    TipoVehiculo, Vehiculo, Viaje,
)
from courier.validators import normalizar_patente, normalizar_rut

SUCURSALES = [
    ('Music Pro - Sede Principal', 'Av. Providencia 1234', 'Santiago', -33.4489, -70.6422),
    ('Music Pro - Sucursal Valparaíso', 'Av. Pedro Montt 789', 'Valparaíso', -33.0472, -71.6127),
    ('Music Pro - Sucursal Concepción', 'Calle Freire 456', 'Concepción', -36.8201, -73.0444),
    ('Music Pro - Franquicia Temuco', 'Calle Arturo Prat 321', 'Temuco', -38.7359, -72.5904),
    ('Music Pro - Franquicia Antofagasta', 'Av. Grecia 1500', 'Antofagasta', -23.6509, -70.3975),
    ('Music Pro - Sucursal La Serena', 'Av. Balmaceda 2100', 'La Serena', -29.9027, -71.2519),
    ('Music Pro - Sucursal Rancagua', 'Calle Independencia 640', 'Rancagua', -34.1708, -70.7444),
    ('Music Pro - Sucursal Talca', '1 Sur 1100', 'Talca', -35.4264, -71.6554),
]

# Horas aproximadas de viaje desde Santiago (para fechas de llegada realistas).
HORAS_DESDE_SANTIAGO = {
    'Santiago': 1, 'Valparaíso': 2, 'Rancagua': 1.5, 'Talca': 3.5, 'Concepción': 6,
    'Temuco': 8.5, 'La Serena': 6, 'Antofagasta': 15,
}

TIPOS = [
    ('Furgón', 'Furgón de reparto urbano para envíos pequeños y medianos.'),
    ('Camioneta', 'Camioneta con caja cerrada para rutas regionales.'),
    ('Camión', 'Camión de carga para traslados masivos entre sucursales.'),
    ('Minibús', 'Minibús para traslado de equipos de giras y personal técnico.'),
    ('Automóvil', 'Vehículo liviano para entregas urgentes de bajo volumen.'),
]

MODELOS = {
    'Furgón': [('Peugeot', 'Partner'), ('Renault', 'Kangoo'), ('Citroën', 'Berlingo'), ('Fiat', 'Fiorino')],
    'Camioneta': [('Toyota', 'Hilux'), ('Nissan', 'Navara'), ('Mitsubishi', 'L200'), ('Ford', 'Ranger')],
    'Camión': [('Mercedes-Benz', 'Atego'), ('Volvo', 'FH'), ('Hyundai', 'HD78'), ('JAC', '1040')],
    'Minibús': [('Mercedes-Benz', 'Sprinter'), ('Hyundai', 'H350'), ('Ford', 'Transit')],
    'Automóvil': [('Toyota', 'Yaris'), ('Hyundai', 'Accent'), ('Chevrolet', 'Sail')],
}

INSTRUMENTOS = [
    'Guitarra eléctrica Fender Stratocaster', 'Batería electrónica Roland TD-17', 'Amplificador Marshall JCM800',
    'Teclado Yamaha PSR-SX900', 'Micrófonos Shure SM58 (x6)', 'Mesa de mezclas Behringer X32',
    'Cables XLR 10 m (x20)', 'Par de bafles JBL EON615', 'Bajo eléctrico Ibanez SR500', 'Piano digital Casio PX-S3100',
    'Guitarra acústica Taylor 214ce', 'Pedalera Boss GT-1000', 'Violín Stentor Student II', 'Saxofón alto Yamaha YAS-280',
    'Monitores de estudio KRK Rokit 5', 'Interfaz de audio Focusrite Scarlett 2i2', 'Platillos Zildjian A Custom',
    'Controlador DJ Pioneer DDJ-400', 'Ukelele Kala KA-15S', 'Atril y soportes de escenario (kit)',
]

LICENCIAS = ['Clase A2', 'Clase A3', 'Clase A4', 'Clase A5', 'Clase B']


class Command(BaseCommand):
    help = 'Carga datos de prueba del sistema Courier y Transporte de Music Pro.'

    def add_arguments(self, parser):
        parser.add_argument('--limpiar', action='store_true', help='Elimina los datos del caso antes de cargar.')
        parser.add_argument('--semilla', type=int, default=2026, help='Semilla para obtener siempre los mismos datos.')

    @transaction.atomic
    def handle(self, *args, **opciones):
        if opciones['limpiar']:
            self._limpiar()
        elif Viaje.objects.exists() or Envio.objects.exists():
            self.stdout.write(self.style.WARNING(
                'La base ya tiene datos. Use --limpiar para borrarlos y volver a cargar.'))
            return

        random.seed(opciones['semilla'])
        self.fake = Faker('es_CL')
        self.fake.seed_instance(opciones['semilla'])
        self.ahora = timezone.now()

        sucursales = self._crear_sucursales()
        tipos = self._crear_tipos()
        vehiculos = self._crear_vehiculos(tipos)
        conductores = self._crear_conductores()
        viajes = self._crear_viajes(vehiculos, conductores, sucursales)
        paquetes = self._crear_paquetes()
        envios = self._crear_envios(sucursales, paquetes, viajes)
        self._crear_incidencias_y_notificaciones(envios)

        self.stdout.write(self.style.SUCCESS(
            f'Datos cargados: {len(sucursales)} sucursales, {len(tipos)} tipos de vehículo, '
            f'{len(vehiculos)} vehículos, {len(conductores)} conductores, {len(viajes)} viajes, '
            f'{len(paquetes)} paquetes, {len(envios)} envíos, {Incidencia.objects.count()} incidencias y '
            f'{Notificacion.objects.count()} notificaciones.'
        ))

    # ------------------------------------------------------------------
    def _limpiar(self):
        for modelo in (Notificacion, Incidencia, Envio, Paquete, Viaje, Vehiculo, Conductor, TipoVehiculo, Sucursal):
            modelo.objects.all().delete()
        self.stdout.write('Datos anteriores eliminados.')

    def _crear_sucursales(self):
        sucursales = []
        for nombre, direccion, ciudad, lat, lng in SUCURSALES:
            slug = ciudad.lower().replace('í', 'i').replace('ó', 'o').replace(' ', '')
            sucursales.append(Sucursal.objects.create(
                nombre=nombre, direccion=f'{direccion}, {ciudad}', ciudad=ciudad,
                telefono=self.fake.phone_number(), email=f'{slug}@musicpro.cl',
                latitud=lat, longitud=lng, activa=True,
            ))
        sucursales[-1].activa = False  # una sucursal inactiva para probar filtros
        sucursales[-1].save(update_fields=['activa'])
        return sucursales

    def _crear_tipos(self):
        return {nombre: TipoVehiculo.objects.create(nombre=nombre, descripcion=desc) for nombre, desc in TIPOS}

    def _crear_vehiculos(self, tipos):
        distribucion = ['Furgón'] * 6 + ['Camioneta'] * 5 + ['Camión'] * 5 + ['Minibús'] * 3 + ['Automóvil'] * 3
        vehiculos = []
        patentes = set()
        for nombre_tipo in distribucion:
            while True:
                try:
                    patente = normalizar_patente(self.fake.license_plate())
                except ValidationError:
                    continue  # Faker también genera patentes especiales (p. ej. "PR-123")
                if patente not in patentes:
                    patentes.add(patente)
                    break
            marca, modelo = random.choice(MODELOS[nombre_tipo])
            estado = random.choices(['operativo', 'mantencion', 'fuera_servicio'], weights=[80, 14, 6])[0]
            vehiculos.append(Vehiculo.objects.create(
                tipo_vehiculo=tipos[nombre_tipo], patente=patente, marca=marca, modelo=modelo,
                anio=random.randint(2008, 2025), estado=estado,
                disponible=(estado == 'operativo' and random.random() > 0.2),
            ))
        return vehiculos

    def _crear_conductores(self):
        conductores = []
        for indice in range(16):
            conductores.append(Conductor.objects.create(
                rut=normalizar_rut(self.fake.person_rut()),
                nombre=self.fake.name(),
                licencia=random.choice(LICENCIAS),
                telefono=self.fake.phone_number(),
                activo=indice < 14,  # dos conductores inactivos
            ))
        return conductores

    def _crear_viajes(self, vehiculos, conductores, sucursales):
        # Los dos últimos vehículos quedan sin viajes (reporte 10) y los
        # conductores inactivos no reciben viajes recientes (reporte 16).
        con_viajes = vehiculos[:-2]
        activos = [c for c in conductores if c.activo]
        pesos_conductor = [random.randint(1, 10) for _ in activos]
        ciudades = [s.ciudad for s in sucursales]
        viajes = []
        for _ in range(220):
            dias = random.randint(-420, 30)  # ~14 meses atrás hasta 30 días adelante
            salida = (self.ahora + timedelta(days=dias)).replace(
                hour=random.randint(6, 20), minute=random.choice([0, 15, 30, 45]), second=0, microsecond=0)
            origen = 'Santiago' if random.random() < 0.6 else random.choice(ciudades)
            destino = random.choice([c for c in ciudades if c != origen])
            horas = abs(HORAS_DESDE_SANTIAGO[destino] - HORAS_DESDE_SANTIAGO[origen]) + random.uniform(0.5, 2.5)
            conductor = random.choices(activos, weights=pesos_conductor)[0]
            if dias < -40 and random.random() < 0.12:
                conductor = random.choice(conductores[-2:])  # viajes antiguos de conductores hoy inactivos

            if salida > self.ahora:
                estado, llegada = 'programado', None
            elif salida + timedelta(hours=horas) > self.ahora:
                estado, llegada = 'en_curso', None
            else:
                estado = random.choices(['finalizado', 'cancelado'], weights=[90, 10])[0]
                llegada = salida + timedelta(hours=horas) if estado == 'finalizado' else None

            viajes.append(Viaje.objects.create(
                vehiculo=random.choice(con_viajes), conductor=conductor,
                origen=origen, destino=destino, fecha_salida=salida, fecha_llegada=llegada,
                estado=estado,
                observaciones='' if random.random() < 0.7 else self.fake.sentence(nb_words=10),
            ))

        # Viajes de larga distancia que salieron hace pocas horas: quedan "en curso".
        for destino in ('Antofagasta', 'Temuco', 'Concepción', 'La Serena', 'Talca'):
            viajes.append(Viaje.objects.create(
                vehiculo=random.choice(con_viajes), conductor=random.choice(activos),
                origen='Santiago', destino=destino,
                fecha_salida=(self.ahora - timedelta(minutes=random.randint(30, 150))).replace(second=0, microsecond=0),
                estado='en_curso',
            ))
        return viajes

    def _crear_paquetes(self):
        paquetes = []
        for numero in range(1, 91):
            paquetes.append(Paquete.objects.create(
                codigo=f'PKG-2026-{numero:04d}',
                descripcion=random.choice(INSTRUMENTOS),
                peso=Decimal(str(round(random.uniform(0.5, 60), 2))),
                volumen=Decimal(str(round(random.uniform(0.02, 1.2), 2))),
                valor_declarado=Decimal(random.randrange(80_000, 2_500_000, 10_000)),
                estado='preparacion',
            ))
        return paquetes

    def _crear_envios(self, sucursales, paquetes, viajes):
        activas = [s for s in sucursales if s.activa]
        por_ciudad = {s.ciudad: s for s in activas}
        envios = []
        for numero, paquete in enumerate(paquetes, start=1):
            if numero <= 12:
                viaje = random.choice([v for v in viajes if v.estado in ('en_curso', 'programado')])
            else:
                viaje = random.choice(viajes) if random.random() < 0.85 else None
            if viaje and viaje.origen in por_ciudad and viaje.destino in por_ciudad:
                origen, destino = por_ciudad[viaje.origen], por_ciudad[viaje.destino]
            else:
                origen, destino = random.sample(activas, 2)
                viaje = None

            estado_viaje = viaje.estado if viaje else None
            despacho = viaje.fecha_salida if viaje else None
            estimada = despacho + timedelta(hours=random.randint(8, 48)) if despacho else None
            real = None
            if estado_viaje == 'finalizado':
                estado, progreso = 'entregado', 100
                real = (viaje.fecha_llegada or despacho) + timedelta(hours=random.randint(0, 30))
            elif estado_viaje == 'en_curso':
                estado, progreso = 'en_ruta', random.randint(20, 90)
            elif estado_viaje == 'cancelado':
                estado, progreso = 'cancelado', 0
            else:
                estado, progreso = 'pendiente', 0

            envios.append(Envio.objects.create(
                numero_envio=f'ENV-2026-{numero:04d}',
                sucursal_origen=origen, sucursal_destino=destino, paquete=paquete, viaje=viaje,
                estado=estado, prioridad=random.choices(['baja', 'media', 'alta', 'urgente'], weights=[20, 45, 25, 10])[0],
                progreso=progreso, fecha_despacho=despacho, fecha_entrega_estimada=estimada,
                fecha_entrega_real=real,
            ))
            paquete.estado = {'entregado': 'entregado', 'en_ruta': 'transito', 'cancelado': 'devuelto'}.get(
                estado, 'preparacion')
            paquete.save(update_fields=['estado'])
        return envios

    def _crear_incidencias_y_notificaciones(self, envios):
        descripciones = {
            'retraso': 'Congestión en la ruta retrasó la entrega estimada.',
            'desvio': 'Corte de camino obligó a tomar una ruta alternativa.',
            'mecanica': 'Falla mecánica menor detuvo el vehículo por un tiempo.',
            'danio': 'Embalaje con golpes detectado al momento de la descarga.',
            'otra': 'Destinatario no disponible en el horario acordado.',
        }
        for envio in random.sample(envios, 22):
            tipo = random.choice(list(descripciones))
            Incidencia.objects.create(
                envio=envio, tipo=tipo, descripcion=descripciones[tipo],
                resuelta=envio.estado in ('entregado', 'cancelado') or random.random() < 0.3,
            )
        for envio in envios:
            if envio.estado == 'pendiente' and random.random() < 0.5:
                continue
            canal = random.choice(['email', 'sms', 'push'])
            mensaje = {
                'pendiente': f'Su envío {envio.numero_envio} fue registrado y espera despacho.',
                'en_ruta': f'Su envío {envio.numero_envio} va en camino a {envio.sucursal_destino.ciudad}.',
                'entregado': f'Su envío {envio.numero_envio} fue entregado en {envio.sucursal_destino.ciudad}.',
                'cancelado': f'Su envío {envio.numero_envio} fue cancelado. Contáctenos para más información.',
            }[envio.estado]
            Notificacion.objects.create(envio=envio, canal=canal, mensaje=mensaje,
                                        enviada=envio.estado != 'pendiente')
