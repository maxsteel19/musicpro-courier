from django.urls import path

from . import views

app_name = 'courier'

urlpatterns = [
    # Público
    path('', views.inicio, name='inicio'),

    # Panel (requiere sesión)
    path('panel/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil, name='perfil'),
    path('seguimiento/', views.seguimiento, name='seguimiento'),

    # Courier
    path('sucursales/', views.sucursal_lista, name='sucursal_lista'),
    path('sucursales/nueva/', views.sucursal_crear, name='sucursal_crear'),
    path('sucursales/<int:pk>/editar/', views.sucursal_editar, name='sucursal_editar'),
    path('sucursales/<int:pk>/eliminar/', views.sucursal_eliminar, name='sucursal_eliminar'),

    path('paquetes/', views.paquete_lista, name='paquete_lista'),
    path('paquetes/nuevo/', views.paquete_crear, name='paquete_crear'),
    path('paquetes/<int:pk>/editar/', views.paquete_editar, name='paquete_editar'),
    path('paquetes/<int:pk>/eliminar/', views.paquete_eliminar, name='paquete_eliminar'),

    path('envios/', views.envio_lista, name='envio_lista'),
    path('envios/nuevo/', views.envio_crear, name='envio_crear'),
    path('envios/<int:pk>/', views.envio_detalle, name='envio_detalle'),
    path('envios/<int:pk>/editar/', views.envio_editar, name='envio_editar'),
    path('envios/<int:pk>/eliminar/', views.envio_eliminar, name='envio_eliminar'),

    path('incidencias/', views.incidencia_lista, name='incidencia_lista'),
    path('incidencias/nueva/', views.incidencia_crear, name='incidencia_crear'),
    path('incidencias/<int:pk>/editar/', views.incidencia_editar, name='incidencia_editar'),
    path('incidencias/<int:pk>/eliminar/', views.incidencia_eliminar, name='incidencia_eliminar'),

    path('notificaciones/', views.notificacion_lista, name='notificacion_lista'),
    path('notificaciones/nueva/', views.notificacion_crear, name='notificacion_crear'),
    path('notificaciones/<int:pk>/editar/', views.notificacion_editar, name='notificacion_editar'),
    path('notificaciones/<int:pk>/eliminar/', views.notificacion_eliminar, name='notificacion_eliminar'),

    # Transporte
    path('tipos-vehiculo/', views.tipo_vehiculo_lista, name='tipo_vehiculo_lista'),
    path('tipos-vehiculo/nuevo/', views.tipo_vehiculo_crear, name='tipo_vehiculo_crear'),
    path('tipos-vehiculo/<int:pk>/editar/', views.tipo_vehiculo_editar, name='tipo_vehiculo_editar'),
    path('tipos-vehiculo/<int:pk>/eliminar/', views.tipo_vehiculo_eliminar, name='tipo_vehiculo_eliminar'),

    path('vehiculos/', views.vehiculo_lista, name='vehiculo_lista'),
    path('vehiculos/nuevo/', views.vehiculo_crear, name='vehiculo_crear'),
    path('vehiculos/<int:pk>/editar/', views.vehiculo_editar, name='vehiculo_editar'),
    path('vehiculos/<int:pk>/eliminar/', views.vehiculo_eliminar, name='vehiculo_eliminar'),

    path('conductores/', views.conductor_lista, name='conductor_lista'),
    path('conductores/nuevo/', views.conductor_crear, name='conductor_crear'),
    path('conductores/<int:pk>/editar/', views.conductor_editar, name='conductor_editar'),
    path('conductores/<int:pk>/eliminar/', views.conductor_eliminar, name='conductor_eliminar'),

    path('viajes/', views.viaje_lista, name='viaje_lista'),
    path('viajes/nuevo/', views.viaje_crear, name='viaje_crear'),
    path('viajes/<int:pk>/', views.viaje_detalle, name='viaje_detalle'),
    path('viajes/<int:pk>/editar/', views.viaje_editar, name='viaje_editar'),
    path('viajes/<int:pk>/eliminar/', views.viaje_eliminar, name='viaje_eliminar'),

    # Usuarios (solo administradores)
    path('usuarios/', views.usuario_lista, name='usuario_lista'),
    path('usuarios/nuevo/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:pk>/password/', views.usuario_password, name='usuario_password'),
    path('usuarios/<int:pk>/estado/', views.usuario_cambiar_estado, name='usuario_cambiar_estado'),
    path('usuarios/<int:pk>/eliminar/', views.usuario_eliminar, name='usuario_eliminar'),

    # Reportes ORM
    path('reportes/', views.reportes_indice, name='reportes'),
    path('reportes/<int:numero>/', views.reporte_detalle, name='reporte_detalle'),

    # Endpoints JSON
    path('api/envios/', views.api_envios, name='api_envios'),
    path('api/sucursales/', views.api_sucursales, name='api_sucursales'),
    path('api/kpis/', views.api_kpis, name='api_kpis'),
]
