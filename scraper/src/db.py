import logging
import os
import sys
from typing import Generator

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bacterial_user:password@postgres:5432/bacterial_classification")

logger.info(f"Connecting to database at: {DATABASE_URL.split('@')[1].split('/')[0]}")

if "neon.tech" in DATABASE_URL:
    logger.info("Using SSL connection for Neon database")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"sslmode": "require"}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session() -> Session:
    return SessionLocal()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
