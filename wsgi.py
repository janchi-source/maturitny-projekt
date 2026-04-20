import os

from app import create_app
from config import DevelopmentConfig, ProductionConfig

if os.getenv("VERCEL") and not os.getenv("UPLOAD_FOLDER"):
    os.environ["UPLOAD_FOLDER"] = "/tmp/uploads"

_env = os.getenv("APP_ENV", "development").strip().lower()
if os.getenv("VERCEL"):
    _config = ProductionConfig
else:
    _config = ProductionConfig if _env == "production" else DevelopmentConfig
if _config is ProductionConfig:
    ProductionConfig.validate()

app = create_app(_config)
