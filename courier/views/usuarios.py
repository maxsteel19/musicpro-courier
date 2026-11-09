"""Mantenedor de usuarios propio (crear, consultar, modificar, desactivar y eliminar).

Solo pueden usarlo los administradores: el decorador ``@administrador_requerido``
exige sesión iniciada (``login_required``) y rol staff/superusuario.
"""
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from ..decorators import administrador_requerido
from ..forms import UsuarioCrearForm, UsuarioEditarForm, UsuarioPasswordForm
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
    return render(request, 'courier/usuarios/lista.html', {
        'titulo': 'Usuarios',
        'pagina': paginar(request, usuarios),
        'q': q, 'estado': estado, 'rol': rol,
        'params': parametros_sin_pagina(request),
    })


@administrador_requerido
def usuario_crear(request):
    form = UsuarioCrearForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()  # la contraseña se guarda con hash (PBKDF2)
        messages.success(request, f'Usuario "{usuario.username}" creado correctamente.')
        return redirect('courier:usuario_lista')
    return render(request, 'courier/usuarios/formulario.html', {
        'titulo': 'Nuevo usuario', 'form': form, 'es_edicion': False,
    })


@administrador_requerido
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    _verificar_puede_modificar(request.user, usuario)
    form = UsuarioEditarForm(request.POST or None, instance=usuario, editor=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Usuario "{usuario.username}" actualizado correctamente.')
        return redirect('courier:usuario_lista')
    return render(request, 'courier/usuarios/formulario.html', {
        'titulo': f'Editar usuario: {usuario.username}', 'form': form, 'usuario_obj': usuario, 'es_edicion': True,
    })


@administrador_requerido
def usuario_password(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    _verificar_puede_modificar(request.user, usuario)
    form = UsuarioPasswordForm(usuario, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if usuario.pk == request.user.pk:
            # Mantiene la sesión actual válida tras cambiar la propia contraseña.
            update_session_auth_hash(request, usuario)
        messages.success(request, f'Contraseña de "{usuario.username}" actualizada.')
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
    messages.success(request, f'Usuario "{usuario.username}" {estado}.')
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
        nombre = usuario.username
        usuario.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado.')
        return redirect('courier:usuario_lista')
    return render(request, 'courier/gestion/confirmar_eliminar.html', {
        'titulo': 'Eliminar usuario',
        'objeto': usuario,
        'url_volver': 'courier:usuario_lista',
        'advertencia': 'Esta acción es permanente. Si solo desea bloquear el acceso, use "Desactivar".',
    })
