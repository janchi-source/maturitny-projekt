from app import create_app
from config import ProductionConfig

ProductionConfig.validate()
app = create_app(ProductionConfig)
