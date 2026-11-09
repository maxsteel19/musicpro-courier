"""Datos y utilidades comunes para las pruebas."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from courier.models import (
    Conductor, Envio, Incidencia, Notificacion, Paquete, Sucursal,
    TipoVehiculo, Vehiculo, Viaje,
)

Usuario = get_user_model()
CLAVE = 'ClaveSegura-2026!'


# Hasher rápido solo para las pruebas (en producción se usa PBKDF2).
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PruebaBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user('admin', 'admin@musicpro.cl', CLAVE, is_staff=True)
        cls.operador = Usuario.objects.create_user('operador', 'op@musicpro.cl', CLAVE)
        cls.superusuario = Usuario.objects.create_superuser('root', 'root@musicpro.cl', CLAVE)

        ahora = timezone.now()
        cls.santiago = Sucursal.objects.create(nombre='Sede Santiago', direccion='Av. 1', ciudad='Santiago',
                                               telefono='+56 2 1111 1111', email='stgo@musicpro.cl')
        cls.valpo = Sucursal.objects.create(nombre='Sucursal Valparaíso', direccion='Av. 2', ciudad='Valparaíso',
                                            telefono='+56 32 222 2222', email='valpo@musicpro.cl')
        cls.paquete = Paquete.objects.create(codigo='PKG-T-1', descripcion='Guitarra', peso=Decimal('5'),
                                             volumen=Decimal('0.1'), valor_declarado=Decimal('500000'))
        cls.camion = TipoVehiculo.objects.create(nombre='Camión')
        cls.furgon = TipoVehiculo.objects.create(nombre='Furgón')
        cls.vehiculo = Vehiculo.objects.create(tipo_vehiculo=cls.camion, patente='BCDF-12', marca='Volvo',
                                               modelo='FH', anio=2015)
        cls.vehiculo_sin_viajes = Vehiculo.objects.create(tipo_vehiculo=cls.furgon, patente='AB-1234',
                                                          marca='Renault', modelo='Kangoo', anio=2010)
        cls.conductor = Conductor.objects.create(rut='12.345.678-5', nombre='Ana Rojas', licencia='Clase A4')
        cls.conductor_sin_viajes = Conductor.objects.create(rut='11.111.111-1', nombre='Pedro Soto',
                                                            licencia='Clase B')
        cls.viaje = Viaje.objects.create(vehiculo=cls.vehiculo, conductor=cls.conductor, origen='Santiago',
                                         destino='Valparaíso', fecha_salida=ahora - timedelta(days=2),
                                         fecha_llegada=ahora - timedelta(days=2) + timedelta(hours=2),
                                         estado='finalizado')
        cls.viaje_programado = Viaje.objects.create(vehiculo=cls.vehiculo, conductor=cls.conductor,
                                                    origen='Santiago', destino='Temuco',
                                                    fecha_salida=ahora + timedelta(days=3), estado='programado')
        cls.envio = Envio.objects.create(numero_envio='ENV-T-1', sucursal_origen=cls.santiago,
                                         sucursal_destino=cls.valpo, paquete=cls.paquete, viaje=cls.viaje)
        cls.incidencia = Incidencia.objects.create(envio=cls.envio, tipo='retraso', descripcion='Atraso')
        cls.notificacion = Notificacion.objects.create(envio=cls.envio, canal='email', mensaje='En camino')

    def iniciar_sesion(self, usuario=None):
        self.client.force_login(usuario or self.operador)
