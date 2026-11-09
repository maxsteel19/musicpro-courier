"""Preparación de datos para los gráficos del panel y de los reportes.

Los gráficos se dibujan con HTML/CSS en las plantillas (sin librerías
externas). Este módulo solo calcula proporciones, escalas y etiquetas a
partir de listas de etiquetas y valores que ya vienen del ORM.

Formas elegidas según lo que el lector necesita hacer:
- Reparto de un total (viajes por estado) -> barra segmentada.
- Comparar y ordenar categorías (tipos, conductores, destinos) -> barras horizontales.
- Evolución en el tiempo -> columnas con eje y líneas guía finas.
"""
import math

# Colores por estado de viaje (validados contra el fondo oscuro de las tarjetas).
# El orden de los segmentos también está validado para daltonismo.
ESTADOS_VIAJE = {
    'finalizado': {'color': 'var(--viz-finalizado)', 'icono': 'fa-circle-check', 'texto_oscuro': False},
    'en_curso': {'color': 'var(--viz-en-curso)', 'icono': 'fa-truck-moving', 'texto_oscuro': False},
    'programado': {'color': 'var(--viz-programado)', 'icono': 'fa-clock', 'texto_oscuro': True},
    'pendiente': {'color': 'var(--viz-programado)', 'icono': 'fa-clock', 'texto_oscuro': True},
    'cancelado': {'color': 'var(--viz-cancelado)', 'icono': 'fa-ban', 'texto_oscuro': False},
}
ORDEN_ESTADOS = ['finalizado', 'en_curso', 'programado', 'pendiente', 'cancelado']

# Ancho mínimo (en % del total) para imprimir el porcentaje dentro de un segmento.
MINIMO_PARA_ROTULO = 9


def formato_numero(valor):
    """Formato chileno: 1.234 / 12,5"""
    if isinstance(valor, float) and not valor.is_integer():
        return f'{valor:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'{int(valor):,}'.replace(',', '.')


def _porcentaje(parte, total):
    return round(parte * 100 / total, 1) if total else 0


def escala(maximo, divisiones=4):
    """Devuelve (tope, marcas) con números "redondos" para el eje Y."""
    if maximo <= 0:
        return 1, [0, 1]
    maximo = math.ceil(maximo)
    paso_bruto = maximo / divisiones
    magnitud = 10 ** math.floor(math.log10(paso_bruto))
    paso = next(m * magnitud for m in (1, 2, 5, 10) if paso_bruto <= m * magnitud)
    paso = max(1, int(round(paso)))  # se grafican conteos: marcas enteras
    tope = math.ceil(maximo / paso) * paso
    marcas = [paso * i for i in range(tope // paso + 1)]
    return tope, marcas


def barra_segmentada(etiquetas, valores, claves=None):
    """Reparto de un total en partes (máximo 6).

    ``claves`` (p. ej. códigos de estado) asigna colores fijos; si no se
    entregan, se usan los colores categóricos en orden.
    """
    total = sum(valores)
    partes = []
    for i, (etiqueta, valor) in enumerate(zip(etiquetas, valores)):
        clave = claves[i] if claves else None
        estilo = ESTADOS_VIAJE.get(clave, {
            'color': f'var(--viz-serie-{i + 1})', 'icono': 'fa-square', 'texto_oscuro': i == 3,
        })
        cuota = _porcentaje(valor, total)
        partes.append({
            'clave': clave, 'etiqueta': etiqueta, 'valor': valor, 'valor_txt': formato_numero(valor),
            'cuota': cuota, 'cuota_txt': f'{formato_numero(cuota)} %', 'color': estilo['color'],
            'icono': estilo['icono'], 'texto_oscuro': estilo['texto_oscuro'],
            'rotular': cuota >= MINIMO_PARA_ROTULO,
        })
    if claves:
        partes.sort(key=lambda p: ORDEN_ESTADOS.index(p['clave']) if p['clave'] in ORDEN_ESTADOS else 99)
    return {'tipo': 'segmentos', 'total': total, 'total_txt': formato_numero(total),
            'partes': [p for p in partes if p['valor'] > 0], 'todas': partes}


def barras_ranking(etiquetas, valores, detalles=None, total=None):
    """Barras horizontales ordenadas de mayor a menor (un solo color)."""
    filas = sorted(zip(etiquetas, valores, detalles or [''] * len(valores)), key=lambda f: -f[1])
    maximo = max((v for _, v, _ in filas), default=0)
    referencia = total if total is not None else sum(valores)
    return {'tipo': 'ranking', 'filas': [{
        'posicion': i, 'etiqueta': etiqueta, 'detalle': detalle, 'valor': valor, 'valor_txt': formato_numero(valor),
        'ancho': round(valor * 100 / maximo, 2) if maximo else 0,
        'cuota_txt': f'{formato_numero(_porcentaje(valor, referencia))} %',
    } for i, (etiqueta, valor, detalle) in enumerate(filas, start=1)]}


def columnas(etiquetas, valores, maximo_etiquetas=8, unidad='viajes'):
    """Columnas verticales para una serie en el tiempo.

    Se rotulan solo el valor máximo y el último (no un número en cada barra);
    el resto se lee en el eje, en el tooltip o en la tabla.
    """
    tope, marcas = escala(max(valores, default=0))
    n = len(valores)
    cada = max(1, math.ceil(n / maximo_etiquetas))
    indice_max = valores.index(max(valores)) if n and max(valores) > 0 else None
    barras = []
    for i, (etiqueta, valor) in enumerate(zip(etiquetas, valores)):
        desde_el_final = n - 1 - i
        barras.append({
            'etiqueta': etiqueta, 'valor': valor, 'valor_txt': formato_numero(valor),
            'alto': round(valor * 100 / tope, 2) if tope else 0,
            'mostrar_eje': desde_el_final % cada == 0,
            # En pantallas angostas se oculta una de cada dos etiquetas del eje.
            'eje_alterno': desde_el_final % (2 * cada) != 0,
            'rotular': valor > 0 and (i == indice_max or i == n - 1),
        })
    promedio = sum(valores) / n if n else 0
    return {
        'tipo': 'columnas', 'barras': barras, 'unidad': unidad,
        'marcas': [{'valor': formato_numero(m), 'pos': round(m * 100 / tope, 2)} for m in marcas],
        'total_txt': formato_numero(sum(valores)), 'promedio_txt': formato_numero(round(promedio, 1)),
    }


def sparkline(valores, ancho=120, alto=30, margen=4):
    """Puntos de una línea pequeña (SVG) para los indicadores."""
    if not valores:
        return None
    maximo = max(valores) or 1
    paso = (ancho - 2 * margen) / max(1, len(valores) - 1)
    puntos = [(round(margen + i * paso, 1), round(alto - margen - v * (alto - 2 * margen) / maximo, 1))
              for i, v in enumerate(valores)]
    return {'ancho': ancho, 'alto': alto, 'puntos': ' '.join(f'{x},{y}' for x, y in puntos),
            'ultimo_x': puntos[-1][0], 'ultimo_y': puntos[-1][1]}


def variacion(actual, anterior, mayor_es_mejor=True, en_puntos=False):
    """Cambio respecto del período anterior, con su sentido (bueno/malo)."""
    if anterior in (None, 0) and not en_puntos:
        return {'texto': 'sin datos del período anterior', 'sentido': 'neutro', 'icono': 'fa-minus', 'sin_base': True}
    diferencia = actual - anterior
    cambio = diferencia if en_puntos else diferencia * 100 / anterior
    if abs(cambio) < 0.05:
        return {'texto': 'sin cambios', 'sentido': 'neutro', 'icono': 'fa-minus'}
    signo = '+' if cambio > 0 else '−'
    unidad = ' pp' if en_puntos else ' %'
    bueno = (cambio > 0) == mayor_es_mejor
    return {
        'texto': f'{signo}{formato_numero(round(abs(cambio), 1))}{unidad}',
        'sentido': 'bueno' if bueno else 'malo',
        'icono': 'fa-arrow-trend-up' if cambio > 0 else 'fa-arrow-trend-down',
    }


def desde_resultado(grafico):
    """Convierte el gráfico declarado por un reporte en datos para la plantilla."""
    if not grafico:
        return None
    tipo = grafico.get('tipo')
    etiquetas, valores = grafico.get('etiquetas', []), grafico.get('valores', [])
    if tipo == 'segmentos':
        return barra_segmentada(etiquetas, valores, grafico.get('claves'))
    if tipo == 'columnas':
        return columnas(etiquetas, valores, maximo_etiquetas=12)
    return barras_ranking(etiquetas, valores)
