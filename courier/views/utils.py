"""Funciones de apoyo compartidas por las vistas."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import redirect, render

POR_PAGINA = 15


def paginar(request, queryset, por_pagina=POR_PAGINA):
    """Devuelve la página solicitada (?page=N) de un queryset."""
    return Paginator(queryset, por_pagina).get_page(request.GET.get('page'))


def parametros_sin_pagina(request):
    """Query string actual sin el parámetro ``page`` (para los enlaces de paginación)."""
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def formulario_crud(request, *, form_class, titulo, url_lista, instancia=None,
                    antes_de_guardar=None, icono='fa-pen', form_kwargs=None, extra=None):
    """Muestra y procesa el formulario de creación/edición de un registro.

    - GET: formulario vacío (crear) o con los datos actuales (editar).
    - POST válido: guarda con el ORM (``form.save()``) y redirige al listado.
    - POST inválido: vuelve a mostrar el formulario con los errores.
    """
    form = form_class(request.POST or None, instance=instancia, **(form_kwargs or {}))
    if request.method == 'POST' and form.is_valid():
        objeto = form.save(commit=False)
        if antes_de_guardar:
            antes_de_guardar(objeto)
        objeto.save()
        form.save_m2m()
        accion = 'actualizado' if instancia else 'creado'
        messages.success(request, f'Registro "{objeto}" {accion} correctamente.')
        return redirect(url_lista)

    contexto = {
        'form': form,
        'titulo': titulo,
        'icono': icono,
        'url_volver': url_lista,
        'es_edicion': instancia is not None,
    }
    contexto.update(extra or {})
    return render(request, 'courier/gestion/formulario.html', contexto)


def eliminar_crud(request, *, instancia, url_lista, titulo, advertencia=''):
    """Pide confirmación (GET) y elimina el registro (POST).

    Si el registro está referenciado por otros (``on_delete=PROTECT``) la
    base de datos no se modifica y se informa al usuario.
    """
    if request.method == 'POST':
        nombre = str(instancia)
        try:
            instancia.delete()
        except (ProtectedError, RestrictedError) as error:
            relacionados = {obj._meta.verbose_name_plural for obj in error.protected_objects}
            messages.error(
                request,
                f'No se puede eliminar "{nombre}" porque tiene registros asociados '
                f'({", ".join(sorted(relacionados))}).',
            )
        else:
            messages.success(request, f'Registro "{nombre}" eliminado correctamente.')
        return redirect(url_lista)

    return render(request, 'courier/gestion/confirmar_eliminar.html', {
        'objeto': instancia,
        'titulo': titulo,
        'url_volver': url_lista,
        'advertencia': advertencia,
    })
