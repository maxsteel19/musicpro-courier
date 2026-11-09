"""Mantenedor propio de usuarios (solo administradores)."""
from django.urls import reverse

from .base import CLAVE, PruebaBase, Usuario


class AccesoMantenedorUsuariosTests(PruebaBase):
    def test_operador_recibe_403(self):
        self.iniciar_sesion(self.operador)
        for url in (reverse('courier:usuario_lista'), reverse('courier:usuario_crear'),
                    reverse('courier:usuario_editar', args=[self.admin.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_operador_no_ve_el_menu_de_usuarios(self):
        self.iniciar_sesion(self.operador)
        self.assertNotContains(self.client.get(reverse('courier:dashboard')), reverse('courier:usuario_lista'))

    def test_administrador_ve_el_listado(self):
        self.iniciar_sesion(self.admin)
        respuesta = self.client.get(reverse('courier:usuario_lista'))
        self.assertContains(respuesta, 'operador')


class CrudUsuariosTests(PruebaBase):
    def setUp(self):
        self.iniciar_sesion(self.admin)

    def test_crear_usuario_con_clave_cifrada(self):
        respuesta = self.client.post(reverse('courier:usuario_crear'), {
            'username': 'nuevo', 'first_name': 'Nora', 'last_name': 'Paz', 'email': 'nora@musicpro.cl',
            'is_active': 'on', 'password1': 'ClaveNueva-2026!', 'password2': 'ClaveNueva-2026!',
        })
        self.assertRedirects(respuesta, reverse('courier:usuario_lista'))
        usuario = Usuario.objects.get(username='nuevo')
        self.assertNotEqual(usuario.password, 'ClaveNueva-2026!')
        self.assertTrue(usuario.check_password('ClaveNueva-2026!'))
        self.assertFalse(usuario.is_staff)

    def test_crear_usuario_rechaza_clave_debil(self):
        respuesta = self.client.post(reverse('courier:usuario_crear'), {
            'username': 'debil', 'email': 'd@musicpro.cl', 'password1': '123', 'password2': '123',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username='debil').exists())

    def test_editar_usuario(self):
        self.client.post(reverse('courier:usuario_editar', args=[self.operador.pk]), {
            'username': 'operador', 'first_name': 'Olga', 'last_name': 'Pérez', 'email': 'olga@musicpro.cl',
            'is_active': 'on', 'is_staff': 'on',
        })
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.first_name, 'Olga')
        self.assertTrue(self.operador.is_staff)

    def test_administrador_no_puede_quitarse_su_propio_rol(self):
        self.client.post(reverse('courier:usuario_editar', args=[self.admin.pk]), {
            'username': 'admin', 'email': 'admin@musicpro.cl',  # sin is_staff ni is_active
        })
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.is_active)

    def test_desactivar_y_reactivar_usuario(self):
        url = reverse('courier:usuario_cambiar_estado', args=[self.operador.pk])
        self.assertEqual(self.client.get(url).status_code, 405)  # solo POST
        self.client.post(url)
        self.operador.refresh_from_db()
        self.assertFalse(self.operador.is_active)
        self.client.post(url)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.is_active)

    def test_usuario_desactivado_pierde_el_acceso(self):
        self.client.post(reverse('courier:usuario_cambiar_estado', args=[self.operador.pk]))
        otro_cliente = self.client_class()
        otro_cliente.post(reverse('login'), {'username': 'operador', 'password': CLAVE})
        self.assertEqual(otro_cliente.get(reverse('courier:dashboard')).status_code, 302)

    def test_no_puede_desactivarse_ni_eliminarse_a_si_mismo(self):
        self.client.post(reverse('courier:usuario_cambiar_estado', args=[self.admin.pk]))
        self.client.post(reverse('courier:usuario_eliminar', args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_cambiar_clave_de_otro_usuario(self):
        self.client.post(reverse('courier:usuario_password', args=[self.operador.pk]), {
            'new_password1': 'Renovada-2026!', 'new_password2': 'Renovada-2026!'})
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password('Renovada-2026!'))

    def test_eliminar_usuario(self):
        self.assertEqual(self.client.get(reverse('courier:usuario_eliminar', args=[self.operador.pk])).status_code, 200)
        self.client.post(reverse('courier:usuario_eliminar', args=[self.operador.pk]))
        self.assertFalse(Usuario.objects.filter(pk=self.operador.pk).exists())

    def test_administrador_normal_no_puede_modificar_superusuario(self):
        for url in (reverse('courier:usuario_editar', args=[self.superusuario.pk]),
                    reverse('courier:usuario_password', args=[self.superusuario.pk]),
                    reverse('courier:usuario_eliminar', args=[self.superusuario.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.client.post(reverse('courier:usuario_cambiar_estado', args=[self.superusuario.pk]))
        self.superusuario.refresh_from_db()
        self.assertTrue(self.superusuario.is_active)
