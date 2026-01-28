from pathlib import Path
import os
from sqlalchemy import create_engine
import sys

HERE = Path(__file__).resolve().parent.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from modules.cits.models import Base
import logging
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "customer_issue.db"

if DB_PATH.exists():
    logger.info("Removing existing DB: %s", DB_PATH)
    try:
        DB_PATH.unlink()
    except Exception:
        logger.exception("Failed to remove DB")
        raise

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
logger.info("Creating database and tables...")
Base.metadata.create_all(bind=engine)
logger.info("Done. New DB created at: %s", DB_PATH)

