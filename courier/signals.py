"""Señales de autenticación de Django conectadas a la bitácora de auditoría.

Los intentos fallidos se registran en el formulario de login
(``courier/views/cuentas.py``), donde también se aplica el bloqueo.
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .auditoria import registrar


@receiver(user_logged_in, dispatch_uid='courier_auditoria_login')
def auditar_inicio_de_sesion(sender, request, user, **kwargs):
    registrar(request, 'login', usuario=user, descripcion='Inicio de sesión correcto.')


@receiver(user_logged_out, dispatch_uid='courier_auditoria_logout')
def auditar_cierre_de_sesion(sender, request, user, **kwargs):
    if user is not None:
        registrar(request, 'logout', usuario=user, descripcion='Cierre de sesión.')
