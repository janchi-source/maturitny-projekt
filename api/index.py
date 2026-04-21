import os

if os.getenv("VERCEL") and not os.getenv("UPLOAD_FOLDER"):
	os.environ["UPLOAD_FOLDER"] = "/tmp/uploads"
if os.getenv("VERCEL"):
	db_url = os.getenv("DATABASE_URL", "").strip()
	if not db_url or db_url == "sqlite:///promat.db":
		os.environ["DATABASE_URL"] = "sqlite:////tmp/promat.db"
	elif db_url.startswith(("postgres://", "postgresql://")):
		try:
			import psycopg2  # noqa: F401
		except Exception:
			os.environ["DATABASE_URL"] = "sqlite:////tmp/promat.db"
	if not os.getenv("SECRET_KEY"):
		os.environ["SECRET_KEY"] = "vercel-runtime-secret"

from app import create_app
from config import ProductionConfig

ProductionConfig.validate()
app = create_app(ProductionConfig)
