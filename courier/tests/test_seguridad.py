"""Seguridad del prototipo: pauta OWASP del curso y puntos revisados en la demostración.

- Acceso: bloqueo por intentos, recuperación de clave y claves temporales.
- Validación de entradas y protección contra XSS.
- Protección de datos confidenciales (cifrado) y acuerdo de uso de datos.
- Auditoría y cabeceras de seguridad.
"""
import re

from django.contrib.auth import SESSION_KEY
from django.core import mail
from django.db import connection
from django.test import override_settings
from django.urls import reverse

from courier.entradas import DatosSucursal
from courier.models import (
    BloqueoAcceso, Conductor, PerfilUsuario, RegistroAuditoria, Sucursal, Vehiculo,
)

from .base import CLAVE, PruebaBase, Usuario, aceptar_acuerdo


def iniciar(cliente, username, clave):
    return cliente.post(reverse('login'), {'username': username, 'password': clave})


@override_settings(LOGIN_MAX_INTENTOS=3, LOGIN_MINUTOS_BLOQUEO=15)
class BloqueoPorIntentosTests(PruebaBase):
    def test_bloquea_la_cuenta_tras_los_intentos_fallidos(self):
        respuesta = iniciar(self.client, 'operador', 'mala-1')
        self.assertContains(respuesta, 'Le quedan 2 intento(s)')
        iniciar(self.client, 'operador', 'mala-2')
        respuesta = iniciar(self.client, 'operador', 'mala-3')
        self.assertContains(respuesta, 'Cuenta bloqueada temporalmente')
        # Aunque ahora use la clave correcta, no puede entrar mientras dure el bloqueo.
        respuesta = iniciar(self.client, 'operador', CLAVE)
        self.assertContains(respuesta, 'Cuenta bloqueada temporalmente')
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertTrue(RegistroAuditoria.objects.filter(accion='bloqueo', username='operador').exists())

    def test_usuario_inexistente_recibe_la_misma_respuesta(self):
        # No se revela si la cuenta existe: el mensaje y el conteo son iguales.
        respuesta = iniciar(self.client, 'no-existe', 'mala')
        self.assertContains(respuesta, 'Le quedan 2 intento(s)')

    def test_ingreso_correcto_reinicia_el_contador(self):
        iniciar(self.client, 'operador', 'mala-1')
        iniciar(self.client, 'operador', 'mala-2')
        self.assertRedirects(iniciar(self.client, 'operador', CLAVE), reverse('courier:dashboard'))
        self.assertFalse(BloqueoAcceso.objects.filter(username='operador').exists())

    def test_administrador_puede_desbloquear(self):
        for clave in ('a', 'b', 'c'):
            iniciar(self.client_class(), 'operador', clave)
        self.iniciar_sesion(self.admin)
        self.assertContains(self.client.get(reverse('courier:usuario_lista')), 'Bloqueada')
        self.client.post(reverse('courier:usuario_desbloquear', args=[self.operador.pk]))
        self.assertRedirects(iniciar(self.client_class(), 'operador', CLAVE), reverse('courier:dashboard'))

    def test_operador_no_puede_desbloquear(self):
        self.iniciar_sesion(self.operador)
        respuesta = self.client.post(reverse('courier:usuario_desbloquear', args=[self.admin.pk]))
        self.assertEqual(respuesta.status_code, 403)


class RecuperacionDeClaveTests(PruebaBase):
    def test_flujo_completo_de_recuperacion(self):
        respuesta = self.client.post(reverse('password_reset'), {'email': 'op@musicpro.cl'})
        self.assertRedirects(respuesta, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        enlace = re.search(r'https?://[^/]+(/cuentas/recuperar/\S+)', mail.outbox[0].body).group(1)

        respuesta = self.client.get(enlace, follow=True)  # Django cambia el token por uno de sesión
        url_formulario = respuesta.redirect_chain[-1][0]
        respuesta = self.client.post(url_formulario, {
            'new_password1': 'Recuperada-2026!', 'new_password2': 'Recuperada-2026!'})
        self.assertRedirects(respuesta, reverse('password_reset_complete'))
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password('Recuperada-2026!'))

        # El enlace es de un solo uso.
        self.assertContains(self.client.get(enlace, follow=True), 'El enlace no es válido')

    def test_correo_desconocido_no_revela_nada(self):
        respuesta = self.client.post(reverse('password_reset'), {'email': 'nadie@musicpro.cl'})
        self.assertRedirects(respuesta, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_login_ofrece_recuperar_la_clave(self):
        self.assertContains(self.client.get(reverse('login')), reverse('password_reset'))


class ClaveTemporalTests(PruebaBase):
    def test_usuario_creado_por_admin_debe_cambiar_su_clave(self):
        self.iniciar_sesion(self.admin)
        self.client.post(reverse('courier:usuario_crear'), {
            'username': 'nuevo', 'first_name': 'Nora', 'last_name': 'Paz', 'email': 'nora@musicpro.cl',
            'is_active': 'on', 'password1': 'Temporal-2026!', 'password2': 'Temporal-2026!'})
        nuevo = Usuario.objects.get(username='nuevo')
        aceptar_acuerdo(nuevo)

        cliente = self.client_class()
        iniciar(cliente, 'nuevo', 'Temporal-2026!')
        self.assertRedirects(cliente.get(reverse('courier:dashboard')), reverse('password_cambiar'))
        cliente.post(reverse('password_cambiar'), {
            'old_password': 'Temporal-2026!', 'new_password1': 'Personal-2026!', 'new_password2': 'Personal-2026!'})
        self.assertEqual(cliente.get(reverse('courier:dashboard')).status_code, 200)
        self.assertFalse(PerfilUsuario.objects.get(usuario=nuevo).debe_cambiar_password)

    def test_clave_asignada_a_otro_usuario_queda_temporal(self):
        self.iniciar_sesion(self.admin)
        self.client.post(reverse('courier:usuario_password', args=[self.operador.pk]), {
            'new_password1': 'Renovada-2026!', 'new_password2': 'Renovada-2026!'})
        self.assertTrue(PerfilUsuario.objects.get(usuario=self.operador).debe_cambiar_password)


class PoliticaDeContrasenasTests(PruebaBase):
    def test_exige_letras_numeros_y_simbolos(self):
        self.iniciar_sesion(self.admin)
        for clave in ('soloLetrasLargas', 'Letras12345678', 'Simbolos-sin-numero'):
            with self.subTest(clave=clave):
                respuesta = self.client.post(reverse('courier:usuario_crear'), {
                    'username': 'debil', 'first_name': 'D', 'last_name': 'D', 'email': 'd@musicpro.cl',
                    'is_active': 'on', 'password1': clave, 'password2': clave})
                self.assertContains(respuesta, 'La contraseña debe contener al menos')
        self.assertFalse(Usuario.objects.filter(username='debil').exists())

    def test_la_clave_no_se_vuelve_a_mostrar_en_la_pagina(self):
        self.iniciar_sesion(self.admin)
        respuesta = self.client.post(reverse('courier:usuario_crear'), {
            'username': 'x', 'email': 'x@musicpro.cl', 'password1': 'Secreta-2026!', 'password2': 'Otra-2026!'})
        self.assertNotContains(respuesta, 'Secreta-2026!')


class ValidacionDeEntradasTests(PruebaBase):
    def setUp(self):
        self.iniciar_sesion()

    def datos_sucursal(self, **cambios):
        datos = {'nombre': 'Sucursal Talca', 'direccion': "Av. O'Higgins 123", 'ciudad': 'Talca',
                 'telefono': '+56 71 222 3333', 'email': 'talca@musicpro.cl', 'latitud': '-35.4',
                 'longitud': '-71.6', 'activa': 'on'}
        datos.update(cambios)
        return datos

    def test_rechaza_caracteres_peligrosos(self):
        for valor in ('<script>alert(1)</script>', 'Sede "X"', '100%', 'a\\b', 'nulo\x00'):
            with self.subTest(valor=valor):
                respuesta = self.client.post(reverse('courier:sucursal_crear'), self.datos_sucursal(nombre=valor))
                self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Sucursal.objects.filter(ciudad='Talca').count(), 0)

    def test_acepta_texto_normal_con_apostrofo(self):
        respuesta = self.client.post(reverse('courier:sucursal_crear'), self.datos_sucursal())
        self.assertRedirects(respuesta, reverse('courier:sucursal_lista'))
        self.assertEqual(Sucursal.objects.get(ciudad='Talca').direccion, "Av. O'Higgins 123")

    def test_tipos_largos_y_formatos_invalidos_no_producen_error_500(self):
        casos = {'latitud': 'abc', 'email': 'no-es-correo', 'nombre': 'x' * 250}
        for campo, valor in casos.items():
            with self.subTest(campo=campo):
                respuesta = self.client.post(reverse('courier:sucursal_crear'), self.datos_sucursal(**{campo: valor}))
                self.assertEqual(respuesta.status_code, 200)
        respuesta = self.client.post(reverse('courier:vehiculo_crear'), {
            'tipo_vehiculo': self.camion.pk, 'patente': 'KLMN12', 'marca': 'X', 'modelo': 'Y',
            'anio': '1800', 'estado': 'robado'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Vehiculo.objects.filter(patente='KLMN-12').exists())

    def test_opcion_inexistente_en_un_select(self):
        respuesta = self.client.post(reverse('courier:vehiculo_crear'), {
            'tipo_vehiculo': 99999, 'patente': 'KLMN12', 'marca': 'X', 'modelo': 'Y', 'anio': '2020',
            'estado': 'operativo'})
        self.assertContains(respuesta, 'Seleccione una opción válida.')

    def test_valor_unico_duplicado(self):
        respuesta = self.client.post(reverse('courier:tipo_vehiculo_crear'), {'nombre': 'camión'})
        self.assertContains(respuesta, 'Ya existe un registro con este valor')

    def test_desmarcar_una_casilla_al_editar(self):
        self.client.post(reverse('courier:sucursal_editar', args=[self.valpo.pk]), {
            'nombre': self.valpo.nombre, 'direccion': 'Av. 2', 'ciudad': 'Valparaíso',
            'telefono': '+56 32 222 2222', 'email': 'valpo@musicpro.cl', 'latitud': '0', 'longitud': '0'})
        self.valpo.refresh_from_db()
        self.assertFalse(self.valpo.activa)


class ProteccionXSSTests(PruebaBase):
    def test_los_formularios_escapan_los_valores(self):
        # Aunque un dato peligroso llegara a la base (por ejemplo, cargado por otra vía),
        # la página lo muestra como texto y no como HTML.
        Sucursal.objects.filter(pk=self.valpo.pk).update(nombre='"><script>alert(1)</script>')
        self.iniciar_sesion()
        for url in (reverse('courier:sucursal_editar', args=[self.valpo.pk]), reverse('courier:envio_crear'),
                    reverse('courier:sucursal_lista')):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertNotContains(respuesta, '<script>alert(1)</script>')
                self.assertContains(respuesta, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_campo_renderizado_escapa_comillas(self):
        sucursal = Sucursal(nombre='a" onfocus="alert(1)', direccion='d', ciudad='c', telefono='1', email='a@b.cl')
        html = str(DatosSucursal(instance=sucursal)['nombre'])
        self.assertIn('&quot; onfocus=&quot;', html)
        self.assertNotIn('" onfocus="', html)


class CifradoDeDatosTests(PruebaBase):
    def test_rut_y_telefono_se_guardan_cifrados(self):
        conductor = Conductor.objects.create(rut='7.654.321-6', nombre='Lía', licencia='B', telefono='+56 9 1234 5678')
        with connection.cursor() as cursor:
            cursor.execute('SELECT rut, telefono FROM courier_conductor WHERE id = %s', [conductor.pk])
            rut_guardado, telefono_guardado = cursor.fetchone()
        self.assertNotIn('7.654.321', rut_guardado)
        self.assertNotIn('1234', telefono_guardado)
        conductor.refresh_from_db()
        self.assertEqual(conductor.rut, '7.654.321-6')
        self.assertEqual(conductor.telefono, '+56 9 1234 5678')

    def test_rut_duplicado_se_detecta_aunque_este_cifrado(self):
        self.iniciar_sesion()
        respuesta = self.client.post(reverse('courier:conductor_crear'), {
            'rut': '12345678-5', 'nombre': 'Copia', 'licencia': 'B', 'activo': 'on'})
        self.assertContains(respuesta, 'Ya existe un conductor con este RUT.')

    def test_busqueda_por_rut(self):
        self.iniciar_sesion()
        respuesta = self.client.get(reverse('courier:conductor_lista'), {'q': '12345678-5'})
        self.assertContains(respuesta, 'Ana Rojas')
        self.assertNotContains(respuesta, 'Pedro Soto')


class AcuerdoDeUsoDeDatosTests(PruebaBase):
    def setUp(self):
        self.nuevo = Usuario.objects.create_user('nuevo', 'n@musicpro.cl', CLAVE)
        self.client.force_login(self.nuevo)

    def test_sin_aceptar_no_puede_usar_el_sistema(self):
        respuesta = self.client.get(reverse('courier:envio_lista'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta['Location'].startswith(reverse('courier:acuerdo_datos')))

    def test_aceptar_registra_version_fecha_y_auditoria(self):
        destino = reverse('courier:envio_lista')
        respuesta = self.client.post(reverse('courier:acuerdo_datos'),
                                     {'acepto': 'on', 'decision': 'aceptar', 'next': destino})
        self.assertRedirects(respuesta, destino)
        perfil = PerfilUsuario.objects.get(usuario=self.nuevo)
        self.assertTrue(perfil.acepto_acuerdo_vigente)
        self.assertIsNotNone(perfil.acuerdo_aceptado_en)
        self.assertTrue(RegistroAuditoria.objects.filter(accion='acuerdo', usuario=self.nuevo).exists())

    def test_sin_marcar_la_casilla_no_se_acepta(self):
        respuesta = self.client.post(reverse('courier:acuerdo_datos'), {'decision': 'aceptar'})
        self.assertContains(respuesta, 'Debe marcar la casilla')
        self.assertFalse(PerfilUsuario.objects.get(usuario=self.nuevo).acepto_acuerdo_vigente)

    def test_rechazar_cierra_la_sesion(self):
        self.client.post(reverse('courier:acuerdo_datos'), {'decision': 'rechazar'})
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_no_redirige_a_sitios_externos(self):
        respuesta = self.client.post(reverse('courier:acuerdo_datos'),
                                     {'acepto': 'on', 'next': 'https://sitio-malicioso.com/'})
        self.assertRedirects(respuesta, reverse('courier:dashboard'))

    def test_politica_de_privacidad_es_publica(self):
        self.client.logout()
        respuesta = self.client.get(reverse('courier:privacidad'))
        self.assertContains(respuesta, 'Ley N.º 19.628')


class AuditoriaTests(PruebaBase):
    def test_login_logout_y_cambios_quedan_registrados(self):
        iniciar(self.client, 'operador', CLAVE)
        self.client.post(reverse('courier:tipo_vehiculo_crear'), {'nombre': 'Grúa'})
        self.client.post(reverse('logout'))
        acciones = list(RegistroAuditoria.objects.filter(username='operador').values_list('accion', flat=True))
        self.assertIn('login', acciones)
        self.assertIn('crear', acciones)
        self.assertIn('logout', acciones)
        self.assertEqual(RegistroAuditoria.objects.get(accion='crear').ip, '127.0.0.1')

    def test_intento_de_escalar_privilegios_queda_registrado(self):
        self.iniciar_sesion(self.operador)
        self.assertEqual(self.client.get(reverse('courier:usuario_lista')).status_code, 403)
        self.assertTrue(RegistroAuditoria.objects.filter(accion='acceso_denegado', usuario=self.operador).exists())

    def test_solo_administradores_ven_la_bitacora(self):
        self.iniciar_sesion(self.operador)
        self.assertEqual(self.client.get(reverse('courier:auditoria')).status_code, 403)
        self.iniciar_sesion(self.admin)
        respuesta = self.client.get(reverse('courier:auditoria'), {'accion': 'acceso_denegado'})
        self.assertContains(respuesta, 'operador')

    def test_los_registros_no_se_pueden_modificar(self):
        registro = RegistroAuditoria.objects.create(accion='login', username='x')
        registro.descripcion = 'alterado'
        with self.assertRaises(Exception):
            registro.save()


class CabecerasDeSeguridadTests(PruebaBase):
    def test_content_security_policy(self):
        respuesta = self.client.get(reverse('login'))
        politica = respuesta['Content-Security-Policy']
        # El login no tiene scripts en línea: solo se permiten archivos del propio sitio.
        self.assertIn("script-src 'self';", politica)
        self.assertIn("frame-ancestors 'none'", politica)
        self.assertEqual(respuesta['X-Frame-Options'], 'DENY')
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')

    def test_el_script_del_panel_lleva_nonce(self):
        self.iniciar_sesion()
        respuesta = self.client.get(reverse('courier:dashboard'))
        nonce = re.search(r"'nonce-([^']+)'", respuesta['Content-Security-Policy']).group(1)
        self.assertContains(respuesta, f'<script nonce="{nonce}">')
