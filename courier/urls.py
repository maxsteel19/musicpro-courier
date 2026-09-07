from django.urls import path
from . import views

app_name = 'courier'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('seguimiento/', views.seguimiento, name='seguimiento'),
    path('sucursales/', views.sucursales_view, name='sucursales'),
    path('envios/', views.envios_view, name='envios'),
    path('paquetes/', views.paquetes_view, name='paquetes'),
    path('incidencias/', views.incidencias_view, name='incidencias'),
    path('reportes/', views.reportes_view, name='reportes'),
    path('notificaciones/', views.notificaciones_view, name='notificaciones'),
    path('api/envios/', views.api_envios, name='api_envios'),
    path('api/sucursales/', views.api_sucursales, name='api_sucursales'),
    path('api/kpis/', views.api_kpis, name='api_kpis'),
]
