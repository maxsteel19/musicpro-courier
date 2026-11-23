"""Rutas del proyecto Music Pro Courier.

Django Admin no se utiliza (Evaluación 3): la gestión se hace desde el
administrador propio de la app ``courier``.
"""
from django.urls import include, path

from courier import views

urlpatterns = [
    path('cuentas/login/', views.IniciarSesionView.as_view(), name='login'),
    path('cuentas/logout/', views.CerrarSesionView.as_view(), name='logout'),
    path('cuentas/password/', views.CambiarPasswordView.as_view(), name='password_cambiar'),
    # Recuperación de contraseña por correo (enlace de un solo uso).
    path('cuentas/recuperar/', views.RecuperarPasswordView.as_view(), name='password_reset'),
    path('cuentas/recuperar/enviado/', views.RecuperarPasswordEnviadoView.as_view(), name='password_reset_done'),
    path('cuentas/recuperar/<uidb64>/<token>/', views.RecuperarPasswordConfirmarView.as_view(),
         name='password_reset_confirm'),
    path('cuentas/recuperar/listo/', views.RecuperarPasswordListoView.as_view(), name='password_reset_complete'),
    path('', include('courier.urls')),
]
