from django.db import models


class Cliente(models.Model):
    nombre = models.CharField(max_length=80)
    apellido = models.CharField(max_length=80)
    email = models.EmailField(max_length=100, unique=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.nombre} {self.apellido}'

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class Producto(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    categoria = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=12, decimal_places=0)
    stock = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'


class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesado', 'Procesado'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos')
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='tarjeta')
    total = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    def __str__(self):
        return f'Pedido #{self.pk} - {self.cliente}'

    @property
    def detalles(self):
        return self.detalles_pedido.all()

    def guardar_total(self):
        self.total = sum(
            detalle.cantidad * detalle.precio_unitario for detalle in self.detalles_pedido.all()
        )
        self.save(update_fields=['total'])

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles_pedido')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='detalles')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)

    def __str__(self):
        return f'{self.producto} x {self.cantidad}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.pedido.guardar_total()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.pedido.guardar_total()

    class Meta:
        verbose_name = 'Detalle de pedido'
        verbose_name_plural = 'Detalles de pedidos'


