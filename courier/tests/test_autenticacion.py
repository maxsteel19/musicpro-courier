"""Énfasis de la Evaluación 3: autenticación, sesión y control de acceso."""
from django.contrib.auth import SESSION_KEY
from django.urls import reverse

from .base import CLAVE, PruebaBase, Usuario


def urls_protegidas(prueba):
    """Todas las URLs del sistema que exigen sesión iniciada."""
    pk = {
        'sucursal': prueba.santiago.pk, 'paquete': prueba.paquete.pk, 'envio': prueba.envio.pk,
        'incidencia': prueba.incidencia.pk, 'notificacion': prueba.notificacion.pk,
        'tipo_vehiculo': prueba.camion.pk, 'vehiculo': prueba.vehiculo.pk,
        'conductor': prueba.conductor.pk, 'viaje': prueba.viaje.pk,
    }
    urls = [reverse(f'courier:{n}') for n in (
        'dashboard', 'perfil', 'seguimiento', 'reportes', 'api_envios', 'api_sucursales', 'api_kpis',
        'usuario_lista', 'usuario_crear',
    )]
    urls.append(reverse('password_cambiar'))
    urls.append(reverse('courier:reporte_detalle', args=[1]))
    for entidad, clave in pk.items():
        urls += [reverse(f'courier:{entidad}_lista'), reverse(f'courier:{entidad}_crear'),
                 reverse(f'courier:{entidad}_editar', args=[clave]),
                 reverse(f'courier:{entidad}_eliminar', args=[clave])]
    urls += [reverse('courier:envio_detalle', args=[prueba.envio.pk]),
             reverse('courier:viaje_detalle', args=[prueba.viaje.pk]),
             reverse('courier:usuario_editar', args=[prueba.operador.pk]),
             reverse('courier:usuario_password', args=[prueba.operador.pk]),
             reverse('courier:usuario_eliminar', args=[prueba.operador.pk])]
    return urls


class InicioDeSesionTests(PruebaBase):
    def test_pagina_login_disponible(self):
        respuesta = self.client.get(reverse('login'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Iniciar sesión')

    def test_login_correcto_crea_sesion_y_redirige_al_panel(self):
        respuesta = self.client.post(reverse('login'), {'username': 'operador', 'password': CLAVE})
        self.assertRedirects(respuesta, reverse('courier:dashboard'))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.operador.pk)
        self.assertIn('inicio_sesion', self.client.session)

    def test_login_con_clave_incorrecta_no_autentica(self):
        respuesta = self.client.post(reverse('login'), {'username': 'operador', 'password': 'incorrecta'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_usuario_desactivado_no_puede_ingresar(self):
        Usuario.objects.filter(pk=self.operador.pk).update(is_active=False)
        self.client.post(reverse('login'), {'username': 'operador', 'password': CLAVE})
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_respeta_parametro_next(self):
        destino = reverse('courier:viaje_lista')
        respuesta = self.client.post(f"{reverse('login')}?next={destino}",
                                     {'username': 'operador', 'password': CLAVE, 'next': destino})
        self.assertRedirects(respuesta, destino)

    def test_login_no_redirige_a_sitios_externos(self):
        respuesta = self.client.post(reverse('login'), {
            'username': 'operador', 'password': CLAVE, 'next': 'https://sitio-malicioso.com/'})
        self.assertRedirects(respuesta, reverse('courier:dashboard'))

    def test_usuario_autenticado_que_abre_login_va_al_panel(self):
        self.iniciar_sesion()
        self.assertRedirects(self.client.get(reverse('login')), reverse('courier:dashboard'))

    def test_login_cambia_el_identificador_de_sesion(self):
        # Protección contra fijación de sesión: el id anónimo no se reutiliza.
        sesion = self.client.session
        sesion['visita'] = True
        sesion.save()
        clave_anonima = sesion.session_key
        self.client.post(reverse('login'), {'username': 'operador', 'password': CLAVE})
        self.assertNotEqual(self.client.session.session_key, clave_anonima)


class ProteccionDeVistasTests(PruebaBase):
    def test_vistas_protegidas_redirigen_al_login_sin_sesion(self):
        for url in urls_protegidas(self):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta['Location'].startswith(reverse('login')))
                self.assertIn('next=', respuesta['Location'])

    def test_post_sin_sesion_no_modifica_la_base_de_datos(self):
        self.client.post(reverse('courier:sucursal_eliminar', args=[self.valpo.pk]))
        self.client.post(reverse('courier:conductor_crear'), {
            'rut': '7.654.321-6', 'nombre': 'Intruso', 'licencia': 'B', 'activo': 'on'})
        self.assertTrue(self.valpo.__class__.objects.filter(pk=self.valpo.pk).exists())
        self.assertFalse(self.conductor.__class__.objects.filter(nombre='Intruso').exists())

    def test_pagina_publica_no_requiere_sesion_ni_expone_envios(self):
        respuesta = self.client.get(reverse('courier:inicio'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, self.envio.numero_envio)

    def test_usuario_autenticado_accede_a_las_vistas(self):
        self.iniciar_sesion(self.admin)
        for url in urls_protegidas(self):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_paginas_privadas_no_se_guardan_en_cache(self):
        self.iniciar_sesion()
        respuesta = self.client.get(reverse('courier:dashboard'))
        self.assertIn('no-store', respuesta['Cache-Control'])


class CierreDeSesionTests(PruebaBase):
    def test_logout_por_get_no_esta_permitido(self):
        self.iniciar_sesion()
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_logout_cierra_sesion_y_quita_el_acceso(self):
        self.client.post(reverse('login'), {'username': 'operador', 'password': CLAVE})
        self.assertEqual(self.client.get(reverse('courier:dashboard')).status_code, 200)

        respuesta = self.client.post(reverse('logout'))
        self.assertRedirects(respuesta, reverse('login'))
        self.assertNotIn(SESSION_KEY, self.client.session)

        # Después de cerrar sesión ya no puede entrar a las vistas protegidas.
        respuesta = self.client.get(reverse('courier:dashboard'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta['Location'].startswith(reverse('login')))


class SesionYPerfilTests(PruebaBase):
    def test_perfil_muestra_al_usuario_identificado_por_la_sesion(self):
        self.client.post(reverse('login'), {'username': 'operador', 'password': CLAVE})
        respuesta = self.client.get(reverse('courier:perfil'))
        self.assertContains(respuesta, 'operador')
        self.assertEqual(respuesta.context['user'], self.operador)

    def test_cambio_de_clave_propia_mantiene_la_sesion(self):
        self.client.post(reverse('login'), {'username': 'operador', 'password': CLAVE})
        respuesta = self.client.post(reverse('password_cambiar'), {
            'old_password': CLAVE, 'new_password1': 'OtraClave-2026!', 'new_password2': 'OtraClave-2026!'})
        self.assertRedirects(respuesta, reverse('courier:perfil'))
        self.assertEqual(self.client.get(reverse('courier:dashboard')).status_code, 200)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password('OtraClave-2026!'))

    def test_registro_guarda_al_usuario_de_la_sesion(self):
        self.iniciar_sesion()
        self.client.post(reverse('courier:incidencia_crear'), {
            'envio': self.envio.pk, 'tipo': 'danio', 'descripcion': 'Caja golpeada'})
        incidencia = self.incidencia.__class__.objects.get(descripcion='Caja golpeada')
        self.assertEqual(incidencia.reportada_por, self.operador)
