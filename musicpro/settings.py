"""
Configuración del proyecto Music Pro Courier (Evaluación 3 - Aplicación web con CRUD).

Los valores sensibles (clave secreta, credenciales de MySQL) se leen desde
variables de entorno o desde un archivo ``.env`` en la raíz del proyecto
(ver ``.env.example``). Así no quedan escritos en el código ni en GitHub.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured

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
    # Evita que el navegador guarde en caché páginas privadas: después de
    # cerrar sesión, el botón "Atrás" no vuelve a mostrar datos protegidos.
    'courier.middleware.SinCacheParaUsuariosAutenticadosMiddleware',
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
]

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
