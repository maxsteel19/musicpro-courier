"""Cifrado de datos personales en la base de datos (pauta OWASP A02).

Se usa Fernet de la librería ``cryptography`` (AES-128 en modo CBC con
autenticación HMAC-SHA256). La clave se lee de ``DJANGO_CLAVE_CIFRADO`` en el
archivo ``.env``; nunca se escribe en el código.

- ``CampoCifrado`` guarda el texto cifrado y lo descifra al leerlo, así el
  resto del código (vistas, reportes, plantillas) trabaja con el valor normal.
- Como cada cifrado produce un texto distinto, no se puede buscar ni exigir
  unicidad sobre el valor cifrado. Para eso existe ``huella()``: un HMAC
  determinista que permite comparar sin guardar el dato en claro.
"""
import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


@lru_cache(maxsize=1)
def _fernet():
    return Fernet(settings.CLAVE_CIFRADO_DATOS.encode('ascii'))


@lru_cache(maxsize=1)
def _clave_huella():
    # Clave derivada distinta de la de cifrado (no se reutiliza la misma clave
    # para dos propósitos criptográficos diferentes).
    return hashlib.sha256(b'huella:' + settings.CLAVE_CIFRADO_DATOS.encode('ascii')).digest()


def cifrar(texto):
    return _fernet().encrypt(str(texto).encode('utf-8')).decode('ascii')


def descifrar(token):
    try:
        return _fernet().decrypt(token.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeEncodeError):
        # Dato guardado antes de activar el cifrado: se devuelve tal cual.
        return token


def huella(texto):
    """HMAC-SHA256 del texto (64 caracteres hexadecimales)."""
    return hmac.new(_clave_huella(), str(texto).encode('utf-8'), hashlib.sha256).hexdigest()


class CampoCifrado(models.TextField):
    """Campo de texto que se guarda cifrado en la base de datos."""

    description = 'Texto cifrado con Fernet (AES + HMAC)'

    def from_db_value(self, value, expression, connection):
        if value in (None, ''):
            return value
        return descifrar(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ''):
            return value
        return cifrar(value)
