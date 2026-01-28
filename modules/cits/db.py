from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

DB_PATH = Path(__file__).parent.parent.parent / "customer_issue.db"

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


def get_customer_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_customer_db_sync() -> Session:
    db = SessionLocal()
    return db

