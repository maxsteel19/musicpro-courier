"""
Configuración del proyecto Music Pro Courier (Evaluación 3 - Aplicación web con CRUD).

Los valores sensibles (clave secreta, credenciales de MySQL) se leen desde
variables de entorno o desde un archivo ``.env`` en la raíz del proyecto
(ver ``.env.example``). Así no quedan escritos en el código ni en GitHub.
"""
import base64
import hashlib
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_archivo_env(ruta):
    """Carga pares CLAVE=valor desde un archivo .env sin dependencias externas.

    Las variables que ya existen en el sistema tienen prioridad sobre el archivo.
    """
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, valor = linea.split('=', 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_archivo_env(BASE_DIR / '.env')


def _env_bool(nombre, por_defecto):
    return os.environ.get(nombre, str(por_defecto)).lower() in {'true', '1', 'yes', 'si', 'sí'}


DEBUG = _env_bool('DJANGO_DEBUG', True)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY cuando DJANGO_DEBUG está desactivado.')
    SECRET_KEY = 'django-insecure-musicpro-courier-solo-desarrollo'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]

# Evaluación 3: el sistema usa un administrador propio, por lo que
# django.contrib.admin NO está instalado.
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'courier',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Content-Security-Policy: el navegador solo ejecuta scripts del propio sitio.
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    # Evita que el navegador guarde en caché páginas privadas: después de
    # cerrar sesión, el botón "Atrás" no vuelve a mostrar datos protegidos.
    'courier.middleware.SinCacheParaUsuariosAutenticadosMiddleware',
    # Obliga a aceptar el acuerdo de uso de datos y a cambiar claves temporales.
    'courier.middleware.ControlDeCuentaMiddleware',
]

ROOT_URLCONF = 'musicpro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csp',
                'courier.context_processors.datos_generales',
            ],
        },
    },
]

WSGI_APPLICATION = 'musicpro.wsgi.application'

# ---------------------------------------------------------------------------
# Base de datos: MySQL local (requisito de la Evaluación 3).
# Para pruebas rápidas sin MySQL se puede usar DB_ENGINE=sqlite.
# ---------------------------------------------------------------------------
DB_ENGINE = os.environ.get('DB_ENGINE', 'mysql').lower()

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'musicpro_courier'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            'TEST': {
                'NAME': os.environ.get('DB_TEST_NAME', 'test_musicpro_courier'),
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_unicode_ci',
            },
        }
    }
else:
    raise ImproperlyConfigured("DB_ENGINE debe ser 'mysql' o 'sqlite'.")

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    # Propio: exige combinar letras, números y símbolos.
    {'NAME': 'courier.validators.ComplejidadPasswordValidator'},
]

# Bloqueo de cuentas tras intentos fallidos de inicio de sesión.
LOGIN_MAX_INTENTOS = int(os.environ.get('LOGIN_MAX_INTENTOS', 5))
LOGIN_MINUTOS_BLOQUEO = int(os.environ.get('LOGIN_MINUTOS_BLOQUEO', 15))

# Recuperación de contraseña: el enlace del correo vence en 1 hora.
PASSWORD_RESET_TIMEOUT = 60 * 60
# En desarrollo el correo se muestra en la consola de "runserver".
# En producción se configura un servidor SMTP en el archivo .env.
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'courier.correo.ConsolaLegibleEmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Music Pro Courier <no-responder@musicpro.cl>')

# Versión vigente del acuerdo de uso de datos. Si se modifica el texto del
# acuerdo, se sube la versión y todos los usuarios deben aceptarlo de nuevo.
VERSION_ACUERDO_DATOS = '1.0'

# Clave para cifrar datos personales en la base de datos (courier/cifrado.py).
CLAVE_CIFRADO_DATOS = os.environ.get('DJANGO_CLAVE_CIFRADO')
if not CLAVE_CIFRADO_DATOS:
    if not DEBUG:
        raise ImproperlyConfigured('Defina DJANGO_CLAVE_CIFRADO cuando DJANGO_DEBUG está desactivado.')
    # Solo en desarrollo: se deriva de SECRET_KEY para que el proyecto funcione sin configurar nada.
    CLAVE_CIFRADO_DATOS = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()).decode()

# ---------------------------------------------------------------------------
# Autenticación y sesión
# ---------------------------------------------------------------------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'courier:dashboard'
LOGOUT_REDIRECT_URL = 'login'

SESSION_COOKIE_AGE = int(os.environ.get('DJANGO_SESSION_SECONDS', 60 * 60))  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # la hora de expiración se renueva con la actividad
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# Content-Security-Policy. Los estilos en línea se permiten porque los
# gráficos usan style="width: ..%"; los scripts en línea necesitan un nonce.
SECURE_CSP = {
    'default-src': [CSP.SELF],
    'script-src': [CSP.SELF, CSP.NONCE],
    'style-src': [CSP.SELF, CSP.UNSAFE_INLINE],
    'img-src': [CSP.SELF, 'data:'],
    'font-src': [CSP.SELF],
    'connect-src': [CSP.SELF],
    'object-src': [CSP.NONE],
    'base-uri': [CSP.SELF],
    'form-action': [CSP.SELF],
    'frame-ancestors': [CSP.NONE],
}

# En producción (DEBUG=False) todo el tráfico va cifrado con TLS (HTTPS).
if not DEBUG:
    SECURE_SSL_REDIRECT = _env_bool('DJANGO_SSL_REDIRECT', True)
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', 60 * 60 * 24 * 365))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ---------------------------------------------------------------------------
# Internacionalización
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Bootstrap usa "danger" en vez de "error" para los mensajes en rojo.
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}
