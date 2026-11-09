"""Validaciones y normalizaciones propias del contexto chileno."""
import re

from django.core.exceptions import ValidationError


def calcular_digito_verificador(cuerpo):
    """Calcula el dígito verificador de un RUT con el algoritmo módulo 11."""
    suma = 0
    multiplicador = 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return '0'
    if resto == 10:
        return 'K'
    return str(resto)


def normalizar_rut(valor):
    """Valida un RUT y lo devuelve con formato ``12.345.678-9``."""
    limpio = re.sub(r'[^0-9kK]', '', valor or '').upper()
    if len(limpio) < 2 or not limpio[:-1].isdigit():
        raise ValidationError('Ingrese un RUT válido, por ejemplo 12.345.678-5.')
    cuerpo, dv = limpio[:-1], limpio[-1]
    if calcular_digito_verificador(cuerpo) != dv:
        raise ValidationError('El dígito verificador del RUT no es correcto.')
    cuerpo_con_puntos = f'{int(cuerpo):,}'.replace(',', '.')
    return f'{cuerpo_con_puntos}-{dv}'


PATENTE_NUEVA = re.compile(r'^[A-Z]{4}\d{2}$')    # BCDF12  -> BCDF-12
PATENTE_ANTIGUA = re.compile(r'^[A-Z]{2}\d{4}$')  # AB1234  -> AB-1234


def normalizar_patente(valor):
    """Valida una patente chilena (formato antiguo o nuevo) y la normaliza."""
    limpio = re.sub(r'[^0-9A-Za-z]', '', valor or '').upper()
    if PATENTE_NUEVA.match(limpio):
        return f'{limpio[:4]}-{limpio[4:]}'
    if PATENTE_ANTIGUA.match(limpio):
        return f'{limpio[:2]}-{limpio[2:]}'
    raise ValidationError('Patente inválida. Use el formato BCDF-12 o AB-1234.')
