from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker 
from models import Base 
from core.config import DB_PATH 

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

try:
    Base.metadata.create_all(engine)
except Exception as e:
                                                     
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()
