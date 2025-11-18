import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------
# Base directory
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------
# Load environment variables
# ---------------------------
# Load .env in local dev only (not on Render)
if os.environ.get("RENDER", "") != "true":
    dotenv_path = BASE_DIR / "skills_exchange" / ".env"
    load_dotenv(dotenv_path)

# ---------------------------
# Django secret key and debug
# ---------------------------
SECRET_KEY = os.environ.get('SECRET_KEY', os.environ.get('DJANGO_SECRET_KEY', 'unsafe-dev-key'))
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

# ---------------------------
# Allowed hosts configuration
# ---------------------------
ALLOWED_HOSTS = [h.strip() for h in
                 os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

# Backward compatibility with RENDER_EXTERNAL_HOSTNAME
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Add localhost for local development if DEBUG is True
if DEBUG and 'localhost' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend(['localhost', '127.0.0.1'])

# ---------------------------
# CSRF Trusted Origins
# ---------------------------
CSRF_TRUSTED_ORIGINS = [o.strip() for o in
                        os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# ---------------------------
# Installed apps
# ---------------------------
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ui',
    'core',
    'channels',
]

# ---------------------------
# Middleware
# ---------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ---------------------------
# URL configuration
# ---------------------------
ROOT_URLCONF = 'skills_exchange.urls'

# ---------------------------
# Templates
# ---------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ---------------------------
# WSGI application
# ---------------------------
WSGI_APPLICATION = 'skills_exchange.wsgi.application'

# ---------------------------
# Database configuration (Supabase PostgreSQL)
# ---------------------------
if DEBUG:
    # LOCAL DEVELOPMENT - using individual Supabase credentials
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.getenv("PGHOST"),
            "PORT": os.getenv("PGPORT"),
            "USER": os.getenv("PGUSER"),
            "PASSWORD": os.getenv("PGPASSWORD"),
            "NAME": os.getenv("PGDATABASE"),
            "OPTIONS": {
                "sslmode": os.getenv("PGSSLMODE", "require"),
            },
        }
    }
else:
    # RENDER DEPLOYMENT - using DATABASE_URL
    DATABASE_URL = os.environ.get("DATABASE_URL")
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }

# ---------------------------
# Password validation
# ---------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------
# Internationalization
# ---------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------
# Static files
# ---------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [BASE_DIR / "static"]

# ---------------------------
# Media files
# ---------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------
# Authentication
# ---------------------------
AUTH_USER_MODEL = 'core.CustomUser'
LOGIN_REDIRECT_URL = '/profile/'
LOGIN_URL = '/login/'

# ---------------------------
# Default primary key field type
# ---------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------
# ASGI / Channels configuration
# ---------------------------
ASGI_APPLICATION = 'skills_exchange.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# ---------------------------
# Security settings (production)
# ---------------------------
if not DEBUG:
    # Enable security features in production
    if os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true":
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_BROWSER_XSS_FILTER = True
        SECURE_CONTENT_TYPE_NOSNIFF = True