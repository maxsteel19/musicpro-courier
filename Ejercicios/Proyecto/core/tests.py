from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Cliente, DetallePedido, Pedido, Producto


class EvaluacionDjangoAdminTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin_eval',
            email='admin@eval.test',
            password='ClaveSegura123!',
        )
        self.cliente = Cliente.objects.create(
            nombre='Ana',
            apellido='Pérez',
            email='ana@example.com',
            telefono='987654321',
            direccion='Avenida Siempre Viva 123',
            activo=True,
        )
        self.producto = Producto.objects.create(
            codigo='P-001',
            nombre='Teclado mecánico',
            categoria='Tecnología',
            precio=59900,
            stock=15,
            activo=True,
        )

    def test_admin_requires_login(self):
        response = self.client.get('/admin/core/cliente/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_model_relationships_and_totals(self):
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            estado='pendiente',
            metodo_pago='tarjeta',
        )
        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=59900,
        )

        self.assertEqual(pedido.cliente.email, 'ana@example.com')
        self.assertEqual(pedido.total, 119800)
        self.assertEqual(pedido.detalles.count(), 1)

    def test_seed_command_creates_demo_data(self):
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/core/pedido/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedido')
