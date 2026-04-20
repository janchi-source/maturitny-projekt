import os

from app import create_app
from config import DevelopmentConfig, ProductionConfig

_env = os.getenv("APP_ENV", "development").strip().lower()
_config = ProductionConfig if _env == "production" else DevelopmentConfig
if _config is ProductionConfig:
    ProductionConfig.validate()

app = create_app(_config)
