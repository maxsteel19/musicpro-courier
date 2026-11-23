"""Mantenedor de usuarios propio (crear, consultar, modificar, desactivar y eliminar)
y bitácora de auditoría.

Solo pueden usarlo los administradores: el decorador ``@administrador_requerido``
exige sesión iniciada (``login_required``) y rol staff/superusuario.
"""
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods, require_POST

from ..auditoria import registrar
from ..decorators import administrador_requerido
from ..entradas import DatosCrearUsuario, DatosEditarUsuario, DatosPasswordUsuario
from ..models import BloqueoAcceso, PerfilUsuario, RegistroAuditoria
from .utils import paginar, parametros_sin_pagina

Usuario = get_user_model()


def _verificar_puede_modificar(editor, usuario):
    """Un administrador normal no puede modificar a un superusuario."""
    if usuario.is_superuser and not editor.is_superuser:
        raise PermissionDenied('Solo un superusuario puede modificar a otro superusuario.')


@administrador_requerido
def usuario_lista(request):
    usuarios = Usuario.objects.order_by('-is_active', 'username')
    q = request.GET.get('q', '').strip()
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q)
            | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    estado = request.GET.get('estado', '')
    if estado in ('activo', 'inactivo'):
        usuarios = usuarios.filter(is_active=(estado == 'activo'))
    rol = request.GET.get('rol', '')
    if rol == 'admin':
        usuarios = usuarios.filter(Q(is_staff=True) | Q(is_superuser=True))
    elif rol == 'operador':
        usuarios = usuarios.filter(is_staff=False, is_superuser=False)
    bloqueados = set(BloqueoAcceso.objects.filter(bloqueado_hasta__gt=timezone.now())
                     .values_list('username', flat=True))
    return render(request, 'courier/usuarios/lista.html', {
        'titulo': 'Usuarios',
        'pagina': paginar(request, usuarios),
        'q': q, 'estado': estado, 'rol': rol,
        'params': parametros_sin_pagina(request),
        'bloqueados': bloqueados,
    })


@administrador_requerido
def usuario_crear(request):
    form = DatosCrearUsuario(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()  # la contraseña se guarda con hash (PBKDF2)
        # La clave la definió el administrador: es temporal y se exige cambiarla al ingresar.
        PerfilUsuario.objects.update_or_create(usuario=usuario, defaults={'debe_cambiar_password': True})
        registrar(request, 'crear', objeto=usuario,
                  descripcion=f'Usuario "{usuario.username}" creado con contraseña temporal.')
        messages.success(request, f'Usuario "{usuario.username}" creado correctamente. '
                                  'Deberá cambiar su contraseña al ingresar por primera vez.')
        return redirect('courier:usuario_lista')
    return render(request, 'courier/usuarios/formulario.html', {
        'titulo': 'Nuevo usuario', 'form': form, 'es_edicion': False,
    })


@administrador_requerido
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    _verificar_puede_modificar(request.user, usuario)
    form = DatosEditarUsuario(request.POST or None, instance=usuario, editor=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        registrar(request, 'editar', objeto=usuario, descripcion=f'Usuario "{usuario.username}" modificado.')
        messages.success(request, f'Usuario "{usuario.username}" actualizado correctamente.')
        return redirect('courier:usuario_lista')
    return render(request, 'courier/usuarios/formulario.html', {
        'titulo': f'Editar usuario: {usuario.username}', 'form': form, 'usuario_obj': usuario, 'es_edicion': True,
    })


@administrador_requerido
def usuario_password(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    _verificar_puede_modificar(request.user, usuario)
    form = DatosPasswordUsuario(usuario, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if usuario.pk == request.user.pk:
            # Mantiene la sesión actual válida tras cambiar la propia contraseña.
            update_session_auth_hash(request, usuario)
            registrar(request, 'password', objeto=usuario, descripcion='Cambió su propia contraseña.')
            messages.success(request, f'Contraseña de "{usuario.username}" actualizada.')
        else:
            # Clave asignada por un administrador: temporal, y se quita un posible bloqueo.
            PerfilUsuario.objects.update_or_create(usuario=usuario, defaults={'debe_cambiar_password': True})
            BloqueoAcceso.objects.filter(username=usuario.username.lower()).delete()
            registrar(request, 'password', objeto=usuario,
                      descripcion=f'Asignó una contraseña temporal a "{usuario.username}".')
            messages.success(request, f'Contraseña temporal de "{usuario.username}" asignada. '
                                      'Deberá cambiarla al ingresar.')
        return redirect('courier:usuario_lista')
    return render(request, 'courier/usuarios/password.html', {
        'titulo': f'Cambiar contraseña: {usuario.username}', 'form': form, 'usuario_obj': usuario,
    })


@administrador_requerido
@require_POST
def usuario_cambiar_estado(request, pk):
    """Activa o desactiva una cuenta (alternativa segura a eliminarla)."""
    usuario = get_object_or_404(Usuario, pk=pk)
    _verificar_puede_modificar(request.user, usuario)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puede desactivar su propia cuenta.')
        return redirect('courier:usuario_lista')
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])
    estado = 'activado' if usuario.is_active else 'desactivado'
    registrar(request, 'editar', objeto=usuario, descripcion=f'Usuario "{usuario.username}" {estado}.')
    messages.success(request, f'Usuario "{usuario.username}" {estado}.')
    return redirect('courier:usuario_lista')


@administrador_requerido
@require_POST
def usuario_desbloquear(request, pk):
    """Quita el bloqueo por intentos fallidos antes de que venza."""
    usuario = get_object_or_404(Usuario, pk=pk)
    _verificar_puede_modificar(request.user, usuario)
    BloqueoAcceso.objects.filter(username=usuario.username.lower()).delete()
    registrar(request, 'desbloqueo', objeto=usuario, descripcion=f'Desbloqueó la cuenta "{usuario.username}".')
    messages.success(request, f'Cuenta "{usuario.username}" desbloqueada.')
    return redirect('courier:usuario_lista')


@administrador_requerido
@require_http_methods(['GET', 'POST'])
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    _verificar_puede_modificar(request.user, usuario)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No puede eliminar su propia cuenta mientras está conectado.')
        return redirect('courier:usuario_lista')
    if request.method == 'POST':
        nombre, pk_usuario = usuario.username, usuario.pk
        usuario.delete()
        registrar(request, 'eliminar', modelo='usuario', objeto_id=pk_usuario,
                  descripcion=f'Usuario "{nombre}" eliminado.')
        messages.success(request, f'Usuario "{nombre}" eliminado.')
        return redirect('courier:usuario_lista')
    return render(request, 'courier/gestion/confirmar_eliminar.html', {
        'titulo': 'Eliminar usuario',
        'objeto': usuario,
        'url_volver': 'courier:usuario_lista',
        'advertencia': 'Esta acción es permanente. Si solo desea bloquear el acceso, use "Desactivar".',
    })


def _fecha_o_none(texto):
    try:
        return parse_date(texto or '')
    except ValueError:  # p. ej. 2026-02-31
        return None


@administrador_requerido
def auditoria_lista(request):
    """Bitácora de seguridad (solo lectura): no hay vistas para editar ni borrar registros."""
    registros = RegistroAuditoria.objects.select_related('usuario')
    q = request.GET.get('q', '').strip()
    if q:
        registros = registros.filter(
            Q(username__icontains=q) | Q(descripcion__icontains=q) | Q(ip__icontains=q) | Q(modelo__icontains=q)
        )
    accion = request.GET.get('accion', '')
    if accion in dict(RegistroAuditoria.ACCIONES):
        registros = registros.filter(accion=accion)
    desde = _fecha_o_none(request.GET.get('desde'))
    hasta = _fecha_o_none(request.GET.get('hasta'))
    zona = timezone.get_current_timezone()
    if desde:
        registros = registros.filter(fecha__gte=timezone.make_aware(datetime.combine(desde, time.min), zona))
    if hasta:
        registros = registros.filter(
            fecha__lt=timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), zona))
    return render(request, 'courier/usuarios/auditoria.html', {
        'titulo': 'Auditoría de seguridad',
        'pagina': paginar(request, registros, por_pagina=25),
        'q': q, 'accion': accion, 'desde': desde, 'hasta': hasta,
        'acciones': RegistroAuditoria.ACCIONES,
        'params': parametros_sin_pagina(request),
    })
