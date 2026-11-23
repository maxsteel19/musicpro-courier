"""Autenticación con las herramientas de Django (django.contrib.auth).

Además del login y logout de Django, aquí se implementa:

- Bloqueo temporal de la cuenta tras ``LOGIN_MAX_INTENTOS`` intentos fallidos.
- Recuperación de contraseña por correo con un enlace de un solo uso.
- Cambio obligatorio de contraseñas temporales.
- Aceptación del acuerdo de uso de datos.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm,
)
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordResetCompleteView,
    PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from ..auditoria import ip_cliente, registrar
from ..entradas import EstiloBootstrapMixin
from ..models import BloqueoAcceso, PerfilUsuario


# ---------------------------------------------------------------------------
# Inicio de sesión con bloqueo por intentos fallidos
# ---------------------------------------------------------------------------


class FormularioLogin(EstiloBootstrapMixin, AuthenticationForm):
    """Login de Django + bloqueo temporal tras varios intentos fallidos.

    Los intentos se cuentan por nombre de usuario, exista o no la cuenta, y el
    mensaje es el mismo en ambos casos: así no se revela qué usuarios existen.
    """

    def clean(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username or not self.cleaned_data.get('password'):
            return super().clean()

        registro = BloqueoAcceso.objects.filter(username=username.lower()).first()
        if registro is not None and registro.esta_bloqueado:
            registrar(self.request, 'login_fallido', username=username,
                      descripcion='Intento de ingreso con la cuenta bloqueada.')
            raise ValidationError(self._mensaje_bloqueo(registro), code='bloqueada')

        try:
            return super().clean()
        except ValidationError:
            self._registrar_intento_fallido(username)
            raise  # nunca se llega aquí: _registrar_intento_fallido lanza su propio error

    def _registrar_intento_fallido(self, username):
        maximo = settings.LOGIN_MAX_INTENTOS
        with transaction.atomic():
            registro, _ = BloqueoAcceso.objects.select_for_update().get_or_create(username=username.lower())
            if registro.bloqueado_hasta and not registro.esta_bloqueado:
                # El bloqueo anterior ya venció: el conteo parte de cero.
                registro.intentos_fallidos = 0
                registro.bloqueado_hasta = None
            registro.intentos_fallidos += 1
            registro.ultima_ip = ip_cliente(self.request)
            if registro.intentos_fallidos >= maximo:
                registro.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.LOGIN_MINUTOS_BLOQUEO)
            registro.save()

        registrar(self.request, 'login_fallido', username=username,
                  descripcion=f'Usuario o contraseña incorrectos (intento {registro.intentos_fallidos} de {maximo}).')
        if registro.esta_bloqueado:
            registrar(self.request, 'bloqueo', username=username,
                      descripcion=f'Cuenta bloqueada {settings.LOGIN_MINUTOS_BLOQUEO} minutos tras '
                                  f'{maximo} intentos fallidos.')
            raise ValidationError(self._mensaje_bloqueo(registro), code='bloqueada')
        restantes = maximo - registro.intentos_fallidos
        raise ValidationError(
            'Usuario o contraseña incorrectos. Le quedan %(restantes)s intento(s) antes del bloqueo temporal.',
            code='invalid_login', params={'restantes': restantes},
        )

    @staticmethod
    def _mensaje_bloqueo(registro):
        return (f'Cuenta bloqueada temporalmente por {settings.LOGIN_MAX_INTENTOS} intentos fallidos. '
                f'Intente de nuevo en {registro.minutos_restantes} minuto(s), recupere su contraseña '
                f'o pida a un administrador que la desbloquee.')


class FormularioCambioPassword(EstiloBootstrapMixin, PasswordChangeForm):
    pass


class FormularioRecuperar(EstiloBootstrapMixin, PasswordResetForm):
    pass


class FormularioNuevaPassword(EstiloBootstrapMixin, SetPasswordForm):
    pass


class IniciarSesionView(LoginView):
    """Login de Django con plantilla propia.

    Al autenticar, Django crea una sesión nueva (cambia el identificador para
    evitar fijación de sesión) y guarda en ella el id del usuario. Además
    registramos en la sesión la hora de inicio y el acceso anterior.
    """

    template_name = 'registration/login.html'
    authentication_form = FormularioLogin
    redirect_authenticated_user = True

    def form_valid(self, form):
        usuario = form.get_user()
        acceso_anterior = usuario.last_login
        respuesta = super().form_valid(form)  # llama a django.contrib.auth.login()
        # Ingreso correcto: se reinicia el contador de intentos fallidos.
        BloqueoAcceso.objects.filter(
            username__in={usuario.username.lower(), form.cleaned_data['username'].strip().lower()}
        ).delete()
        self.request.session['inicio_sesion'] = timezone.now().isoformat()
        self.request.session['acceso_anterior'] = acceso_anterior.isoformat() if acceso_anterior else None
        messages.success(self.request, f'Bienvenido/a, {usuario.get_full_name() or usuario.username}.')
        return respuesta


class CerrarSesionView(LogoutView):
    """Cierra la sesión (solo acepta POST con token CSRF)."""

    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)  # llama a django.contrib.auth.logout()
        messages.info(request, 'Sesión cerrada correctamente.')
        return respuesta


class CambiarPasswordView(PasswordChangeView):
    """Cambio de contraseña del propio usuario.

    ``PasswordChangeView`` ya está protegida con ``login_required`` y, al
    guardar, actualiza el hash de la sesión para que el usuario no sea
    desconectado (las demás sesiones abiertas con la clave antigua se invalidan).
    """

    template_name = 'registration/cambiar_password.html'
    form_class = FormularioCambioPassword
    success_url = reverse_lazy('courier:perfil')

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['clave_temporal'] = PerfilUsuario.de(self.request.user).debe_cambiar_password
        return contexto

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        PerfilUsuario.objects.filter(usuario=self.request.user).update(debe_cambiar_password=False)
        registrar(self.request, 'password', objeto=self.request.user,
                  descripcion='El usuario cambió su propia contraseña.')
        messages.success(self.request, 'Su contraseña fue actualizada correctamente.')
        return respuesta


# ---------------------------------------------------------------------------
# Recuperación de contraseña por correo
# ---------------------------------------------------------------------------


class RecuperarPasswordView(PasswordResetView):
    """Pide el correo y envía un enlace para crear una nueva contraseña.

    La respuesta es la misma exista o no el correo (no revela qué correos
    están registrados). El enlace es de un solo uso y vence en
    ``PASSWORD_RESET_TIMEOUT`` segundos.
    """

    template_name = 'registration/recuperar_form.html'
    email_template_name = 'registration/recuperar_email.txt'
    subject_template_name = 'registration/recuperar_asunto.txt'
    form_class = FormularioRecuperar
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        registrar(self.request, 'recuperacion',
                  descripcion=f'Solicitud de recuperación para el correo {form.cleaned_data["email"]}.')
        return super().form_valid(form)


class RecuperarPasswordEnviadoView(PasswordResetDoneView):
    template_name = 'registration/recuperar_enviado.html'


class RecuperarPasswordConfirmarView(PasswordResetConfirmView):
    template_name = 'registration/recuperar_confirmar.html'
    form_class = FormularioNuevaPassword
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        usuario = form.user
        # La nueva clave la eligió el propio usuario: ya no es temporal y se quita el bloqueo.
        PerfilUsuario.objects.update_or_create(usuario=usuario, defaults={'debe_cambiar_password': False})
        BloqueoAcceso.objects.filter(username=usuario.username.lower()).delete()
        registrar(self.request, 'recuperacion', usuario=usuario, objeto=usuario,
                  descripcion='Contraseña restablecida con el enlace enviado por correo.')
        return respuesta


class RecuperarPasswordListoView(PasswordResetCompleteView):
    template_name = 'registration/recuperar_listo.html'


# ---------------------------------------------------------------------------
# Acuerdo de uso de datos
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['GET', 'POST'])
def acuerdo_datos(request):
    """Muestra el acuerdo de uso y confidencialidad de datos y registra su aceptación."""
    perfil = PerfilUsuario.de(request.user)
    version = settings.VERSION_ACUERDO_DATOS
    siguiente = request.POST.get('next') or request.GET.get('next') or ''
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        siguiente = reverse('courier:dashboard')

    error = ''
    if request.method == 'POST':
        if request.POST.get('decision') == 'rechazar':
            registrar(request, 'acuerdo', descripcion=f'Rechazó el acuerdo de uso de datos (versión {version}).')
            logout(request)
            messages.warning(request, 'Para usar el sistema debe aceptar el acuerdo de uso de datos.')
            return redirect('login')
        if request.POST.get('acepto') != 'on':
            error = 'Debe marcar la casilla "He leído y acepto" para continuar.'
        else:
            perfil.acuerdo_version = version
            perfil.acuerdo_aceptado_en = timezone.now()
            perfil.acuerdo_ip = ip_cliente(request)
            perfil.save()
            registrar(request, 'acuerdo', descripcion=f'Aceptó el acuerdo de uso de datos (versión {version}).')
            messages.success(request, 'Gracias. Se registró su aceptación del acuerdo de uso de datos.')
            return redirect(siguiente)

    return render(request, 'registration/acuerdo_datos.html', {
        'perfil': perfil, 'version': version, 'next': siguiente, 'error': error,
        'ya_aceptado': perfil.acepto_acuerdo_vigente,
    })
