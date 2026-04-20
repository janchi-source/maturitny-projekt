import os

from app import create_app
from config import DevelopmentConfig, ProductionConfig


_env = os.getenv("APP_ENV", "development").strip().lower()
_config = ProductionConfig if _env == "production" else DevelopmentConfig
if _config is ProductionConfig:
    ProductionConfig.validate()

app = create_app(_config)


if __name__ == "__main__":
    cert_file = os.getenv("SSL_CERT_FILE")
    key_file = os.getenv("SSL_KEY_FILE")
    ssl_mode = os.getenv("SSL_MODE", "").strip().lower()
    ssl_context = None
    if cert_file and key_file:
        ssl_context = (cert_file, key_file)
    elif ssl_mode == "adhoc":
        ssl_context = "adhoc"

    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        ssl_context=ssl_context,
    )
    