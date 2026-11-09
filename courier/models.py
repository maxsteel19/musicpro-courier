from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# ===========================================================================
# Módulo Courier (Evaluación 2): sucursales, paquetes, envíos, incidencias
# y notificaciones de Music Pro Tour.
# ===========================================================================


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
        ordering = ['nombre']


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
    peso = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    volumen = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    valor_declarado = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='preparacion')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.codigo} - {self.descripcion}'

    class Meta:
        verbose_name = 'Paquete'
        verbose_name_plural = 'Paquetes'
        ordering = ['-fecha_creacion']


# ===========================================================================
# Módulo Transporte (Evaluación 3): tipos de vehículo, vehículos,
# conductores y viajes que trasladan los envíos entre sucursales.
# ===========================================================================


class TipoVehiculo(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Tipo de vehículo'
        verbose_name_plural = 'Tipos de vehículo'
        ordering = ['nombre']


class Vehiculo(models.Model):
    ESTADO_CHOICES = [
        ('operativo', 'Operativo'),
        ('mantencion', 'En mantención'),
        ('fuera_servicio', 'Fuera de servicio'),
    ]

    tipo_vehiculo = models.ForeignKey(TipoVehiculo, on_delete=models.PROTECT, related_name='vehiculos')
    patente = models.CharField(max_length=15, unique=True)
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=80)
    anio = models.PositiveIntegerField(
        'año', validators=[MinValueValidator(1950), MaxValueValidator(2100)]
    )
    disponible = models.BooleanField(default=True)
    estado = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='operativo')

    def __str__(self):
        return f'{self.patente} - {self.marca} {self.modelo}'

    class Meta:
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
        ordering = ['patente']


class Conductor(models.Model):
    rut = models.CharField('RUT', max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    licencia = models.CharField(max_length=30)
    telefono = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Conductor'
        verbose_name_plural = 'Conductores'
        ordering = ['nombre']


class Viaje(models.Model):
    ESTADO_CHOICES = [
        ('programado', 'Programado'),
        ('en_curso', 'En curso'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]

    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name='viajes')
    conductor = models.ForeignKey(Conductor, on_delete=models.PROTECT, related_name='viajes')
    origen = models.CharField(max_length=150)
    destino = models.CharField(max_length=150)
    fecha_salida = models.DateTimeField()
    fecha_llegada = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='programado')
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f'{self.codigo}: {self.origen} → {self.destino}'

    @property
    def codigo(self):
        return f'VJ-{self.pk:04d}' if self.pk else 'VJ-nuevo'

    @property
    def duracion(self):
        if self.fecha_salida and self.fecha_llegada:
            return self.fecha_llegada - self.fecha_salida
        return None

    class Meta:
        verbose_name = 'Viaje'
        verbose_name_plural = 'Viajes'
        ordering = ['-fecha_salida']


# ===========================================================================
# Envíos y su seguimiento
# ===========================================================================


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
    sucursal_origen = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='envios_origen')
    sucursal_destino = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='envios_destino')
    paquete = models.ForeignKey(Paquete, on_delete=models.PROTECT, related_name='envios')
    viaje = models.ForeignKey(
        Viaje, on_delete=models.SET_NULL, null=True, blank=True, related_name='envios',
        help_text='Viaje (vehículo + conductor) que transporta el envío.',
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    progreso = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    fecha_despacho = models.DateTimeField(null=True, blank=True)
    fecha_entrega_estimada = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='envios_creados', editable=False,
    )

    def __str__(self):
        return f'{self.numero_envio} - {self.get_estado_display()}'

    class Meta:
        verbose_name = 'Envío'
        verbose_name_plural = 'Envíos'
        ordering = ['-id']


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
    reportada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='incidencias_reportadas', editable=False,
    )

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.envio.numero_envio}'

    class Meta:
        verbose_name = 'Incidencia'
        verbose_name_plural = 'Incidencias'
        ordering = ['-fecha']


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
        return f'{self.get_canal_display()} - {self.envio.numero_envio}'

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_envio']
