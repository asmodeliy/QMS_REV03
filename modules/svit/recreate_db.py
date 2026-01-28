
import os
from pathlib import Path
from sqlalchemy import create_engine
from modules.svit.models import Base
import logging

logger = logging.getLogger(__name__)

SVIT_DB_PATH = Path(__file__).parent.parent.parent / "svit.db"

def recreate_database():
    logger.info("Recreating SVIT DB: %s", SVIT_DB_PATH)
    
    if SVIT_DB_PATH.exists():
        backup_path = SVIT_DB_PATH.with_suffix(".db.backup")
        logger.info("Backing up existing DB to: %s", backup_path.name)
        os.rename(SVIT_DB_PATH, backup_path)
    
    engine = create_engine(f"sqlite:///{SVIT_DB_PATH}", echo=False)
    Base.metadata.create_all(engine)
    
    logger.info("SVIT DB created: %s", SVIT_DB_PATH.name)
    logger.info("Backup file: %s", SVIT_DB_PATH.with_suffix('.db.backup').name)

if __name__ == "__main__":
    try:
        recreate_database()
    except Exception:
        logger.exception("Failed to recreate SVIT database")
        exit(1)

