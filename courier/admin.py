from django.contrib import admin
from .models import Envio, Sucursal, Paquete, Incidencia, Notificacion


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'telefono', 'activa')
    list_filter = ('activa', 'ciudad')
    search_fields = ('nombre', 'ciudad')


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'estado', 'valor_declarado')
    list_filter = ('estado',)
    search_fields = ('codigo', 'descripcion')


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ('numero_envio', 'sucursal_origen', 'sucursal_destino', 'estado', 'prioridad', 'conductor')
    list_filter = ('estado', 'prioridad')
    search_fields = ('numero_envio', 'conductor')


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('envio', 'tipo', 'resuelta', 'fecha')
    list_filter = ('tipo', 'resuelta')
    search_fields = ('descripcion',)


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('envio', 'canal', 'enviada', 'fecha_envio')
    list_filter = ('canal', 'enviada')
    search_fields = ('mensaje',)
