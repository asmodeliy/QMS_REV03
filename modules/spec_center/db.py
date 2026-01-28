from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from modules.spec_center.models import Base

DB_PATH = Path(__file__).parent.parent.parent / "spec_center.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
                                                     
    pass


def get_spec_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_spec_db_sync() -> Session:
    db = SessionLocal()
    return db

