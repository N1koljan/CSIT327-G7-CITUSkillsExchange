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
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

if DEBUG and 'localhost' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.extend(['localhost', '127.0.0.1'])

# ---------------------------
# CSRF Trusted Origins
# ---------------------------
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

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

    # ❌ WRONG: Do not put it here.
    # 'cloudinary_storage',

    'django.contrib.staticfiles',  # <--- Static files must come FIRST

    # ✅ CORRECT: Put it here, AFTER staticfiles
 #   'cloudinary_storage',
 #   'cloudinary',
    'storages',
    'ui',
    'core',
    'channels',
]

# ---------------------------
# Middleware
# ---------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
# Database configuration
# ---------------------------
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.getenv("PGHOST"),
            "PORT": os.getenv("PGPORT"),
            "USER": os.getenv("PGUSER"),
            "PASSWORD": os.getenv("PGPASSWORD"),
            "NAME": os.getenv("PGDATABASE"),
            "CONN_MAX_AGE": 0,
            "OPTIONS": {
                "sslmode": os.getenv("PGSSLMODE", "require"),
            },
        }
    }
else:
    DATABASE_URL = os.environ.get("DATABASE_URL")
    db_config = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=60,
        ssl_require=True
    )
    db_config['PORT'] = '6543'
    DATABASES = {
        'default': db_config
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
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# ---------------------------
# Static files (CSS, JavaScript, Images)
# ---------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Keep WhiteNoise for CSS/JS - it's faster for static assets
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [BASE_DIR / "static"]

# ---------------------------
# Media files (User Uploads) & Cloudinary
# ---------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 👇 CHANGED: Cloudinary Configuration
#CLOUDINARY_STORAGE = {
#    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', 'dvobk6ehs'),
#    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', '278777249963586'),
 #   'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', '-aTTYbEcK04fJOV96KwrU7rGD10'),
#}

# 👇 CHANGED: Tell Django to use Cloudinary for uploaded media
# DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ---------------------------
# Authentication
# ---------------------------
AUTH_USER_MODEL = 'core.CustomUser'
LOGIN_REDIRECT_URL = '/profile/'
LOGIN_URL = '/login/'
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
# Security settings
# ---------------------------
if not DEBUG:
    if os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true":
        SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------
# Email Configuration
# ---------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'mgerardgrant@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'CIT-U Skills Exchange <mgerardgrant@gmail.com>'

# 2. SUPABASE STORAGE SETTINGS (Replaces Cloudinary)
AWS_ACCESS_KEY_ID = os.environ.get('SUPABASE_PROJECT_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
AWS_STORAGE_BUCKET_NAME = 'media'
AWS_S3_ENDPOINT_URL = f'https://{AWS_ACCESS_KEY_ID}.supabase.co/storage/v1/s3'

# Technical settings to make Supabase happy
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False  # <--- This makes the image links public (fixes the broken image icon)

# Tell Django to use Supabase S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# 👇 ADD THIS LINE
# This forces the link to be the clean, public format
AWS_S3_CUSTOM_DOMAIN = f'{AWS_ACCESS_KEY_ID}.supabase.co/storage/v1/object/public/{AWS_STORAGE_BUCKET_NAME}'