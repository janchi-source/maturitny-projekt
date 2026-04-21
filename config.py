import os

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(url):
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _default_database_url():
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/promat.db"
    return "sqlite:///promat.db"


def _default_upload_folder():
    if os.getenv("VERCEL"):
        return "/tmp/uploads"
    return "uploads"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.getenv("DATABASE_URL", _default_database_url()))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", _default_upload_folder())
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "https")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), True)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.getenv("REMEMBER_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = _as_bool(os.getenv("REMEMBER_COOKIE_SECURE"), True)
    WTF_CSRF_SSL_STRICT = _as_bool(os.getenv("WTF_CSRF_SSL_STRICT"), True)
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", "3600"))
    PROXY_FIX_X_FOR = int(os.getenv("PROXY_FIX_X_FOR", "1"))
    PROXY_FIX_X_PROTO = int(os.getenv("PROXY_FIX_X_PROTO", "1"))
    PROXY_FIX_X_HOST = int(os.getenv("PROXY_FIX_X_HOST", "1"))
    PROXY_FIX_X_PORT = int(os.getenv("PROXY_FIX_X_PORT", "1"))
    PROXY_FIX_X_PREFIX = int(os.getenv("PROXY_FIX_X_PREFIX", "1"))
    ENFORCE_HTTPS = _as_bool(os.getenv("ENFORCE_HTTPS"), True)
    HSTS_ENABLED = _as_bool(os.getenv("HSTS_ENABLED"), True)
    HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))
    HSTS_INCLUDE_SUBDOMAINS = _as_bool(os.getenv("HSTS_INCLUDE_SUBDOMAINS"), True)
    HSTS_PRELOAD = _as_bool(os.getenv("HSTS_PRELOAD"), False)

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:26b")
    OLLAMA_INSIGHTS_MODEL = os.getenv("OLLAMA_INSIGHTS_MODEL", "gemma3:1b")
    REGISTRATION_INVITE_CODE = os.getenv("REGISTRATION_INVITE_CODE", "PROMAT-BASIC")

    BUILTIN_ADMIN_USERNAME = os.getenv("BUILTIN_ADMIN_USERNAME", "admin")
    BUILTIN_ADMIN_EMAIL = os.getenv("BUILTIN_ADMIN_EMAIL", "admin@mail.eu")
    BUILTIN_ADMIN_PASSWORD = os.getenv("BUILTIN_ADMIN_PASSWORD", "seksos")


class DevelopmentConfig(Config):
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), False)
    REMEMBER_COOKIE_SECURE = _as_bool(os.getenv("REMEMBER_COOKIE_SECURE"), False)
    WTF_CSRF_SSL_STRICT = _as_bool(os.getenv("WTF_CSRF_SSL_STRICT"), False)
    ENFORCE_HTTPS = _as_bool(os.getenv("ENFORCE_HTTPS"), False)
    HSTS_ENABLED = _as_bool(os.getenv("HSTS_ENABLED"), False)


class ProductionConfig(Config):
    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY:
            raise RuntimeError("SECRET_KEY must be set for production.")
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError("DATABASE_URL must be set for production.")
