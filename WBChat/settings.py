
from pathlib import Path
import os
import dj_database_url
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-99d_ev36(!f#!46nr@ab5g4@%nynk$pb@fs5_(%v0q(hbr0s#q'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '.serveousercontent.com',
    '.ngrok-free.app',
    '.trycloudflare.com',
    "wbchat-production.up.railway.app",
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
    'https://*.serveousercontent.com',
    'https://*.trycloudflare.com',
]


# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'channels',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    # Local apps
    'accounts',
    'news',
    'chat',
    'org',
    'documents',
    'notifications',
    'integrations',
    'knowledge',
    'surveys',
    'tinymce',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'WBChat.middleware.Custom404Middleware',
]

ROOT_URLCONF = 'WBChat.urls'

import os

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # <--- вот эта строка
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.notifications_count',
            ],
        },
    },
]


WSGI_APPLICATION = 'WBChat.wsgi.application'
ASGI_APPLICATION = 'WBChat.asgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600
    )
}
# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True
AUTH_USER_MODEL = 'accounts.User'


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# CHANNELS & REDIS CONFIGURATION
# ==============================================================================

# Channel Layers for WebSocket support
# Using in-memory backend for development (will switch to Redis in production)


# To use Redis (uncomment when Redis is running):
CHANNEL_LAYERS = {
'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
         },
     },
 }

# Redis configuration for Celery
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# Celery Configuration
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ==============================================================================
# REST FRAMEWORK CONFIGURATION
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ==============================================================================
# CORS CONFIGURATION
# ==============================================================================

# CORS settings for frontend development
CORS_ALLOW_ALL_ORIGINS = True  # Set to False in production
CORS_ALLOW_CREDENTIALS = True

# In production, use specific origins:
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",  # React dev server
#     "http://localhost:5173",  # Vite dev server
#     "https://your-production-domain.com",
# ]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ==============================================================================
# WEBSOCKET CONFIGURATION
# ==============================================================================

# WebSocket configuration
WEBSOCKET_URL = 'ws://localhost:8000/ws/'
WEBSOCKET_HEARTBEAT_INTERVAL = 30  # seconds
WEBSOCKET_DISCONNECT_TIMEOUT = 60  # seconds

# ==============================================================================
# INTEGRATIONS CONFIGURATION
# ==============================================================================

INTEGRATIONS = {
    # HR Provider - переключить на OneCHRProvider в продакшене
    'HR_PROVIDER': 'integrations.hr.mock.MockHRProvider',
    # Auth Provider - переключить на KeycloakProvider в продакшене
    'AUTH_PROVIDER': 'integrations.auth.mock.MockAuthProvider',
    # Document System Provider
    'DOCUMENT_PROVIDER': 'integrations.documents.mock.MockTezisProvider',
    # Интервал синхронизации (часы)
    'SYNC_INTERVAL_HOURS': 1,
    # 1C Settings (для продакшена)
    # 'ONEC_URL': 'https://1c.wbbank.ru/api/',
    # 'ONEC_USERNAME': '',
    # 'ONEC_PASSWORD': '',
    # Keycloak Settings (для продакшена)
    # 'KEYCLOAK_URL': 'https://keycloak.wbbank.ru/',
    # 'KEYCLOAK_REALM': 'wbbank',
    # 'KEYCLOAK_CLIENT_ID': '',
    # 'KEYCLOAK_CLIENT_SECRET': '',
}

# ==============================================================================
# DOCUMENTS CONFIGURATION
# ==============================================================================

DOCUMENTS = {
    'MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50 MB
    'ALLOWED_EXTENSIONS': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf'],
    'PREVIEW_ENABLED': True,
    'SEARCH_CONFIG': 'russian',  # PostgreSQL FTS config
}

# ==============================================================================
# CELERY BEAT SCHEDULE
# ==============================================================================

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'sync-employees-hourly': {
        'task': 'integrations.tasks.sync_employees_from_hr',
        'schedule': crontab(minute=0),  # Каждый час
    },
    'sync-departments-daily': {
        'task': 'integrations.tasks.sync_departments_from_hr',
        'schedule': crontab(hour=1, minute=0),  # В 01:00
    },
    'sync-positions-daily': {
        'task': 'integrations.tasks.sync_positions_from_hr',
        'schedule': crontab(hour=1, minute=30),  # В 01:30
    },
    'update-employee-statuses': {
        'task': 'integrations.tasks.update_employee_statuses',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
    },
    'archive-terminated-employees': {
        'task': 'integrations.tasks.archive_terminated_employees',
        'schedule': crontab(hour=2, minute=0),  # В 02:00
    },
    'kb-check-review-deadlines': {
        'task': 'knowledge.tasks.check_review_deadlines',
        'schedule': crontab(hour=8, minute=0),  # В 08:00 ежедневно
    },
    'kb-update-tag-counts': {
        'task': 'knowledge.tasks.update_tag_counts',
        'schedule': crontab(hour=3, minute=0),  # В 03:00 ежедневно
    },
}

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'wbchat.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'integrations': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'documents': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}


# === TinyMCE ===
TINYMCE_DEFAULT_CONFIG = {
    'license_key': 'gpl',
    'height': 500,
    'menubar': 'file edit view insert format tools table',
    'plugins': [
        'advlist', 'autolink', 'lists', 'link', 'image', 'charmap',
        'preview', 'anchor', 'searchreplace', 'visualblocks', 'code',
        'fullscreen', 'insertdatetime', 'media', 'table', 'codesample',
        'help', 'wordcount', 'emoticons',
    ],
    'toolbar': (
        'undo redo | blocks | bold italic underline strikethrough | '
        'forecolor backcolor | alignleft aligncenter alignright alignjustify | '
        'bullist numlist outdent indent | link image media table codesample | '
        'removeformat | fullscreen preview | help'
    ),
    'codesample_languages': [
        {'text': 'Python', 'value': 'python'},
        {'text': 'JavaScript', 'value': 'javascript'},
        {'text': 'HTML/XML', 'value': 'markup'},
        {'text': 'CSS', 'value': 'css'},
        {'text': 'SQL', 'value': 'sql'},
        {'text': 'Bash', 'value': 'bash'},
        {'text': 'JSON', 'value': 'json'},
    ],
    'language': 'ru',
    'content_css': 'default',
    'skin': 'oxide-dark',
    'promotion': False,
    'branding': False,
    'image_advtab': True,
    'automatic_uploads': True,
    'file_picker_types': 'image',
}
