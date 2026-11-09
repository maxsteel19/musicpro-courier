"""Parte 2: los 20 reportes del informe ORM (proyecto Transporte)."""
from datetime import datetime, time, timedelta

from django.urls import reverse
from django.utils import timezone

from courier.models import Viaje
from courier.reportes import REPORTES

from .base import PruebaBase


class ReportesTests(PruebaBase):
    def parametros(self, **extra):
        hoy = timezone.localdate()
        p = {
            'tipo': self.camion, 'vehiculo': self.vehiculo, 'conductor': self.conductor, 'anio': hoy.year,
            'inicio': timezone.make_aware(datetime.combine(hoy - timedelta(days=7), time.min)),
            'fin': timezone.make_aware(datetime.combine(hoy + timedelta(days=1), time.min)),
        }
        p.update(extra)
        return p

    def test_hay_20_reportes(self):
        self.assertEqual(sorted(REPORTES), list(range(1, 21)))

    def test_todas_las_paginas_de_reporte_responden(self):
        self.iniciar_sesion()
        self.assertContains(self.client.get(reverse('courier:reportes')), 'Informe de consultas ORM')
        for numero in REPORTES:
            with self.subTest(reporte=numero):
                respuesta = self.client.get(reverse('courier:reporte_detalle', args=[numero]))
                self.assertEqual(respuesta.status_code, 200)
                self.assertIsNotNone(respuesta.context['resultado'])
                self.assertTrue(respuesta.context['consultas'], 'Debe mostrar el SQL generado por el ORM')

    def test_reporte_con_parametros_enviados(self):
        self.iniciar_sesion()
        respuesta = self.client.get(reverse('courier:reporte_detalle', args=[2]), {'tipo': self.furgon.pk})
        self.assertContains(respuesta, 'AB-1234')
        self.assertNotContains(respuesta, 'BCDF-12')

    def test_reporte_inexistente(self):
        self.iniciar_sesion()
        self.assertEqual(self.client.get(reverse('courier:reporte_detalle', args=[99])).status_code, 404)

    def test_resultados_correctos(self):
        p = self.parametros()
        self.assertEqual(REPORTES[1].funcion(p).filas.__len__(), 2)
        self.assertEqual([f[0] for f in REPORTES[2].funcion(p).filas], ['BCDF-12'])
        self.assertEqual([f[0] for f in REPORTES[4].funcion(p).filas], ['AB-1234', 'BCDF-12'])
        self.assertEqual(REPORTES[5].funcion(p).filas[0], ['Total registrados', 2])
        self.assertEqual(len(REPORTES[6].funcion(p).filas), 2)
        estados = dict(REPORTES[8].funcion(p).filas)
        self.assertEqual(estados, {'Programado': 1, 'En curso': 0, 'Finalizado': 1, 'Cancelado': 0})
        self.assertEqual(len(REPORTES[9].funcion(p).filas), 1)  # solo el viaje de hace 2 días
        self.assertEqual([f[0] for f in REPORTES[10].funcion(p).filas], ['AB-1234'])
        self.assertEqual(REPORTES[11].funcion(p).filas[0][1:4], ['Ana Rojas', '12.345.678-5', 2])
        self.assertEqual([f[0] for f in REPORTES[16].funcion(p).filas], ['Pedro Soto'])
        self.assertIn('2 h 00 min', REPORTES[17].funcion(p).resumen)
        porcentajes = REPORTES[19].funcion(p).filas
        self.assertEqual(porcentajes[0][2], '50.0 %')

    def test_distribucion_mensual(self):
        anio = timezone.localdate().year - 1
        zona = timezone.get_current_timezone()
        for mes, dia in ((3, 5), (3, 20), (7, 1)):
            Viaje.objects.create(vehiculo=self.vehiculo, conductor=self.conductor, origen='A', destino='B',
                                 fecha_salida=datetime(anio, mes, dia, 0, 30, tzinfo=zona), estado='finalizado',
                                 fecha_llegada=datetime(anio, mes, dia, 5, 0, tzinfo=zona))
        filas = dict(REPORTES[20].funcion(self.parametros(anio=anio)).filas)
        self.assertEqual(filas['Mar'], 2)
        self.assertEqual(filas['Jul'], 1)
        self.assertEqual(sum(filas.values()), 3)
        ranking = REPORTES[18].funcion(self.parametros(anio=anio)).filas
        self.assertEqual(ranking[0][3], 3)
