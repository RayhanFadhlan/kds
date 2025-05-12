import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("db_init.log")
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine
from src.models import Base

def init_db():
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bacterial_user:password@postgres:5432/bacterial_classification")

    try:
        if "neon.tech" in DATABASE_URL:
            logger.info("Using SSL connection for Neon database")
            engine = create_engine(
                DATABASE_URL,
                connect_args={"sslmode": "require"}
            )
        else:
            engine = create_engine(DATABASE_URL)

        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)

        logger.info("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    success = init_db()
    if success:
        logger.info("Database initialization completed successfully!")
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)
