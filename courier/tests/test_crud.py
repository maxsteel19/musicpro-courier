"""Operaciones CRUD desde la interfaz propia y su reflejo en la base de datos."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from courier.models import (
    Conductor, Envio, Incidencia, Notificacion, Paquete, Sucursal,
    TipoVehiculo, Vehiculo, Viaje,
)

from .base import PruebaBase


def fecha_html(valor):
    return timezone.localtime(valor).strftime('%Y-%m-%dT%H:%M')


class CrudEntidadesTests(PruebaBase):
    """Crea, consulta, modifica y elimina cada entidad del caso."""

    def setUp(self):
        self.iniciar_sesion()

    def casos(self):
        salida = timezone.now() + timedelta(days=1)
        return [
            ('sucursal', Sucursal, {
                'nombre': 'Sucursal Prueba', 'direccion': 'Calle 1', 'ciudad': 'Talca', 'telefono': '123',
                'email': 'p@musicpro.cl', 'latitud': '0', 'longitud': '0', 'activa': 'on'},
             'nombre', 'Sucursal Editada'),
            ('paquete', Paquete, {
                'codigo': 'pkg-nuevo', 'descripcion': 'Batería', 'peso': '10', 'volumen': '0.5',
                'valor_declarado': '900000', 'estado': 'preparacion'},
             'descripcion', 'Batería editada'),
            ('tipo_vehiculo', TipoVehiculo, {'nombre': 'Minibús', 'descripcion': 'Giras'},
             'nombre', 'Minibús XL'),
            ('vehiculo', Vehiculo, {
                'tipo_vehiculo': self.camion.pk, 'patente': 'gh jk 34', 'marca': 'Hyundai', 'modelo': 'HD78',
                'anio': '2020', 'estado': 'operativo', 'disponible': 'on'},
             'modelo', 'HD65'),
            ('conductor', Conductor, {
                'rut': '7654321-6', 'nombre': 'Carla Muñoz', 'licencia': 'Clase A2', 'telefono': '', 'activo': 'on'},
             'nombre', 'Carla Muñoz Pérez'),
            ('viaje', Viaje, {
                'vehiculo': self.vehiculo.pk, 'conductor': self.conductor.pk, 'origen': 'Santiago',
                'destino': 'Rancagua', 'fecha_salida': fecha_html(salida), 'fecha_llegada': '',
                'estado': 'programado', 'observaciones': ''},
             'destino', 'Talca'),
            ('envio', Envio, {
                'numero_envio': 'env-nuevo', 'sucursal_origen': self.santiago.pk,
                'sucursal_destino': self.valpo.pk, 'paquete': self.paquete.pk, 'viaje': self.viaje_programado.pk,
                'estado': 'pendiente', 'prioridad': 'alta', 'progreso': '0', 'fecha_despacho': '',
                'fecha_entrega_estimada': '', 'fecha_entrega_real': '', 'observaciones': ''},
             'observaciones', 'Frágil'),
            ('incidencia', Incidencia, {'envio': self.envio.pk, 'tipo': 'desvio', 'descripcion': 'Corte de ruta'},
             'descripcion', 'Corte de ruta (resuelto)'),
            ('notificacion', Notificacion, {'envio': self.envio.pk, 'canal': 'sms', 'mensaje': 'Su envío salió'},
             'mensaje', 'Su envío llegó'),
        ]

    def test_crear_editar_eliminar(self):
        for entidad, modelo, datos, campo, nuevo_valor in self.casos():
            with self.subTest(entidad=entidad):
                antes = modelo.objects.count()
                # Crear
                respuesta = self.client.post(reverse(f'courier:{entidad}_crear'), datos)
                self.assertRedirects(respuesta, reverse(f'courier:{entidad}_lista'))
                self.assertEqual(modelo.objects.count(), antes + 1)
                objeto = modelo.objects.order_by('-pk').first()

                # Consultar (listado)
                self.assertEqual(self.client.get(reverse(f'courier:{entidad}_lista')).status_code, 200)

                # Editar
                datos_editados = dict(datos, **{campo: nuevo_valor})
                respuesta = self.client.post(reverse(f'courier:{entidad}_editar', args=[objeto.pk]), datos_editados)
                self.assertRedirects(respuesta, reverse(f'courier:{entidad}_lista'))
                objeto.refresh_from_db()
                self.assertEqual(getattr(objeto, campo), nuevo_valor)

                # Eliminar (confirmación GET + POST)
                url_eliminar = reverse(f'courier:{entidad}_eliminar', args=[objeto.pk])
                self.assertContains(self.client.get(url_eliminar), 'Sí, eliminar')
                self.client.post(url_eliminar)
                self.assertFalse(modelo.objects.filter(pk=objeto.pk).exists())

    def test_formularios_normalizan_datos(self):
        self.client.post(reverse('courier:vehiculo_crear'), {
            'tipo_vehiculo': self.camion.pk, 'patente': 'zz9988', 'marca': 'Ford', 'modelo': 'Cargo',
            'anio': '2019', 'estado': 'mantencion', 'disponible': 'on'})
        vehiculo = Vehiculo.objects.get(patente='ZZ-9988')
        self.assertFalse(vehiculo.disponible)  # en mantención no queda disponible
        self.client.post(reverse('courier:conductor_crear'), {
            'rut': '76543216', 'nombre': 'Luis', 'licencia': 'B', 'activo': 'on'})
        self.assertTrue(Conductor.objects.filter(rut='7.654.321-6').exists())

    def test_busqueda_y_filtros_en_listados(self):
        respuesta = self.client.get(reverse('courier:vehiculo_lista'), {'q': 'Volvo'})
        self.assertContains(respuesta, 'BCDF-12')
        self.assertNotContains(respuesta, 'AB-1234')
        respuesta = self.client.get(reverse('courier:viaje_lista'), {'estado': 'programado'})
        self.assertContains(respuesta, 'Temuco')
        self.assertNotContains(respuesta, self.viaje.codigo)

    def test_detalles(self):
        self.assertContains(self.client.get(reverse('courier:envio_detalle', args=[self.envio.pk])), 'ENV-T-1')
        self.assertContains(self.client.get(reverse('courier:viaje_detalle', args=[self.viaje.pk])), 'ENV-T-1')
        self.assertEqual(self.client.get(reverse('courier:envio_detalle', args=[9999])).status_code, 404)

    def test_seguimiento_por_numero(self):
        respuesta = self.client.get(reverse('courier:seguimiento'), {'numero': 'env-t-1'})
        self.assertRedirects(respuesta, reverse('courier:envio_detalle', args=[self.envio.pk]))

    def test_envio_registra_al_usuario_que_lo_creo(self):
        self.client.post(reverse('courier:envio_crear'), {
            'numero_envio': 'ENV-USR', 'sucursal_origen': self.santiago.pk, 'sucursal_destino': self.valpo.pk,
            'paquete': self.paquete.pk, 'estado': 'pendiente', 'prioridad': 'media', 'progreso': '0'})
        self.assertEqual(Envio.objects.get(numero_envio='ENV-USR').creado_por, self.operador)


class ValidacionesTests(PruebaBase):
    def setUp(self):
        self.iniciar_sesion()

    def test_envio_con_origen_igual_a_destino(self):
        respuesta = self.client.post(reverse('courier:envio_crear'), {
            'numero_envio': 'ENV-X', 'sucursal_origen': self.santiago.pk, 'sucursal_destino': self.santiago.pk,
            'paquete': self.paquete.pk, 'estado': 'pendiente', 'prioridad': 'media', 'progreso': '0'})
        self.assertContains(respuesta, 'El destino debe ser distinto del origen.')
        self.assertFalse(Envio.objects.filter(numero_envio='ENV-X').exists())

    def test_viaje_con_llegada_anterior_a_salida(self):
        salida = timezone.now()
        respuesta = self.client.post(reverse('courier:viaje_crear'), {
            'vehiculo': self.vehiculo.pk, 'conductor': self.conductor.pk, 'origen': 'Santiago',
            'destino': 'Talca', 'fecha_salida': fecha_html(salida),
            'fecha_llegada': fecha_html(salida - timedelta(hours=3)), 'estado': 'finalizado'})
        self.assertContains(respuesta, 'La llegada debe ser posterior a la salida.')

    def test_viaje_con_conductor_inactivo(self):
        self.conductor_sin_viajes.activo = False
        self.conductor_sin_viajes.save()
        respuesta = self.client.post(reverse('courier:viaje_crear'), {
            'vehiculo': self.vehiculo.pk, 'conductor': self.conductor_sin_viajes.pk, 'origen': 'Santiago',
            'destino': 'Talca', 'fecha_salida': fecha_html(timezone.now()), 'estado': 'programado'})
        self.assertContains(respuesta, 'El conductor seleccionado está inactivo.')

    def test_rut_invalido(self):
        respuesta = self.client.post(reverse('courier:conductor_crear'), {
            'rut': '12.345.678-9', 'nombre': 'X', 'licencia': 'B'})
        self.assertContains(respuesta, 'El dígito verificador del RUT no es correcto.')

    def test_patente_duplicada(self):
        respuesta = self.client.post(reverse('courier:vehiculo_crear'), {
            'tipo_vehiculo': self.camion.pk, 'patente': 'bcdf12', 'marca': 'X', 'modelo': 'Y',
            'anio': '2020', 'estado': 'operativo'})
        self.assertContains(respuesta, 'Ya existe un vehículo con esta patente.')

    def test_no_se_elimina_registro_con_datos_asociados(self):
        respuesta = self.client.post(reverse('courier:sucursal_eliminar', args=[self.santiago.pk]), follow=True)
        self.assertContains(respuesta, 'No se puede eliminar')
        self.assertTrue(Sucursal.objects.filter(pk=self.santiago.pk).exists())
        self.client.post(reverse('courier:conductor_eliminar', args=[self.conductor.pk]))
        self.assertTrue(Conductor.objects.filter(pk=self.conductor.pk).exists())
