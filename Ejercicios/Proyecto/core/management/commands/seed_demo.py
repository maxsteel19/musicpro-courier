from django.core.management.base import BaseCommand
from faker import Faker

from core.models import Cliente, Producto, Pedido, DetallePedido


class Command(BaseCommand):
    help = 'Genera datos ficticios para probar la aplicación Django Admin.'

    def handle(self, *args, **options):
        DetallePedido.objects.all().delete()
        Pedido.objects.all().delete()
        Producto.objects.all().delete()
        Cliente.objects.all().delete()

        fake = Faker('es_ES')

        clientes = []
        for _ in range(100):
            cliente = Cliente.objects.create(
                nombre=fake.first_name(),
                apellido=fake.last_name(),
                email=fake.email(),
                telefono=fake.phone_number()[:20],
                direccion=fake.address(),
                activo=True,
            )
            clientes.append(cliente)

        productos = []
        for i in range(100):
            producto = Producto.objects.create(
                codigo=f'PROD-{i + 1:03d}',
                nombre=' '.join(fake.words(nb=2)).title(),
                categoria=fake.random_element(elements=['Tecnología', 'Hogar', 'Deportes', 'Música', 'Oficina']),
                precio=fake.random_int(1000, 500000),
                stock=fake.random_int(5, 200),
                activo=True,
            )
            productos.append(producto)

        for _ in range(100):
            pedido = Pedido.objects.create(
                cliente=fake.random_element(clientes),
                estado=fake.random_element(elements=['pendiente', 'procesado', 'enviado', 'entregado', 'cancelado']),
                metodo_pago=fake.random_element(elements=['efectivo', 'tarjeta', 'transferencia']),
            )

            for _ in range(fake.random_int(1, 4)):
                producto = fake.random_element(productos)
                cantidad = fake.random_int(1, 5)
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                )

            pedido.guardar_total()

        self.stdout.write(
            self.style.SUCCESS(
                'Datos ficticios generados correctamente: 100 clientes, '
                '100 productos y 100 pedidos.'
            )
        )
