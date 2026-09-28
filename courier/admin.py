from django.contrib import admin

from .models import Envio, Incidencia, Notificacion, Paquete, Sucursal


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'telefono', 'email', 'activa')
    list_filter = ('activa', 'ciudad')
    search_fields = ('nombre', 'direccion', 'ciudad', 'email')


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'estado', 'peso', 'valor_declarado')
    list_filter = ('estado',)
    search_fields = ('codigo', 'descripcion')


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ('numero_envio', 'estado', 'prioridad', 'sucursal_origen', 'sucursal_destino')
    list_filter = ('estado', 'prioridad')
    search_fields = ('numero_envio', 'conductor', 'patente_vehiculo')
    list_select_related = ('sucursal_origen', 'sucursal_destino', 'paquete')


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('envio', 'tipo', 'fecha', 'resuelta')
    list_filter = ('tipo', 'resuelta')
    search_fields = ('envio__numero_envio', 'descripcion')


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('envio', 'canal', 'fecha_envio', 'enviada')
    list_filter = ('canal', 'enviada')
    search_fields = ('envio__numero_envio', 'mensaje')