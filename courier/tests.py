from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Paquete


class CourierAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username='courier-admin',
            email='admin@example.com',
            password='SafeTestPassword-123!',
        )

    def test_admin_requires_authentication(self):
        response = self.client.get('/admin/courier/paquete/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_admin_supports_package_crud(self):
        self.client.force_login(self.admin_user)
        add_url = '/admin/courier/paquete/add/'
        package_data = {
            'codigo': 'TEST-001',
            'descripcion': 'Paquete de prueba',
            'peso': '1.25',
            'volumen': '0.50',
            'valor_declarado': '1000.00',
            'estado': 'preparacion',
            '_save': 'Guardar',
        }

        response = self.client.post(add_url, package_data)

        self.assertEqual(response.status_code, 302)
        package = Paquete.objects.get(codigo='TEST-001')
        changelist = self.client.get('/admin/courier/paquete/')
        self.assertContains(changelist, 'TEST-001')

        package_data['descripcion'] = 'Paquete actualizado'
        change_url = f'/admin/courier/paquete/{package.pk}/change/'
        response = self.client.post(change_url, package_data)

        self.assertEqual(response.status_code, 302)
        package.refresh_from_db()
        self.assertEqual(package.descripcion, 'Paquete actualizado')

        delete_url = f'/admin/courier/paquete/{package.pk}/delete/'
        response = self.client.post(delete_url, {'post': 'yes'})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Paquete.objects.filter(pk=package.pk).exists())