import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///promat.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")
    REGISTRATION_INVITE_CODE = os.getenv("REGISTRATION_INVITE_CODE", "PROMAT-BASIC")

    BUILTIN_ADMIN_USERNAME = os.getenv("BUILTIN_ADMIN_USERNAME", "admin")
    BUILTIN_ADMIN_EMAIL = os.getenv("BUILTIN_ADMIN_EMAIL", "admin@mail.eu")
    BUILTIN_ADMIN_PASSWORD = os.getenv("BUILTIN_ADMIN_PASSWORD", "seksos")
