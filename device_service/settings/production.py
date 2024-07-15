"""
Production settings
"""

from .common import *  # noqa

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

DEBUG = os.getenv("ENV", default="dev") == "dev"  # noqa

SECRET_KEY = os.getenv(  # noqa
    "SECRET_KEY", "django-insecure-*$0b8ibx7uzk45cm+fxw7*jj(yzi2ye!l4+!dnyxa-u-nbuz=q"
)

ALLOWED_HOSTS = [os.getenv("ALLOWED_HOSTS", "*")]  # noqa

HOST = os.getenv("HOST", "http://localhost:8000/")  # noqa
DEFAULT_TENANT_HOST = os.getenv("DEFAULT_TENANT_HOST", "localhost")  # noqa

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": os.getenv("DB_NAME", "spacedf_device_service"),  # noqa
        "USER": os.getenv("DB_USERNAME", "postgres"),  # noqa
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),  # noqa
        "HOST": os.getenv("DB_HOST", "localhost"),  # noqa
        "PORT": "5432",
    }
}

# CORS config
CORS_ALLOWED_ORIGINS = os.getenv(  # noqa
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")

# JWT config
SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "JWK_URL": os.getenv(  # noqa
        "JWK_URL", "http://localhost:8001/api/.well-known/jwks.json"
    ),
}

# Celery
CELERY_BROKER_URL = os.getenv(  # noqa
    "CELERY_BROKER_URL", "amqp://guest:guest@localhost"
)
