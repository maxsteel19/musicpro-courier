"""Datos de los gráficos del panel y de los reportes."""
from django.test import SimpleTestCase
from django.urls import reverse

from courier import graficos

from .base import PruebaBase


class GraficosTests(SimpleTestCase):
    def test_escala_usa_numeros_redondos(self):
        self.assertEqual(graficos.escala(17), (20, [0, 5, 10, 15, 20]))
        self.assertEqual(graficos.escala(2), (2, [0, 1, 2]))
        self.assertEqual(graficos.escala(0), (1, [0, 1]))

    def test_barra_segmentada_reparte_el_total_en_orden_fijo(self):
        g = graficos.barra_segmentada(['Programado', 'En curso', 'Finalizado', 'Cancelado'], [10, 0, 30, 10],
                                      ['programado', 'en_curso', 'finalizado', 'cancelado'])
        self.assertEqual(g['total'], 50)
        self.assertEqual([p['clave'] for p in g['partes']], ['finalizado', 'programado', 'cancelado'])
        self.assertEqual(g['partes'][0]['cuota_txt'], '60 %')
        self.assertEqual(len(g['todas']), 4)  # la tabla incluye las partes en cero

    def test_ranking_ordena_de_mayor_a_menor(self):
        g = graficos.barras_ranking(['A', 'B', 'C'], [2, 8, 4])
        self.assertEqual([f['etiqueta'] for f in g['filas']], ['B', 'C', 'A'])
        self.assertEqual(g['filas'][0]['ancho'], 100)

    def test_columnas_rotulan_solo_maximo_y_ultimo(self):
        g = graficos.columnas(list('abcde'), [1, 9, 3, 0, 4])
        self.assertEqual([b['rotular'] for b in g['barras']], [False, True, False, False, True])

    def test_variacion_considera_si_subir_es_bueno(self):
        self.assertEqual(graficos.variacion(12, 10)['sentido'], 'bueno')
        self.assertEqual(graficos.variacion(12, 10, mayor_es_mejor=False)['sentido'], 'malo')
        self.assertEqual(graficos.variacion(5, 0)['sentido'], 'neutro')


class PanelPorPeriodoTests(PruebaBase):
    def test_todos_los_periodos_responden(self):
        self.iniciar_sesion()
        for periodo in ('7', '30', '90', '365'):
            with self.subTest(periodo=periodo):
                respuesta = self.client.get(reverse('courier:dashboard'), {'periodo': periodo})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context['periodo'], periodo)

    def test_periodo_invalido_usa_30_dias(self):
        self.iniciar_sesion()
        respuesta = self.client.get(reverse('courier:dashboard'), {'periodo': 'abc'})
        self.assertEqual(respuesta.context['periodo'], '30')
        self.assertEqual(len(respuesta.context['evolucion']['barras']), 30)

    def test_panel_cuenta_los_viajes_del_periodo(self):
        self.iniciar_sesion()
        contexto = self.client.get(reverse('courier:dashboard'), {'periodo': '7'}).context
        self.assertEqual(contexto['indicadores'][0]['valor'], 1)  # viaje finalizado hace 2 días
        self.assertEqual(contexto['por_estado']['total'], 2)       # + el programado a futuro
        self.assertEqual(contexto['top_conductores']['filas'][0]['etiqueta'], 'Ana Rojas')
