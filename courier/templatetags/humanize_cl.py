"""Filtros de plantilla con formato chileno."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def clp(valor):
    """Formatea un monto en pesos chilenos: 1250000 -> $1.250.000"""
    try:
        numero = int(Decimal(valor).quantize(Decimal('1')))
    except (InvalidOperation, TypeError, ValueError):
        return valor
    return '$' + f'{numero:,}'.replace(',', '.')


@register.filter
def duracion(td):
    """Convierte un timedelta en texto: 5 h 30 min"""
    if not td:
        return '—'
    minutos = int(td.total_seconds() // 60)
    horas, minutos = divmod(minutos, 60)
    return f'{horas} h {minutos:02d} min'


@register.filter
def porcentaje(parte, total):
    try:
        return round(float(parte) * 100 / float(total), 1) if total else 0
    except (TypeError, ValueError):
        return 0
