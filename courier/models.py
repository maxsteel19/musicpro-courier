from django.db import models


class Sucursal(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300)
    ciudad = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    latitud = models.FloatField(default=0)
    longitud = models.FloatField(default=0)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'


class Paquete(models.Model):
    ESTADO_CHOICES = [
        ('preparacion', 'En Preparación'),
        ('despachado', 'Despachado'),
        ('transito', 'En Tránsito'),
        ('entregado', 'Entregado'),
        ('devuelto', 'Devuelto'),
    ]

    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=300)
    peso = models.DecimalField(max_digits=8, decimal_places=2)
    volumen = models.DecimalField(max_digits=8, decimal_places=2)
    valor_declarado = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='preparacion')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.codigo} - {self.descripcion}'

    class Meta:
        verbose_name = 'Paquete'
        verbose_name_plural = 'Paquetes'


class Envio(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_ruta', 'En Ruta'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    numero_envio = models.CharField(max_length=50, unique=True)
    sucursal_origen = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='envios_origen')
    sucursal_destino = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='envios_destino')
    paquete = models.ForeignKey(Paquete, on_delete=models.CASCADE, related_name='envios')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    conductor = models.CharField(max_length=200, blank=True)
    patente_vehiculo = models.CharField(max_length=10, blank=True)
    progreso = models.PositiveIntegerField(default=0)
    fecha_despacho = models.DateTimeField(null=True, blank=True)
    fecha_entrega_estimada = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f'{self.numero_envio} - {self.estado}'

    class Meta:
        verbose_name = 'Envío'
        verbose_name_plural = 'Envíos'


class Incidencia(models.Model):
    TIPO_CHOICES = [
        ('retraso', 'Retraso'),
        ('desvio', 'Desvío'),
        ('mecanica', 'Contingencia Mecánica'),
        ('danio', 'Daño'),
        ('otra', 'Otra'),
    ]

    envio = models.ForeignKey(Envio, on_delete=models.CASCADE, related_name='incidencias')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    resuelta = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.tipo} - {self.envio.numero_envio}'

    class Meta:
        verbose_name = 'Incidencia'
        verbose_name_plural = 'Incidencias'


class Notificacion(models.Model):
    CANAL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push'),
    ]

    envio = models.ForeignKey(Envio, on_delete=models.CASCADE, related_name='notificaciones')
    canal = models.CharField(max_length=10, choices=CANAL_CHOICES)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    enviada = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.canal} - {self.envio.numero_envio}'

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
