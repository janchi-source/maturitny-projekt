import os

from app import create_app
from config import ProductionConfig

if os.getenv("VERCEL") and not os.getenv("UPLOAD_FOLDER"):
	os.environ["UPLOAD_FOLDER"] = "/tmp/uploads"

ProductionConfig.validate()
app = create_app(ProductionConfig)
