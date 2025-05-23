"""
Django settings for IUW project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import environ
import os
import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType, NestedGroupOfNamesType

import base64
# Initialize environ
env = environ.Env(
    # Set default values
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ['*']),
    REDIS_PORT=(int, 6379),
    MAX_UPLOAD_SIZE=(int, 5242880000),  # 5GB in bytes
    IRIDA_TIMEOUT=(int, 10),
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-n(4&*ld9n-cm9$=7w6zp9=^rj73@xn*)k2673@m&vf682=gly4')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DJANGO_DEBUG')

ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')
# Application definition
SITE_URL = 'https://irida.quadram.ac.uk/iuw'
LOGIN_URL = '/iuw/accounts/login/'
LOGIN_REDIRECT_URL = '/iuw/'
LOGOUT_REDIRECT_URL = '/iuw/'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_results',
    'uploader.apps.UploaderConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'IUW.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'IUW.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

if env('DJANGO_ENV', default='development') == 'production':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/iuw/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'uploader.User'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# LDAP Configuration - Only add if LDAP is enabled
if env('USE_LDAP'):
    AUTHENTICATION_BACKENDS.append('django_auth_ldap.backend.LDAPBackend')
    AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = True
    AUTH_LDAP_SERVER_URI = env('LDAP_SERVER_URI', default="ldap://your.ldap.server")
    AUTH_LDAP_BIND_DN = env('LDAP_BIND_DN', default="")
    encoded_password = env('LDAP_BIND_PASSWORD_B64', default="")
    AUTH_LDAP_BIND_PASSWORD = base64.b64decode(encoded_password).decode('utf-8')
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        env('LDAP_SEARCH_BASE', default=""),
        ldap.SCOPE_SUBTREE,
        "(uid=%(user)s)"
    )
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr="CN")
    # Add group configuration
    AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
        env('LDAP_GROUP_SEARCH_BASE', default="ou=groups,dc=example,dc=com"),
        ldap.SCOPE_SUBTREE,
        "(objectClass=groupOfNames)"
    )
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
    
    # Specify which groups should be automatically activated
    AUTH_LDAP_USER_FLAGS_BY_GROUP = {
        "is_active": env('LDAP_AUTO_ACTIVE_GROUPS', default="cn=approved_users,ou=groups,dc=example,dc=com"),
    }

    # Always update user attributes on login
    AUTH_LDAP_ALWAYS_UPDATE_USER = True
    
    AUTH_LDAP_USER_QUERY_FIELD = 'email'
    # Mirror LDAP group assignments
    AUTH_LDAP_MIRROR_GROUPS = True

    # If user is not in auto-active groups, set them as inactive
    AUTH_LDAP_USER_ATTR_MAP = {
        "username": "sAMAccountName",
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
        #"is_active": "userAccountControl",  # This will be overridden by AUTH_LDAP_USER_FLAGS_BY_GROUP
    }

# Redis Settings
REDIS_HOST = env('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = env('REDIS_PORT')
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Celery Settings
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 86400  # 24 hours
CELERY_TASK_SOFT_TIME_LIMIT = 82800  # 23 hours
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_REDIRECT_STDOUTS = False
CELERY_WORKER_REDIRECT_STDOUTS_LEVEL = 'DEBUG'
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_BROKER_CONNECTION_TIMEOUT = 30

# Celery Beat Settings
CELERY_BEAT_SCHEDULE = {
    'update-queue-notifications': {
        'task': 'uploader.tasks.update_queue_notifications',
        'schedule': 5.0,  # Run every 30 seconds
    },
}

# File Upload Settings
UPLOAD_ROOT = env('UPLOAD_ROOT', default=str(BASE_DIR / 'uploads'))
MEDIA_URL = env('MEDIA_URL', default='/media/')
MEDIA_ROOT = env('MEDIA_ROOT', default=str(BASE_DIR / 'media'))
MAX_UPLOAD_SIZE = env('MAX_UPLOAD_SIZE')
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# Email Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.your-email-provider.com')
EMAIL_PORT = env('EMAIL_PORT')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='no-reply@quadram.ac.uk')
#EMAIL_USE_TLS = env('EMAIL_USE_TLS')
#EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='your-email@example.com')
#EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='your-email-password')

# IRIDA Settings
IRIDA_BASE_URL = env('IRIDA_BASE_URL', default='https://your.irida.server')
IRIDA_API_URL = env('IRIDA_API_URL', default='https://your.irida.server')
IRIDA_CLIENT_ID = env('IRIDA_CLIENT_ID', default='')
IRIDA_CLIENT_SECRET = env('IRIDA_CLIENT_SECRET', default='')
IRIDA_USERNAME = env('IRIDA_USERNAME', default='')
IRIDA_PASSWORD = env('IRIDA_PASSWORD', default='')
IRIDA_TIMEOUT = env('IRIDA_TIMEOUT')

# LDAP Settings
USE_LDAP = os.environ.get('USE_LDAP', 'False').lower() == 'true'
