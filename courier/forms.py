"""Formularios del administrador propio (sin Django Admin)."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from django.db.models import Q
from django.utils import timezone

from .models import (
    Conductor, Envio, Incidencia, Notificacion, Paquete, Sucursal,
    TipoVehiculo, Vehiculo, Viaje,
)
from .validators import normalizar_patente, normalizar_rut

Usuario = get_user_model()


class EntradaFechaHora(forms.DateTimeInput):
    """Selector nativo de fecha y hora del navegador."""

    input_type = 'datetime-local'

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format='%Y-%m-%dT%H:%M')


class EntradaFecha(forms.DateInput):
    input_type = 'date'

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format='%Y-%m-%d')


class EstiloBootstrapMixin:
    """Agrega las clases CSS de Bootstrap a todos los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo, forms.ModelChoiceField) and campo.empty_label is not None:
                campo.empty_label = 'Seleccione una opción'
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                clase = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                clase = 'form-select'
            else:
                clase = 'form-control'
            widget.attrs['class'] = f"{widget.attrs.get('class', '')} {clase}".strip()


# ---------------------------------------------------------------------------
# Courier
# ---------------------------------------------------------------------------


class SucursalForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = ['nombre', 'direccion', 'ciudad', 'telefono', 'email', 'latitud', 'longitud', 'activa']
        labels = {'direccion': 'Dirección', 'telefono': 'Teléfono'}


class PaqueteForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Paquete
        fields = ['codigo', 'descripcion', 'peso', 'volumen', 'valor_declarado', 'estado']
        labels = {
            'codigo': 'Código',
            'descripcion': 'Descripción',
            'peso': 'Peso (kg)',
            'volumen': 'Volumen (m³)',
            'valor_declarado': 'Valor declarado (CLP)',
        }

    def clean_codigo(self):
        return self.cleaned_data['codigo'].strip().upper()


class EnvioForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Envio
        fields = [
            'numero_envio', 'sucursal_origen', 'sucursal_destino', 'paquete', 'viaje',
            'estado', 'prioridad', 'progreso', 'fecha_despacho', 'fecha_entrega_estimada',
            'fecha_entrega_real', 'observaciones',
        ]
        labels = {
            'numero_envio': 'Número de envío',
            'sucursal_origen': 'Sucursal de origen',
            'sucursal_destino': 'Sucursal de destino',
            'progreso': 'Progreso (%)',
            'fecha_despacho': 'Fecha de despacho',
            'fecha_entrega_estimada': 'Entrega estimada',
            'fecha_entrega_real': 'Entrega real',
        }
        widgets = {
            'fecha_despacho': EntradaFechaHora(),
            'fecha_entrega_estimada': EntradaFechaHora(),
            'fecha_entrega_real': EntradaFechaHora(),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo se ofrecen sucursales activas y viajes vigentes, conservando
        # los valores ya asignados cuando se edita un envío existente.
        instancia = self.instance
        self.fields['sucursal_origen'].queryset = Sucursal.objects.filter(
            Q(activa=True) | Q(pk=instancia.sucursal_origen_id)
        )
        self.fields['sucursal_destino'].queryset = Sucursal.objects.filter(
            Q(activa=True) | Q(pk=instancia.sucursal_destino_id)
        )
        self.fields['viaje'].queryset = Viaje.objects.select_related('vehiculo', 'conductor').filter(
            Q(estado__in=['programado', 'en_curso']) | Q(pk=instancia.viaje_id)
        )

    def clean_numero_envio(self):
        return self.cleaned_data['numero_envio'].strip().upper()

    def clean(self):
        datos = super().clean()
        origen = datos.get('sucursal_origen')
        destino = datos.get('sucursal_destino')
        if origen and destino and origen == destino:
            self.add_error('sucursal_destino', 'El destino debe ser distinto del origen.')

        despacho = datos.get('fecha_despacho')
        estimada = datos.get('fecha_entrega_estimada')
        real = datos.get('fecha_entrega_real')
        if despacho and estimada and estimada < despacho:
            self.add_error('fecha_entrega_estimada', 'La entrega estimada no puede ser anterior al despacho.')
        if despacho and real and real < despacho:
            self.add_error('fecha_entrega_real', 'La entrega real no puede ser anterior al despacho.')

        if datos.get('estado') == 'entregado':
            datos['progreso'] = 100
            if not real:
                datos['fecha_entrega_real'] = timezone.now()
        return datos


class IncidenciaForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['envio', 'tipo', 'descripcion', 'resuelta']
        labels = {'envio': 'Envío', 'descripcion': 'Descripción'}
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}


class NotificacionForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Notificacion
        fields = ['envio', 'canal', 'mensaje', 'enviada']
        labels = {'envio': 'Envío'}
        widgets = {'mensaje': forms.Textarea(attrs={'rows': 4})}


# ---------------------------------------------------------------------------
# Transporte
# ---------------------------------------------------------------------------


class TipoVehiculoForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = TipoVehiculo
        fields = ['nombre', 'descripcion']
        labels = {'descripcion': 'Descripción'}
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class VehiculoForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = ['tipo_vehiculo', 'patente', 'marca', 'modelo', 'anio', 'estado', 'disponible']
        labels = {'tipo_vehiculo': 'Tipo de vehículo', 'disponible': 'Disponible para viajes'}

    def clean_patente(self):
        patente = normalizar_patente(self.cleaned_data['patente'])
        repetida = Vehiculo.objects.filter(patente=patente).exclude(pk=self.instance.pk)
        if repetida.exists():
            raise forms.ValidationError('Ya existe un vehículo con esta patente.')
        return patente

    def clean(self):
        datos = super().clean()
        if datos.get('estado') in ('mantencion', 'fuera_servicio'):
            datos['disponible'] = False
        return datos


class ConductorForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Conductor
        fields = ['rut', 'nombre', 'licencia', 'telefono', 'activo']
        labels = {'licencia': 'Licencia de conducir', 'telefono': 'Teléfono'}
        help_texts = {'rut': 'Se valida el dígito verificador. Ej: 12.345.678-5'}

    def clean_rut(self):
        rut = normalizar_rut(self.cleaned_data['rut'])
        if Conductor.objects.filter(rut=rut).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe un conductor con este RUT.')
        return rut


class ViajeForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Viaje
        fields = [
            'vehiculo', 'conductor', 'origen', 'destino', 'fecha_salida',
            'fecha_llegada', 'estado', 'observaciones',
        ]
        labels = {'vehiculo': 'Vehículo', 'fecha_salida': 'Fecha de salida', 'fecha_llegada': 'Fecha de llegada'}
        widgets = {
            'fecha_salida': EntradaFechaHora(),
            'fecha_llegada': EntradaFechaHora(),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehiculo'].queryset = Vehiculo.objects.select_related('tipo_vehiculo')
        # Sugerencias de ciudades (<datalist> en la plantilla del formulario).
        for campo in ('origen', 'destino'):
            self.fields[campo].widget.attrs['list'] = 'lista-ciudades'

    def clean(self):
        datos = super().clean()
        salida = datos.get('fecha_salida')
        llegada = datos.get('fecha_llegada')
        estado = datos.get('estado')
        vehiculo = datos.get('vehiculo')
        conductor = datos.get('conductor')

        if salida and llegada and llegada <= salida:
            self.add_error('fecha_llegada', 'La llegada debe ser posterior a la salida.')
        if estado == 'finalizado' and not llegada:
            self.add_error('fecha_llegada', 'Un viaje finalizado debe tener fecha de llegada.')
        if datos.get('origen') and datos.get('origen', '').strip().lower() == (datos.get('destino') or '').strip().lower():
            self.add_error('destino', 'El destino debe ser distinto del origen.')

        # Solo se valida la disponibilidad cuando se asigna un recurso nuevo.
        if conductor and 'conductor' in self.changed_data and not conductor.activo:
            self.add_error('conductor', 'El conductor seleccionado está inactivo.')
        if vehiculo and 'vehiculo' in self.changed_data and vehiculo.estado == 'fuera_servicio':
            self.add_error('vehiculo', 'El vehículo seleccionado está fuera de servicio.')
        return datos


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------

ETIQUETAS_USUARIO = {
    'username': 'Nombre de usuario',
    'first_name': 'Nombre',
    'last_name': 'Apellido',
    'email': 'Correo electrónico',
    'is_staff': 'Administrador del sistema',
    'is_active': 'Cuenta activa',
}
AYUDAS_USUARIO = {
    'username': 'Hasta 150 caracteres: letras, números y @/./+/-/_',
    'is_staff': 'Los administradores pueden gestionar usuarios.',
    'is_active': 'Desmarque para bloquear el acceso sin eliminar la cuenta.',
}


class UsuarioCrearForm(EstiloBootstrapMixin, UserCreationForm):
    email = forms.EmailField(label='Correo electrónico', required=True)

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active']
        labels = ETIQUETAS_USUARIO
        help_texts = AYUDAS_USUARIO

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].initial = True


class UsuarioEditarForm(EstiloBootstrapMixin, forms.ModelForm):
    email = forms.EmailField(label='Correo electrónico', required=True)

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active']
        labels = ETIQUETAS_USUARIO
        help_texts = AYUDAS_USUARIO

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Un administrador no puede quitarse a sí mismo el rol ni desactivarse:
        # así se evita quedar sin acceso al sistema por error.
        if editor is not None and editor.pk == self.instance.pk:
            for campo in ('is_staff', 'is_active'):
                self.fields[campo].disabled = True
                self.fields[campo].help_text = 'No puede modificar este campo en su propia cuenta.'


class UsuarioPasswordForm(EstiloBootstrapMixin, SetPasswordForm):
    """Permite a un administrador asignar una nueva contraseña a otro usuario."""


# ---------------------------------------------------------------------------
# Parámetros de los reportes ORM
# ---------------------------------------------------------------------------


class ParametrosReporteForm(EstiloBootstrapMixin, forms.Form):
    tipo = forms.ModelChoiceField(
        label='Tipo de vehículo', queryset=TipoVehiculo.objects.all(), required=False,
    )
    vehiculo = forms.ModelChoiceField(
        label='Vehículo', queryset=Vehiculo.objects.all(), required=False,
    )
    conductor = forms.ModelChoiceField(
        label='Conductor', queryset=Conductor.objects.all(), required=False,
    )
    desde = forms.DateField(label='Desde', required=False, widget=EntradaFecha())
    hasta = forms.DateField(label='Hasta', required=False, widget=EntradaFecha())
    anio = forms.IntegerField(label='Año', required=False, min_value=2000, max_value=2100)

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get('desde'), datos.get('hasta')
        if desde and hasta and hasta < desde:
            self.add_error('hasta', 'La fecha final debe ser igual o posterior a la inicial.')
        return datos
