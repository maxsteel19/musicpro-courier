"""Formularios del administrador propio sin usar django.forms.

Seguridad de las entradas (pauta OWASP del curso):

- Todo el HTML de los campos se arma con ``format_html``/``flatatt``, que
  escapan los valores. Así un dato como ``<script>`` se muestra como texto y
  nunca se ejecuta (evita XSS).
- Cada valor se valida en el servidor: caracteres peligrosos, tipo de dato,
  largo máximo, rangos, opciones válidas y valores únicos. Si algo falla, el
  dato se rechaza y se informa al usuario (no se produce un error 500).
"""
from collections import OrderedDict
from datetime import date, datetime
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db.models import Q
from django.forms.utils import flatatt
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .cifrado import CampoCifrado
from .models import (
    Conductor, Envio, Incidencia, Notificacion, Paquete, Sucursal,
    TipoVehiculo, Vehiculo, Viaje,
)
from .validators import normalizar_patente, normalizar_rut, validar_texto_seguro

VALORES_VERDADEROS = (True, 'on', 'true', 'True', '1', 'yes')

Usuario = get_user_model()


class EntradaFechaHora:
    """Selector nativo de fecha y hora del navegador."""

    def __init__(self, attrs=None):
        self.input_type = 'datetime-local'
        self.attrs = dict(attrs or {})


class EntradaFecha:
    def __init__(self, attrs=None):
        self.input_type = 'date'
        self.attrs = dict(attrs or {})


class ManualWidget:
    def __init__(self, input_type='text', attrs=None):
        self.input_type = input_type
        self.attrs = dict(attrs or {})


class ManualField:
    def __init__(self, *, name, label, required=True, help_text='', initial=None,
                 widget=None, choices=None, queryset=None, disabled=False):
        self.name = name
        self.label = label
        self.help_text = help_text
        self.required = required
        self.initial = initial
        self.value = initial
        self.choices = choices or []
        self.queryset = queryset
        self.disabled = disabled
        self.errors = []
        self.widget = widget or ManualWidget('text')
        self.field = SimpleNamespace(required=required, widget=self.widget)
        self.id_for_label = name

    def _valor_para_html(self):
        """Convierte el valor al formato que espera cada tipo de input."""
        valor = self.value
        if valor in (None, ''):
            return ''
        if hasattr(valor, 'pk'):
            return valor.pk
        if self.widget.input_type == 'datetime-local' and isinstance(valor, datetime):
            if timezone.is_aware(valor):
                valor = timezone.localtime(valor)
            return valor.strftime('%Y-%m-%dT%H:%M')
        if self.widget.input_type == 'date' and isinstance(valor, (date, datetime)):
            return valor.strftime('%Y-%m-%d')
        return valor

    def __str__(self):
        # flatatt y format_html escapan cada valor: < > " ' & nunca llegan
        # al navegador como HTML ejecutable.
        tipo = self.widget.input_type
        attrs = {'name': self.name, 'id': self.id_for_label, 'disabled': self.disabled}
        if tipo == 'checkbox':
            attrs.update({'type': 'checkbox', 'class': 'form-check-input',
                          'checked': self.value in VALORES_VERDADEROS})
            return format_html('<input{}>', flatatt(attrs))

        valor = self._valor_para_html()
        if tipo == 'select':
            attrs['class'] = 'form-select'
            opciones = list(self.choices)
            if not self.required:
                opciones.insert(0, ('', '---------'))
            return format_html(
                '<select{}>{}</select>', flatatt(attrs),
                format_html_join('', '<option value="{}"{}>{}</option>', (
                    (clave, ' selected' if str(valor) == str(clave) else '', etiqueta)
                    for clave, etiqueta in opciones
                )),
            )

        attrs.update({'class': 'form-control', **self.widget.attrs})
        if tipo == 'textarea':
            return format_html('<textarea{}>{}</textarea>', flatatt(attrs), valor)
        attrs['type'] = tipo
        if tipo != 'password' and valor != '':
            # Las contraseñas nunca se vuelven a escribir en la página.
            attrs['value'] = valor
        return format_html('<input{}>', flatatt(attrs))


class BaseEntradaManual:
    form_fields = []
    labels = {}
    help_texts = {}
    widgets = {}
    model = None
    # Modelo cuyas reglas (largo, formato, unicidad) se usan para validar
    # cuando el formulario no edita directamente un registro (crear usuario).
    modelo_validacion = None

    def __init__(self, data=None, instance=None, **kwargs):
        self.data = data or {}
        self.instance = instance
        self.initial = kwargs.get('initial', {})
        self.cleaned_data = {}
        self._non_field_errors = []
        self.fields = OrderedDict()
        self._build_fields()
        self._hydrate_from_instance_or_initial()
        if self.data:
            for nombre, campo in self.fields.items():
                if campo.disabled:
                    continue  # un campo bloqueado nunca toma el valor enviado
                if campo.widget.input_type == 'checkbox':
                    # Una casilla desmarcada no viaja en el POST: su ausencia es "False".
                    campo.value = self.data.get(nombre) in VALORES_VERDADEROS
                else:
                    campo.value = self.data.get(nombre, campo.value)
        self._normalize_values()

    def _build_fields(self):
        for nombre in self.form_fields:
            campo = self._make_field(nombre)
            self.fields[nombre] = campo

    def _make_field(self, nombre):
        label = self.labels.get(nombre, nombre.replace('_', ' ').title())
        help_text = self.help_texts.get(nombre, '')
        widget = self.widgets.get(nombre)
        if widget is None and self.model is not None:
            campo = self.model._meta.get_field(nombre)
            if isinstance(campo, models.BooleanField):
                widget = ManualWidget('checkbox')
            elif isinstance(campo, models.DateTimeField):
                widget = ManualWidget('datetime-local')
            elif isinstance(campo, models.DateField):
                widget = ManualWidget('date')
            elif isinstance(campo, CampoCifrado):
                widget = ManualWidget('text')
            elif isinstance(campo, models.TextField):
                widget = ManualWidget('textarea', {'rows': 3})
            elif hasattr(campo, 'remote_field') and campo.remote_field is not None:
                widget = ManualWidget('select')
            elif getattr(campo, 'choices', None):
                widget = ManualWidget('select')
            elif isinstance(campo, (models.IntegerField, models.DecimalField, models.FloatField)):
                paso = '1' if isinstance(campo, models.IntegerField) else 'any'
                widget = ManualWidget('number', {'step': paso})
            else:
                widget = ManualWidget('text')
        elif widget is None:
            widget = ManualWidget('text')
        # Límite de largo también en el navegador (el servidor lo vuelve a validar).
        modelo = self.model or self.modelo_validacion
        if modelo is not None and widget.input_type in ('text', 'email', 'textarea'):
            try:
                largo = modelo._meta.get_field(nombre).max_length
            except FieldDoesNotExist:
                largo = None
            if largo:
                widget = ManualWidget(widget.input_type, {**widget.attrs, 'maxlength': largo})
        return ManualField(name=nombre, label=label, required=self._field_required(nombre),
                           help_text=help_text, initial=self.initial.get(nombre), widget=widget,
                           choices=self._field_choices(nombre), queryset=self._field_queryset(nombre),
                           disabled=getattr(self, '_disabled_fields', {}).get(nombre, False))

    def _field_required(self, nombre):
        if self.model is None:
            return True
        campo = self.model._meta.get_field(nombre)
        return not getattr(campo, 'blank', False)

    def _field_choices(self, nombre):
        if self.model is None:
            return []
        campo = self.model._meta.get_field(nombre)
        if getattr(campo, 'choices', None):
            return list(campo.choices)
        if hasattr(campo, 'remote_field') and campo.remote_field is not None:
            return [(obj.pk, str(obj)) for obj in getattr(self, '_field_queryset', lambda *args, **kwargs: [])(nombre)]
        return []

    def _field_queryset(self, nombre):
        if self.model is None:
            return []
        campo = self.model._meta.get_field(nombre)
        if hasattr(campo, 'remote_field') and campo.remote_field is not None:
            return campo.remote_field.model.objects.all()
        return []

    def _hydrate_from_instance_or_initial(self):
        for nombre, campo in self.fields.items():
            if self.instance is not None and hasattr(self.instance, nombre):
                valor = getattr(self.instance, nombre)
            elif nombre in self.initial:
                valor = self.initial.get(nombre)
            else:
                # Registro nuevo: se propone el valor por defecto del modelo (p. ej. "Activa").
                campo_modelo = self._campo_modelo(nombre) if self.model is not None else None
                valor = campo_modelo.get_default() if campo_modelo is not None and campo_modelo.has_default() else None
            campo.value = valor

    def _normalize_values(self):
        for nombre, campo in self.fields.items():
            valor = campo.value
            if valor in (None, ''):
                campo.value = ''
                continue
            if campo.widget.input_type == 'checkbox':
                campo.value = valor in (True, 'on', 'true', 'True', '1', 'yes')
            elif campo.widget.input_type in ('date', 'datetime-local') and isinstance(valor, str):
                try:
                    if campo.widget.input_type == 'date':
                        campo.value = date.fromisoformat(valor)
                    else:
                        campo.value = datetime.fromisoformat(valor.replace('Z', '+00:00'))
                except ValueError:
                    pass

    def __iter__(self):
        return iter(self.fields.values())

    def __getitem__(self, nombre):
        return self.fields[nombre]

    def non_field_errors(self):
        return self._non_field_errors

    @property
    def errors(self):
        return {'__all__': self._non_field_errors}

    def _campo_modelo(self, nombre):
        modelo = self.model or self.modelo_validacion
        if modelo is None:
            return None
        try:
            return modelo._meta.get_field(nombre)
        except FieldDoesNotExist:
            return None

    def _validar_con_modelo(self, campo, campo_modelo, valor):
        """Aplica las reglas del modelo: tipo, largo, rangos, opciones y unicidad."""
        if campo_modelo.is_relation:
            try:
                return campo_modelo.remote_field.model._default_manager.get(pk=valor)
            except (campo_modelo.remote_field.model.DoesNotExist, ValueError, TypeError):
                campo.errors.append('Seleccione una opción válida.')
                return valor
        try:
            valor = campo_modelo.clean(valor, self.instance)
        except DjangoValidationError as exc:
            campo.errors.extend(exc.messages)
            return valor
        if isinstance(valor, datetime) and timezone.is_naive(valor):
            valor = timezone.make_aware(valor)
        if campo_modelo.unique and not campo_modelo.primary_key and not isinstance(campo_modelo, CampoCifrado):
            filtro = f'{campo_modelo.name}__iexact' if isinstance(valor, str) else campo_modelo.name
            repetidos = campo_modelo.model._default_manager.filter(**{filtro: valor})
            if self.instance is not None and self.instance.pk:
                repetidos = repetidos.exclude(pk=self.instance.pk)
            if repetidos.exists():
                campo.errors.append(f'Ya existe un registro con este valor de "{campo.label}".')
        return valor

    def is_valid(self):
        self.cleaned_data = {}
        self._non_field_errors = []
        valid = True
        for nombre, campo in self.fields.items():
            campo.errors = []
            valor = campo.value
            if valor is None:
                valor = ''
            tipo = campo.widget.input_type
            if tipo == 'checkbox':
                valor = valor in VALORES_VERDADEROS
            elif isinstance(valor, str) and tipo != 'password':
                valor = valor.strip()
                try:
                    validar_texto_seguro(valor, multilinea=(tipo == 'textarea'))
                except DjangoValidationError as exc:
                    campo.errors.extend(exc.messages)
            es_requerido = campo.required and tipo != 'checkbox'
            if es_requerido and valor in ('', None):
                campo.errors.append('Este campo es obligatorio.')
            campo_modelo = self._campo_modelo(nombre)
            if campo_modelo is not None and not campo.errors and valor not in ('', None) and tipo != 'checkbox':
                valor = self._validar_con_modelo(campo, campo_modelo, valor)
            if campo.errors:
                valid = False
                self._non_field_errors.extend(campo.errors)
            elif valor not in ('', None):
                self.cleaned_data[nombre] = valor
            campo.value = valor
        return valid

    def save(self, commit=True):
        if self.model is None:
            return self.instance
        if self.instance is None:
            objeto = self.model()
        else:
            objeto = self.instance
        for nombre in self.form_fields:
            if nombre in self.cleaned_data:
                valor = self.cleaned_data[nombre]
                campo = self.model._meta.get_field(nombre)
                if hasattr(campo, 'remote_field') and campo.remote_field is not None and valor not in (None, ''):
                    if not isinstance(valor, campo.remote_field.model):
                        valor = campo.remote_field.model.objects.filter(pk=valor).first()
                setattr(objeto, nombre, valor)
        if commit:
            objeto.save()
        return objeto

    def save_m2m(self):
        return None

    def add_error(self, nombre, mensaje):
        if nombre not in self.fields:
            self._non_field_errors.append(mensaje)
        else:
            self.fields[nombre].errors.append(mensaje)


class BaseModeloEntradaManual(BaseEntradaManual):
    model = None

    def __init__(self, data=None, instance=None, **kwargs):
        self._disabled_fields = kwargs.pop('disabled_fields', {})
        super().__init__(data=data, instance=instance, **kwargs)

    def _field_required(self, nombre):
        if self.model is None:
            return True
        campo = self.model._meta.get_field(nombre)
        return not getattr(campo, 'blank', False)


class EstiloBootstrapMixin:
    """Agrega la clase de Bootstrap a los formularios de ``django.contrib.auth``."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'form-control')


class DatosSucursal(BaseModeloEntradaManual):
    model = Sucursal
    form_fields = ['nombre', 'direccion', 'ciudad', 'telefono', 'email', 'latitud', 'longitud', 'activa']
    labels = {'direccion': 'Dirección', 'telefono': 'Teléfono'}
    widgets = {'activa': ManualWidget('checkbox'), 'email': ManualWidget('email')}


class DatosPaquete(BaseModeloEntradaManual):
    model = Paquete
    form_fields = ['codigo', 'descripcion', 'peso', 'volumen', 'valor_declarado', 'estado']
    labels = {'codigo': 'Código', 'descripcion': 'Descripción', 'peso': 'Peso (kg)', 'volumen': 'Volumen (m³)', 'valor_declarado': 'Valor declarado (CLP)'}
    widgets = {'descripcion': ManualWidget('textarea', {'rows': 3}), 'estado': ManualWidget('select')}

    def is_valid(self):
        ok = super().is_valid()
        if ok and 'codigo' in self.cleaned_data:
            self.cleaned_data['codigo'] = self.cleaned_data['codigo'].strip().upper()
            self.fields['codigo'].value = self.cleaned_data['codigo']
        return ok


class DatosEnvio(BaseModeloEntradaManual):
    model = Envio
    form_fields = ['numero_envio', 'sucursal_origen', 'sucursal_destino', 'paquete', 'viaje', 'estado', 'prioridad', 'progreso', 'fecha_despacho', 'fecha_entrega_estimada', 'fecha_entrega_real', 'observaciones']
    labels = {'numero_envio': 'Número de envío', 'sucursal_origen': 'Sucursal de origen', 'sucursal_destino': 'Sucursal de destino', 'progreso': 'Progreso (%)', 'fecha_despacho': 'Fecha de despacho', 'fecha_entrega_estimada': 'Entrega estimada', 'fecha_entrega_real': 'Entrega real'}
    widgets = {'fecha_despacho': ManualWidget('datetime-local'), 'fecha_entrega_estimada': ManualWidget('datetime-local'), 'fecha_entrega_real': ManualWidget('datetime-local'), 'observaciones': ManualWidget('textarea', {'rows': 3})}

    def __init__(self, data=None, instance=None, **kwargs):
        super().__init__(data=data, instance=instance, **kwargs)
        if instance is not None:
            self.fields['sucursal_origen'].queryset = Sucursal.objects.filter(Q(activa=True) | Q(pk=instance.sucursal_origen_id))
            self.fields['sucursal_destino'].queryset = Sucursal.objects.filter(Q(activa=True) | Q(pk=instance.sucursal_destino_id))
            self.fields['viaje'].queryset = Viaje.objects.select_related('vehiculo', 'conductor').filter(Q(estado__in=['programado', 'en_curso']) | Q(pk=instance.viaje_id))

    def is_valid(self):
        ok = super().is_valid()
        if ok:
            origen = self.cleaned_data.get('sucursal_origen')
            destino = self.cleaned_data.get('sucursal_destino')
            if origen and destino and origen == destino:
                self.add_error('sucursal_destino', 'El destino debe ser distinto del origen.')
                ok = False
            despacho = self.cleaned_data.get('fecha_despacho')
            estimada = self.cleaned_data.get('fecha_entrega_estimada')
            real = self.cleaned_data.get('fecha_entrega_real')
            if despacho and estimada and estimada < despacho:
                self.add_error('fecha_entrega_estimada', 'La entrega estimada no puede ser anterior al despacho.')
                ok = False
            if despacho and real and real < despacho:
                self.add_error('fecha_entrega_real', 'La entrega real no puede ser anterior al despacho.')
                ok = False
            if self.cleaned_data.get('estado') == 'entregado':
                self.cleaned_data['progreso'] = 100
            if ok and self.cleaned_data.get('estado') == 'entregado' and not real:
                self.cleaned_data['fecha_entrega_real'] = timezone.now()
        return ok


class DatosIncidencia(BaseModeloEntradaManual):
    model = Incidencia
    form_fields = ['envio', 'tipo', 'descripcion', 'resuelta']
    labels = {'envio': 'Envío', 'descripcion': 'Descripción'}
    widgets = {'descripcion': ManualWidget('textarea', {'rows': 4})}


class DatosNotificacion(BaseModeloEntradaManual):
    model = Notificacion
    form_fields = ['envio', 'canal', 'mensaje', 'enviada']
    labels = {'envio': 'Envío'}
    widgets = {'mensaje': ManualWidget('textarea', {'rows': 4})}


class DatosTipoVehiculo(BaseModeloEntradaManual):
    model = TipoVehiculo
    form_fields = ['nombre', 'descripcion']
    labels = {'descripcion': 'Descripción'}
    widgets = {'descripcion': ManualWidget('textarea', {'rows': 3})}


class DatosVehiculo(BaseModeloEntradaManual):
    model = Vehiculo
    form_fields = ['tipo_vehiculo', 'patente', 'marca', 'modelo', 'anio', 'estado', 'disponible']
    labels = {'tipo_vehiculo': 'Tipo de vehículo', 'disponible': 'Disponible para viajes'}

    def is_valid(self):
        ok = super().is_valid()
        if ok and 'patente' in self.cleaned_data:
            try:
                patente = normalizar_patente(self.cleaned_data['patente'])
            except DjangoValidationError as exc:
                self.add_error('patente', str(exc))
                ok = False
            else:
                repetida = Vehiculo.objects.filter(patente=patente).exclude(pk=getattr(self.instance, 'pk', None))
                if repetida.exists():
                    self.add_error('patente', 'Ya existe un vehículo con esta patente.')
                    ok = False
                else:
                    self.cleaned_data['patente'] = patente
                    self.fields['patente'].value = patente
        if ok and self.cleaned_data.get('estado') in ('mantencion', 'fuera_servicio'):
            self.cleaned_data['disponible'] = False
        return ok


class DatosConductor(BaseModeloEntradaManual):
    model = Conductor
    form_fields = ['rut', 'nombre', 'licencia', 'telefono', 'activo']
    labels = {'licencia': 'Licencia de conducir', 'telefono': 'Teléfono'}
    help_texts = {'rut': 'Se valida el dígito verificador. Ej: 12.345.678-5'}
    widgets = {'activo': ManualWidget('checkbox')}

    def is_valid(self):
        ok = super().is_valid()
        if ok and 'rut' in self.cleaned_data:
            try:
                rut = normalizar_rut(self.cleaned_data['rut'])
            except DjangoValidationError as exc:
                self.add_error('rut', str(exc))
                ok = False
            else:
                # El RUT está cifrado: la búsqueda se hace por su huella (HMAC).
                existente = Conductor.objects.con_rut(rut).exclude(pk=getattr(self.instance, 'pk', None))
                if existente.exists():
                    self.add_error('rut', 'Ya existe un conductor con este RUT.')
                    ok = False
                else:
                    self.cleaned_data['rut'] = rut
                    self.fields['rut'].value = rut
        return ok


class DatosViaje(BaseModeloEntradaManual):
    model = Viaje
    form_fields = ['vehiculo', 'conductor', 'origen', 'destino', 'fecha_salida', 'fecha_llegada', 'estado', 'observaciones']
    labels = {'vehiculo': 'Vehículo', 'fecha_salida': 'Fecha de salida', 'fecha_llegada': 'Fecha de llegada'}
    widgets = {'fecha_salida': ManualWidget('datetime-local'), 'fecha_llegada': ManualWidget('datetime-local'), 'observaciones': ManualWidget('textarea', {'rows': 3})}

    def __init__(self, data=None, instance=None, **kwargs):
        super().__init__(data=data, instance=instance, **kwargs)
        self.fields['vehiculo'].queryset = Vehiculo.objects.select_related('tipo_vehiculo')
        for campo in ('origen', 'destino'):
            self.fields[campo].widget.attrs['list'] = 'lista-ciudades'

    def is_valid(self):
        ok = super().is_valid()
        if ok:
            salida = self.cleaned_data.get('fecha_salida')
            llegada = self.cleaned_data.get('fecha_llegada')
            estado = self.cleaned_data.get('estado')
            conductor = self.cleaned_data.get('conductor')
            vehiculo = self.cleaned_data.get('vehiculo')
            if salida and llegada and llegada <= salida:
                self.add_error('fecha_llegada', 'La llegada debe ser posterior a la salida.')
                ok = False
            if estado == 'finalizado' and not llegada:
                self.add_error('fecha_llegada', 'Un viaje finalizado debe tener fecha de llegada.')
                ok = False
            origen = (self.cleaned_data.get('origen') or '').strip().lower()
            destino = (self.cleaned_data.get('destino') or '').strip().lower()
            if origen and origen == destino:
                self.add_error('destino', 'El destino debe ser distinto del origen.')
                ok = False
            if conductor and (self.instance is None or self.instance.conductor_id != conductor.pk) and not conductor.activo:
                self.add_error('conductor', 'El conductor seleccionado está inactivo.')
                ok = False
            if vehiculo and (self.instance is None or self.instance.vehiculo_id != vehiculo.pk) and vehiculo.estado == 'fuera_servicio':
                self.add_error('vehiculo', 'El vehículo seleccionado está fuera de servicio.')
                ok = False
        return ok


ETIQUETAS_USUARIO = {'username': 'Nombre de usuario', 'first_name': 'Nombre', 'last_name': 'Apellido', 'email': 'Correo electrónico', 'is_staff': 'Administrador del sistema', 'is_active': 'Cuenta activa', 'password1': 'Contraseña', 'password2': 'Confirmar contraseña'}
AYUDAS_USUARIO = {'username': 'Hasta 150 caracteres: letras, números y @/./+/-/_', 'is_staff': 'Los administradores pueden gestionar usuarios.', 'is_active': 'Desmarque para bloquear el acceso sin eliminar la cuenta.'}


class DatosCrearUsuario(BaseEntradaManual):
    form_fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'is_staff', 'is_active']
    labels = ETIQUETAS_USUARIO
    help_texts = {**AYUDAS_USUARIO, 'password1': 'Contraseña temporal: el usuario deberá cambiarla al ingresar por primera vez.'}
    widgets = {'is_staff': ManualWidget('checkbox'), 'is_active': ManualWidget('checkbox'), 'password1': ManualWidget('password'), 'password2': ManualWidget('password')}
    modelo_validacion = Usuario

    def __init__(self, data=None, instance=None, **kwargs):
        super().__init__(data=data, instance=instance, **kwargs)
        if not self.data:
            self.fields['is_active'].value = True  # valor sugerido al abrir el formulario

    def is_valid(self):
        ok = super().is_valid()
        if ok:
            password1 = self.cleaned_data.get('password1', '')
            password2 = self.cleaned_data.get('password2', '')
            if password1 != password2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
                ok = False
            try:
                validate_password(password1, user=None)
            except DjangoValidationError as exc:
                self.add_error('password1', exc.messages[0])
                ok = False
        return ok

    def save(self, commit=True):
        usuario = Usuario.objects.create_user(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            email=self.cleaned_data.get('email', ''),
            password=self.cleaned_data['password1'],
            is_staff=self.cleaned_data.get('is_staff', False),
            is_active=self.cleaned_data.get('is_active', True),
        )
        return usuario


class DatosEditarUsuario(BaseEntradaManual):
    model = Usuario
    form_fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active']
    labels = ETIQUETAS_USUARIO
    help_texts = AYUDAS_USUARIO
    widgets = {'is_staff': ManualWidget('checkbox'), 'is_active': ManualWidget('checkbox')}

    def __init__(self, data=None, instance=None, editor=None, **kwargs):
        self.editor = editor
        super().__init__(data=data, instance=instance, **kwargs)
        if editor is not None and editor.pk == getattr(instance, 'pk', None):
            for nombre in ('is_staff', 'is_active'):
                # Bloqueado en el servidor: se ignora lo que llegue en el POST.
                self.fields[nombre].disabled = True
                self.fields[nombre].value = getattr(instance, nombre)
                self.fields[nombre].help_text = 'No puede modificar este campo en su propia cuenta.'

    def save(self, commit=True):
        usuario = self.instance
        for nombre in self.form_fields:
            if nombre in self.cleaned_data:
                setattr(usuario, nombre, self.cleaned_data[nombre])
        if commit:
            usuario.save()
        return usuario


class DatosPasswordUsuario(BaseEntradaManual):
    form_fields = ['new_password1', 'new_password2']
    labels = {'new_password1': 'Nueva contraseña', 'new_password2': 'Confirmar contraseña'}
    help_texts = {'new_password1': 'Si cambia la clave de otro usuario, quedará como temporal y deberá cambiarla al ingresar.'}
    widgets = {'new_password1': ManualWidget('password'), 'new_password2': ManualWidget('password')}

    def __init__(self, usuario, data=None, **kwargs):
        self.usuario = usuario
        super().__init__(data=data, **kwargs)

    def is_valid(self):
        ok = super().is_valid()
        if ok:
            nueva1 = self.cleaned_data.get('new_password1', '')
            nueva2 = self.cleaned_data.get('new_password2', '')
            if nueva1 != nueva2:
                self.add_error('new_password2', 'Las contraseñas no coinciden.')
                ok = False
            try:
                validate_password(nueva1, user=self.usuario)
            except DjangoValidationError as exc:
                self.add_error('new_password1', exc.messages[0])
                ok = False
        return ok

    def save(self):
        self.usuario.set_password(self.cleaned_data['new_password1'])
        self.usuario.save(update_fields=['password'])
        return self.usuario


class ParametrosReporte(BaseEntradaManual):
    form_fields = ['tipo', 'vehiculo', 'conductor', 'desde', 'hasta', 'anio']
    labels = {'tipo': 'Tipo de vehículo', 'vehiculo': 'Vehículo', 'conductor': 'Conductor', 'desde': 'Desde', 'hasta': 'Hasta', 'anio': 'Año'}
    widgets = {'tipo': ManualWidget('select'), 'vehiculo': ManualWidget('select'), 'conductor': ManualWidget('select'), 'desde': EntradaFecha(), 'hasta': EntradaFecha()}

    def __init__(self, data=None, initial=None, **kwargs):
        self.initial = initial or {}
        super().__init__(data=data, initial=initial, **kwargs)
        self.fields['tipo'].choices = [(obj.pk, str(obj)) for obj in TipoVehiculo.objects.all()]
        self.fields['vehiculo'].choices = [(obj.pk, str(obj)) for obj in Vehiculo.objects.all()]
        self.fields['conductor'].choices = [(obj.pk, str(obj)) for obj in Conductor.objects.all()]

    def is_valid(self):
        ok = super().is_valid()
        desde = self.cleaned_data.get('desde')
        hasta = self.cleaned_data.get('hasta')
        if desde and hasta and hasta < desde:
            self.add_error('hasta', 'La fecha final debe ser igual o posterior a la inicial.')
            ok = False
        return ok
