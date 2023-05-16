"""
Django settings for cosapweb project.

Generated by 'django-admin startproject' using Django 4.0.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
import tempfile
from pathlib import Path
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ["COSAP_DJANGO_SECRET"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("COSAP_DJANGO_DEBUG") == "True"

ALLOWED_HOSTS = ["localhost", os.environ.get("COSAP_DJANGO_HOST")]

CSRF_TRUSTED_ORIGINS=[os.environ.get("COSAP_CORS_ALLOWED_ORIGINS")]

CORS_ALLOWED_ORIGINS = [
    "https://localhost:3000",
    os.environ.get("COSAP_BIO_HOST")
    ]

CORS_ALLOWED_ORIGINS = [os.environ.get("COSAP_BIO_HOST", "http://localhost:3000")]
CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "range",
    "cache-control",
    "upload-length",
    "upload-name",
    "upload-offset",
    "x-csrf-token",
]
CORS_ALLOW_CREDENTIALS = True

DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.join(BASE_DIR, "filepond_temp_files")
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = BASE_DIR

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework.authtoken",
    "corsheaders",
    "rest_framework",
    "cosapweb.api",
    "django_drf_filepond",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cosapweb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cosapweb.wsgi.application"

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "cosapweb.authentication.BearerAuthentication",
    ],
}

# Substitute User Model
AUTH_USER_MODEL = "api.CustomUser"

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("COSAP_POSTGRES_NAME", "postgres"),
        "USER": os.environ.get("COSAP_POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("COSAP_POSTGRES_PASSWORD", "postgres"),
        "HOST": "db",
        "PORT": "5432",
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Stored files

MEDIA_ROOT = os.path.join(BASE_DIR, 'data/')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


CELERY_BROKER_URL = "amqp://guest:guest@rabbitmq:5672/vhost"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_TASK_ROUTES = {
    "parse_project_results": {
        "exchange": "cosap_worker",
        "exchange_type": "direct",
        "routing_key": "cosap_worker",
    },
    "cosap_dna_pipeline_task": {
        "exchange": "cosap_worker",
        "exchange_type": "direct",
        "routing_key": "cosap_worker",
    },
}
CELERY_ACCEPT_CONTENT = ["pickle", "json", "msgpack", "yaml"]
CELERY_SEND_TASK = True

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN") ,
    integrations=[
        DjangoIntegration(),
    ],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)