import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Los valores reales (contraseñas, dominios) van en backend/.env, que NO se sube a git.
# Ver backend/.env.example.
load_dotenv(BASE_DIR / ".env")


def _lista(nombre, defecto=""):
    return [v.strip() for v in os.environ.get(nombre, defecto).split(",") if v.strip()]


SECRET_KEY = os.environ.get("SECRET_KEY", "solo-para-desarrollo-cambia-esta-clave-en-produccion")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = _lista("ALLOWED_HOSTS", "*")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "asistencia",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # debe ir lo más arriba posible
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# Solo lo usa el admin técnico de Django (/django-admin/). La interfaz está en frontend/.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "asistencia_db"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "es"
# Zona horaria de Bolivia: evita que una marca a las 21:00 caiga en "otro día".
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ───────────── API (Django REST Framework + JWT) ─────────────

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["asistencia.auth.JWTEstudianteOAdmin"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SIMPLE_JWT = {
    # Una jornada de trabajo. Al vencer, el frontend vuelve a pedir el login.
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=int(os.environ.get("JWT_HORAS", "8"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Dominio(s) del frontend que pueden llamar a la API.
CORS_ALLOWED_ORIGINS = _lista("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
# Para que el frontend pueda leer el nombre del Excel exportado.
CORS_EXPOSE_HEADERS = ["Content-Disposition"]
