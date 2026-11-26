"""
Django settings for core project.
"""

from pathlib import Path
from datetime import timedelta
import os
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-k877m6gp(e#(pvxy%lx+j%a(b5)+l2zx$^=dtj49_=k)a=97&_'
DEBUG = True


ALLOWED_HOSTS = ['*']


# ==========================================
# 1. TENANT & APPS CONFIGURATION
# ==========================================

SHARED_APPS = (
    'django_tenants', 

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party Apps
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'storages',
    # 'rest_framework_simplejwt.token_blacklist'
    # Local Apps (Shared data)
    'accounts',
    'cinemas',  # چون مدل CinemaBranch اینجاست، باید در Shared باشد
    'profiles',
)

# اپلیکیشن‌هایی که دیتای ایزوله دارند (برای هر سینما یک دیتابیس جدا ساخته می‌شود)
TENANT_APPS = (
    'orders',
    'payments',
    'promotions',
    'notifications',
    'operations'
)

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# معرفی مدل مستأجر و دامنه به پکیج
TENANT_MODEL = "cinemas.Cinema"
TENANT_DOMAIN_MODEL = "cinemas.CinemaDomain"

# ==========================================
# 2. CUSTOM USER MODEL
# ==========================================
AUTH_USER_MODEL = 'accounts.User'


# ==========================================
# 3. DATABASE ROUTER & MIDDLEWARE
# ==========================================
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware', # 🔴 باید حتماً اولین میدلور باشد!
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'core.wsgi.application'


# ==========================================
# 4. DATABASE (PostgreSQL for Multi-Tenancy)
# ==========================================
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend', # انجین مخصوص معماری چندمستأجری
        'NAME': 'seatmatrix_db',
        'USER': 'postgres',
        'PASSWORD': '123',
        'HOST': 'db',  # اشاره به سرویس دیتابیس در فایل docker-compose
        'PORT': '5432',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# ==========================================
# 5. INTERNATIONALIZATION
# ==========================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'


# ==========================================
# 6. REST FRAMEWORK & JWT SETTINGS
# ==========================================


# تنظیمات Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',   # جلوگیری از اسپم شدن اندپوینت‌های لاگین و OTP
        'user': '120/minute',
    },
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # تنظیمات اختصاصی کوکی
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_SECURE': not DEBUG,
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SeatMatrix Cinema SaaS API',
    'DESCRIPTION': 'Multi-tenant Cinema Management and Ticket Booking API',
    'VERSION': '1.0.0',
    'COMPONENT_SPLIT_REQUEST': True,
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'withCredentials': True,
    },
}



DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'







# ==================== Object Storage (S3 / MinIO) ====================
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin123')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'cinema-media')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', 'http://minio:9000')


AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN', f'localhost:9000/{AWS_STORAGE_BUCKET_NAME}')
AWS_S3_URL_PROTOCOL = os.getenv('AWS_S3_URL_PROTOCOL', 'http:')

AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False  
AWS_S3_ADDRESSING_STYLE = "path"

STORAGES = {
    "default": {
        "BACKEND": "core.storage.TenantS3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}



BASE_DOMAIN = 'lvh.me'
COOKIE_DOMAIN = '.lvh.me'
ALLOWED_HOSTS = ['.lvh.me', '.localhost', '127.0.0.1']





CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}




# ==================== Payment Gateway (ZarinPal v4) ====================
ZARINPAL_MERCHANT_ID = os.getenv(
    'ZARINPAL_MERCHANT_ID',
    '12345678-1234-1234-1234-123456789012',
)
ZARINPAL_SANDBOX = os.getenv('ZARINPAL_SANDBOX', 'True').lower() == 'true'
ZARINPAL_CURRENCY = os.getenv('ZARINPAL_CURRENCY', 'IRT')  











# ==================== Celery & Celery Beat ====================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


CELERY_BEAT_SCHEDULE = {
    'cancel-expired-pending-orders-every-5-mins': {
        'task': 'orders.tasks.cancel_expired_pending_orders',
        'schedule': crontab(minute='*/5'),
    },
}