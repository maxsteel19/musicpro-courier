from django.contrib import admin

from .models import Cliente, DetallePedido, Pedido, Producto


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'email', 'telefono', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'apellido', 'email', 'telefono')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria', 'precio', 'stock', 'activo')
    list_filter = ('categoria', 'activo')
    search_fields = ('codigo', 'nombre', 'categoria')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha', 'estado', 'metodo_pago', 'total')
    list_filter = ('estado', 'metodo_pago', 'fecha')
    search_fields = ('cliente__nombre', 'cliente__apellido', 'id')


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad', 'precio_unitario')
    list_filter = ('pedido__estado',)
    search_fields = ('producto__nombre', 'pedido__id')
