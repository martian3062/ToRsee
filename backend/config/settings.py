from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    import os

    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


SECRET_KEY = env("SECRET_KEY", "dev-only-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [
    host.strip()
    for host in env("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "sources",
    "jobs",
    "reports",
    "ai",
    "integrations",
    "osint",
    "drugintel",
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

ROOT_URLCONF = "config.urls"

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
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ToRsy API",
    "DESCRIPTION": "OSINT, Tor network intelligence, monitoring, and alerting API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "ProcessingStatusEnum": [
            ("queued", "Queued"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
    },
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in env("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    pattern.strip()
    for pattern in env("CORS_ALLOWED_ORIGIN_REGEXES").split(",")
    if pattern.strip()
]

REDIS_URL = env("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)
CELERY_TASK_EAGER_PROPAGATES = True

PROVIDER_MOCK_MODE = env_bool("PROVIDER_MOCK_MODE", True)
INTELLIGENCE_OPERATOR_KEY = env("INTELLIGENCE_OPERATOR_KEY")
INTELLIGENCE_LIVE_ENABLED = env_bool("INTELLIGENCE_LIVE_ENABLED", False)
TELEGRAM_COLLECTION_ENABLED = env_bool("TELEGRAM_COLLECTION_ENABLED", False)
TELEGRAM_WEBHOOK_MAX_BYTES = int(env("TELEGRAM_WEBHOOK_MAX_BYTES", "262144"))

PROVIDER_SETTINGS = {
    "telegram": {
        "token": env("TELEGRAM_BOT_TOKEN"),
        "webhook_secret": env("TELEGRAM_WEBHOOK_SECRET"),
        "default_chat_id": env("TELEGRAM_DEFAULT_CHAT_ID"),
    },
    "groq": {"api_key": env("GROQ_API_KEY"), "model": env("GROQ_MODEL", "llama-3.3-70b-versatile")},
    "huggingface": {
        "token": env("HF_TOKEN"),
        "text_model": env("HF_TEXT_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
        "embed_model": env("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
    },
    "sarvam": {"api_key": env("SARVAM_API_KEY"), "tts_model": env("SARVAM_TTS_MODEL", "bulbul:v2")},
    "tabpfn": {"enabled": env_bool("TABPFN_ENABLED", False)},
    "firecrawl": {"api_key": env("FIRECRAWL_API_KEY")},
    "zenrows": {"api_key": env("ZENROWS_API_KEY")},
    "bright_data": {
        "api_key": env("BRIGHT_DATA_API_KEY"),
        "collector_id": env("BRIGHT_DATA_COLLECTOR_ID"),
    },
    "tinyfish": {"api_key": env("TINYFISH_API_KEY")},
    "pexels": {"api_key": env("PEXELS_API_KEY")},
    "stitch": {"api_key": env("STITCH_API_KEY")},
    "pinecone": {
        "api_key": env("PINECONE_API_KEY"),
        "index": env("PINECONE_INDEX", "torsy"),
        "host": env("PINECONE_HOST"),
    },
    "supabase": {
        "url": env("SUPABASE_URL"),
        "service_role_key": env("SUPABASE_SERVICE_ROLE_KEY"),
    },
}
