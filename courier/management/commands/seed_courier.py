from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from courier.models import Envio, Incidencia, Notificacion, Paquete, Sucursal


class Command(BaseCommand):
    help = 'Carga datos iniciales del sistema Courier para Music Pro'

    def handle(self, *args, **options):
        now = timezone.now()

        sucursales = {
            'sede': Sucursal.objects.get_or_create(
                nombre='Music Pro - Sede Principal',
                defaults={
                    'direccion': 'Av. Providencia 1234, Santiago',
                    'ciudad': 'Santiago',
                    'telefono': '+56 2 2345 6789',
                    'email': 'sede@musicpro.cl',
                    'latitud': -33.4489,
                    'longitud': -70.6422,
                    'activa': True,
                },
            )[0],
            'concepcion': Sucursal.objects.get_or_create(
                nombre='Music Pro - Sucursal Concepción',
                defaults={
                    'direccion': 'Calle Freire 456, Concepción',
                    'ciudad': 'Concepción',
                    'telefono': '+56 41 234 5678',
                    'email': 'concepcion@musicpro.cl',
                    'latitud': -36.8201,
                    'longitud': -73.0444,
                    'activa': True,
                },
            )[0],
            'valparaiso': Sucursal.objects.get_or_create(
                nombre='Music Pro - Sucursal Valparaíso',
                defaults={
                    'direccion': 'Av. Pedro Montt 789, Valparaíso',
                    'ciudad': 'Valparaíso',
                    'telefono': '+56 32 234 5678',
                    'email': 'valparaiso@musicpro.cl',
                    'latitud': -33.0472,
                    'longitud': -71.6127,
                    'activa': True,
                },
            )[0],
            'temuco': Sucursal.objects.get_or_create(
                nombre='Music Pro - Franquicia Temuco',
                defaults={
                    'direccion': 'Calle Arturo Prat 321, Temuco',
                    'ciudad': 'Temuco',
                    'telefono': '+56 45 234 5678',
                    'email': 'temuco@musicpro.cl',
                    'latitud': -38.7359,
                    'longitud': -72.5904,
                    'activa': True,
                },
            )[0],
            'antofagasta': Sucursal.objects.get_or_create(
                nombre='Music Pro - Franquicia Antofagasta',
                defaults={
                    'direccion': 'Av. Angamos 654, Antofagasta',
                    'ciudad': 'Antofagasta',
                    'telefono': '+56 55 234 5678',
                    'email': 'antofagasta@musicpro.cl',
                    'latitud': -23.6509,
                    'longitud': -70.3975,
                    'activa': True,
                },
            )[0],
        }

        paquetes = {
            'guitarra': Paquete.objects.get_or_create(
                codigo='PKG-2026-0001',
                defaults={
                    'descripcion': 'Guitarra Eléctrica Fender Stratocaster',
                    'peso': Decimal('5.5'),
                    'volumen': Decimal('0.08'),
                    'valor_declarado': Decimal('890000'),
                    'estado': 'preparacion',
                },
            )[0],
            'bateria': Paquete.objects.get_or_create(
                codigo='PKG-2026-0002',
                defaults={
                    'descripcion': 'Batería Electrónica Roland TD-17',
                    'peso': Decimal('25.0'),
                    'volumen': Decimal('0.45'),
                    'valor_declarado': Decimal('1250000'),
                    'estado': 'transito',
                },
            )[0],
            'amplificador': Paquete.objects.get_or_create(
                codigo='PKG-2026-0003',
                defaults={
                    'descripcion': 'Amplificador Marshall JCM 800',
                    'peso': Decimal('30.0'),
                    'volumen': Decimal('0.55'),
                    'valor_declarado': Decimal('750000'),
                    'estado': 'entregado',
                },
            )[0],
            'teclado': Paquete.objects.get_or_create(
                codigo='PKG-2026-0004',
                defaults={
                    'descripcion': 'Teclado Yamaha PSR-SX900',
                    'peso': Decimal('12.0'),
                    'volumen': Decimal('0.30'),
                    'valor_declarado': Decimal('680000'),
                    'estado': 'despachado',
                },
            )[0],
            'microfonos': Paquete.objects.get_or_create(
                codigo='PKG-2026-0005',
                defaults={
                    'descripcion': 'Micrófono Shure SM58 (x6)',
                    'peso': Decimal('3.5'),
                    'volumen': Decimal('0.05'),
                    'valor_declarado': Decimal('420000'),
                    'estado': 'preparacion',
                },
            )[0],
            'mesa': Paquete.objects.get_or_create(
                codigo='PKG-2026-0006',
                defaults={
                    'descripcion': 'Mesa de Mezclas Behringer X32',
                    'peso': Decimal('15.0'),
                    'volumen': Decimal('0.35'),
                    'valor_declarado': Decimal('950000'),
                    'estado': 'transito',
                },
            )[0],
            'cables': Paquete.objects.get_or_create(
                codigo='PKG-2026-0007',
                defaults={
                    'descripcion': 'Cable XLR 10m (x20)',
                    'peso': Decimal('8.0'),
                    'volumen': Decimal('0.15'),
                    'valor_declarado': Decimal('180000'),
                    'estado': 'entregado',
                },
            )[0],
            'bafles': Paquete.objects.get_or_create(
                codigo='PKG-2026-0008',
                defaults={
                    'descripcion': 'Par de Bafles JBL EON 615',
                    'peso': Decimal('45.0'),
                    'volumen': Decimal('0.90'),
                    'valor_declarado': Decimal('1650000'),
                    'estado': 'despachado',
                },
            )[0],
        }

        envios = {
            'env1': Envio.objects.get_or_create(
                numero_envio='ENV-2026-0001',
                defaults={
                    'sucursal_origen': sucursales['sede'],
                    'sucursal_destino': sucursales['concepcion'],
                    'paquete': paquetes['bateria'],
                    'estado': 'en_ruta',
                    'prioridad': 'alta',
                    'conductor': 'Carlos Muñoz',
                    'patente_vehiculo': 'AB-1234',
                    'progreso': 65,
                    'fecha_despacho': now,
                    'fecha_entrega_estimada': now,
                },
            )[0],
            'env2': Envio.objects.get_or_create(
                numero_envio='ENV-2026-0002',
                defaults={
                    'sucursal_origen': sucursales['sede'],
                    'sucursal_destino': sucursales['valparaiso'],
                    'paquete': paquetes['teclado'],
                    'estado': 'en_ruta',
                    'prioridad': 'media',
                    'conductor': 'María González',
                    'patente_vehiculo': 'CD-5678',
                    'progreso': 40,
                    'fecha_despacho': now,
                    'fecha_entrega_estimada': now,
                },
            )[0],
            'env3': Envio.objects.get_or_create(
                numero_envio='ENV-2026-0003',
                defaults={
                    'sucursal_origen': sucursales['sede'],
                    'sucursal_destino': sucursales['temuco'],
                    'paquete': paquetes['mesa'],
                    'estado': 'en_ruta',
                    'prioridad': 'urgente',
                    'conductor': 'Pedro Soto',
                    'patente_vehiculo': 'EF-9012',
                    'progreso': 80,
                    'fecha_despacho': now,
                    'fecha_entrega_estimada': now,
                },
            )[0],
            'env4': Envio.objects.get_or_create(
                numero_envio='ENV-2026-0004',
                defaults={
                    'sucursal_origen': sucursales['sede'],
                    'sucursal_destino': sucursales['antofagasta'],
                    'paquete': paquetes['bafles'],
                    'estado': 'en_ruta',
                    'prioridad': 'alta',
                    'conductor': 'Ana Reyes',
                    'patente_vehiculo': 'GH-3456',
                    'progreso': 25,
                    'fecha_despacho': now,
                    'fecha_entrega_estimada': now,
                },
            )[0],
            'env5': Envio.objects.get_or_create(
                numero_envio='ENV-2026-0005',
                defaults={
                    'sucursal_origen': sucursales['sede'],
                    'sucursal_destino': sucursales['concepcion'],
                    'paquete': paquetes['amplificador'],
                    'estado': 'entregado',
                    'prioridad': 'media',
                    'conductor': 'Luis Fernández',
                    'patente_vehiculo': 'IJ-7890',
                    'progreso': 100,
                    'fecha_despacho': now,
                    'fecha_entrega_estimada': now,
                    'fecha_entrega_real': now,
                },
            )[0],
            'env6': Envio.objects.get_or_create(
                numero_envio='ENV-2026-0006',
                defaults={
                    'sucursal_origen': sucursales['sede'],
                    'sucursal_destino': sucursales['valparaiso'],
                    'paquete': paquetes['cables'],
                    'estado': 'entregado',
                    'prioridad': 'baja',
                    'conductor': 'Roberto Díaz',
                    'patente_vehiculo': 'KL-1357',
                    'progreso': 100,
                    'fecha_despacho': now,
                    'fecha_entrega_estimada': now,
                    'fecha_entrega_real': now,
                },
            )[0],
        }

        Incidencia.objects.get_or_create(
            envio=envios['env1'],
            tipo='retraso',
            defaults={'descripcion': 'Retraso por congestión en Ruta 5 Sur', 'resuelta': False},
        )
        Incidencia.objects.get_or_create(
            envio=envios['env3'],
            tipo='mecanica',
            defaults={'descripcion': 'Cambio de neumático por pinchazo', 'resuelta': True},
        )
        Incidencia.objects.get_or_create(
            envio=envios['env2'],
            tipo='desvio',
            defaults={'descripcion': 'Desvío por corte de ruta por manifestación', 'resuelta': False},
        )

        Notificacion.objects.get_or_create(
            envio=envios['env1'],
            canal='email',
            defaults={'mensaje': 'Su paquete sale de bodega principal', 'enviada': True},
        )
        Notificacion.objects.get_or_create(
            envio=envios['env1'],
            canal='sms',
            defaults={'mensaje': 'Paquete en tránsito por Ruta 5 Sur', 'enviada': True},
        )
        Notificacion.objects.get_or_create(
            envio=envios['env3'],
            canal='push',
            defaults={'mensaje': 'Alerta: retraso mecánico en envío urgente', 'enviada': True},
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Seed completado: {Sucursal.objects.count()} sucursales, '
                f'{Paquete.objects.count()} paquetes, {Envio.objects.count()} envíos. '
                f'{Incidencia.objects.count()} incidencias, {Notificacion.objects.count()} notificaciones.'
            )
        )
