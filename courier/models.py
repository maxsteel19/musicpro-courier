from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .cifrado import CampoCifrado, huella
from .validators import normalizar_rut

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


def _rut_para_huella(rut):
    try:
        return normalizar_rut(rut)
    except ValidationError:
        return (rut or '').strip().upper()


class ConductorQuerySet(models.QuerySet):
    def con_rut(self, rut):
        """Busca por RUT. Como el RUT está cifrado, se compara su huella (HMAC)."""
        try:
            rut = normalizar_rut(rut)
        except ValidationError:
            return self.none()
        return self.filter(rut_huella=huella(rut))


class Conductor(models.Model):
    # Datos personales cifrados en la base de datos (ver courier/cifrado.py).
    rut = CampoCifrado('RUT', validators=[MaxLengthValidator(20)])
    rut_huella = models.CharField(max_length=64, unique=True, editable=False)
    nombre = models.CharField(max_length=150)
    licencia = models.CharField(max_length=30)
    telefono = CampoCifrado('teléfono', blank=True, validators=[MaxLengthValidator(30)])
    activo = models.BooleanField(default=True)

    objects = ConductorQuerySet.as_manager()

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        # La huella permite exigir RUT único y buscar sin guardar el RUT en claro.
        self.rut_huella = huella(_rut_para_huella(self.rut))
        super().save(*args, **kwargs)

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


# ===========================================================================
# Seguridad: perfil de cuenta, bloqueo por intentos fallidos y auditoría
# ===========================================================================


class PerfilUsuario(models.Model):
    """Datos de seguridad de cada cuenta que no están en el usuario de Django."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    debe_cambiar_password = models.BooleanField(
        default=False, help_text='La contraseña es temporal: se exige cambiarla al ingresar.')
    acuerdo_version = models.CharField('versión del acuerdo aceptado', max_length=10, blank=True)
    acuerdo_aceptado_en = models.DateTimeField(null=True, blank=True)
    acuerdo_ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f'Perfil de {self.usuario}'

    @classmethod
    def de(cls, usuario):
        perfil, _ = cls.objects.get_or_create(usuario=usuario)
        return perfil

    @property
    def acepto_acuerdo_vigente(self):
        return self.acuerdo_version == settings.VERSION_ACUERDO_DATOS

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'


class BloqueoAcceso(models.Model):
    """Intentos fallidos de inicio de sesión por nombre de usuario.

    Se registra por nombre (exista o no la cuenta) para no revelar qué
    usuarios existen: el sistema responde igual en ambos casos.
    """

    username = models.CharField(max_length=150, unique=True)
    intentos_fallidos = models.PositiveIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ultimo_intento = models.DateTimeField(auto_now=True)
    ultima_ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return self.username

    @property
    def esta_bloqueado(self):
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())

    @property
    def minutos_restantes(self):
        if not self.esta_bloqueado:
            return 0
        return max(1, round((self.bloqueado_hasta - timezone.now()).total_seconds() / 60))

    class Meta:
        verbose_name = 'Bloqueo de acceso'
        verbose_name_plural = 'Bloqueos de acceso'


class RegistroAuditoria(models.Model):
    """Bitácora de seguridad (Ley 21.459 de delitos informáticos).

    Solo se agregan registros: no existe ninguna vista para editarlos ni
    borrarlos, y el modelo impide modificar un registro ya guardado.
    """

    ACCIONES = [
        ('login', 'Inicio de sesión'),
        ('login_fallido', 'Inicio de sesión fallido'),
        ('bloqueo', 'Cuenta bloqueada'),
        ('desbloqueo', 'Cuenta desbloqueada'),
        ('logout', 'Cierre de sesión'),
        ('crear', 'Creación'),
        ('editar', 'Modificación'),
        ('eliminar', 'Eliminación'),
        ('password', 'Cambio de contraseña'),
        ('recuperacion', 'Recuperación de contraseña'),
        ('acuerdo', 'Acuerdo de uso de datos'),
        ('acceso_denegado', 'Acceso denegado'),
    ]

    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='registros_auditoria')
    username = models.CharField('nombre de usuario', max_length=150, blank=True)
    accion = models.CharField(max_length=20, choices=ACCIONES, db_index=True)
    modelo = models.CharField(max_length=60, blank=True)
    objeto_id = models.CharField(max_length=40, blank=True)
    descripcion = models.CharField('descripción', max_length=300, blank=True)
    ip = models.GenericIPAddressField('IP', null=True, blank=True)
    navegador = models.CharField(max_length=200, blank=True)

    CLASES_CSS = {
        'login_fallido': 'estado-bad', 'bloqueo': 'estado-bad', 'acceso_denegado': 'estado-bad',
        'eliminar': 'badge-alta', 'desbloqueo': 'badge-alta', 'password': 'badge-alta', 'recuperacion': 'badge-alta',
        'login': 'estado-info', 'logout': 'estado-info', 'acuerdo': 'estado-info',
    }

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y %H:%M} {self.username} {self.get_accion_display()}'

    @property
    def clase_css(self):
        return self.CLASES_CSS.get(self.accion, 'estado-ok')

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError('Los registros de auditoría no se pueden modificar.')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Registros de auditoría'
        ordering = ['-fecha', '-id']
