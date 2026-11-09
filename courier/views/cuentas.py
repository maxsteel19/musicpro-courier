"""Autenticación con las herramientas de Django (django.contrib.auth)."""
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import reverse_lazy
from django.utils import timezone

from ..forms import EstiloBootstrapMixin


class FormularioLogin(EstiloBootstrapMixin, AuthenticationForm):
    pass


class FormularioCambioPassword(EstiloBootstrapMixin, PasswordChangeForm):
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

    def form_valid(self, form):
        messages.success(self.request, 'Su contraseña fue actualizada correctamente.')
        return super().form_valid(form)
