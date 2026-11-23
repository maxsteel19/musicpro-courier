"""Bitácora de seguridad: quién hizo qué, cuándo y desde qué IP.

La pide la "Guía para la construcción del Prototipo Funcional" del curso en
relación con la Ley 21.459 de delitos informáticos: permite reconstruir un
acceso no autorizado o un cambio indebido en los datos.
"""
from .models import RegistroAuditoria


def ip_cliente(request):
    """IP de la conexión.

    No se usa la cabecera X-Forwarded-For porque el cliente puede escribirla
    a su gusto. Si el sistema se publica detrás de un proxy, hay que
    configurar el proxy para que entregue la IP real.
    """
    if request is None:
        return None
    return request.META.get('REMOTE_ADDR') or None


def registrar(request, accion, *, usuario=None, username='', objeto=None, modelo='', objeto_id='',
              descripcion=''):
    """Agrega un registro a la bitácora de auditoría."""
    if usuario is None and request is not None:
        usuario_sesion = getattr(request, 'user', None)
        if usuario_sesion is not None and usuario_sesion.is_authenticated:
            usuario = usuario_sesion
    if objeto is not None:
        modelo = modelo or str(objeto._meta.verbose_name)
        objeto_id = objeto_id or (str(objeto.pk) if objeto.pk is not None else '')
    navegador = request.META.get('HTTP_USER_AGENT', '') if request is not None else ''
    return RegistroAuditoria.objects.create(
        usuario=usuario,
        username=(username or getattr(usuario, 'username', ''))[:150],
        accion=accion,
        modelo=str(modelo)[:60],
        objeto_id=str(objeto_id)[:40],
        descripcion=str(descripcion)[:300],
        ip=ip_cliente(request),
        navegador=navegador[:200],
    )
