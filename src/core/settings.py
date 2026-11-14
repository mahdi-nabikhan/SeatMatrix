"""
Django settings for core project.
"""

from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-k877m6gp(e#(pvxy%lx+j%a(b5)+l2zx$^=dtj49_=k)a=97&_'
DEBUG = True

# برای محیط توسعه داکر، اجازه دسترسی به همه هاست‌ها را می‌دهیم
ALLOWED_HOSTS = ['*']


# ==========================================
# 1. TENANT & APPS CONFIGURATION
# ==========================================
# اپلیکیشن‌هایی که دیتای عمومی دارند (فقط در Public Schema ذخیره می‌شوند)
SHARED_APPS = (
    'django_tenants',  # 🔴 باید حتماً اولین گزینه باشد!

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
)

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# معرفی مدل مستأجر و دامنه به پکیج
TENANT_MODEL = "cinemas.CinemaBranch"
TENANT_DOMAIN_MODEL = "cinemas.BranchDomain"


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

# تنظیمات SimpleJWT و مدیریت کوکی‌های امن
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # عمر کوتاه برای امنیت بالا
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # عمر طولانی‌تر برای تمدید خودکار
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # تنظیمات اختصاصی کوکی
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_SECURE': not DEBUG,   # در حالت لوکال False و در سرور واقعی خودکار True می‌شود
    'AUTH_COOKIE_HTTP_ONLY': True,     # جلوگیری از دسترسی جاوااسکریپت (ضد XSS)
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
}

# تنظیمات مستندات Swagger (drf-spectacular)
SPECTACULAR_SETTINGS = {
    'TITLE': 'SeatMatrix Cinema SaaS API',
    'DESCRIPTION': 'Multi-tenant Cinema Management and Ticket Booking API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'withCredentials': True,  # حیاتی: باعث می‌شود Swagger کوکی‌های HttpOnly را در درخواست‌ها بفرستد
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Cinema SaaS API',
    'DESCRIPTION': 'API documentation for the Cinema Booking Marketplace',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}




DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'