

from pathlib import Path 
from sqlalchemy import create_engine 
from sqlalchemy .orm import sessionmaker ,Session 

from modules .svit .models import Base 

DB_PATH =Path (__file__ ).parent .parent .parent /"svit.db"

svit_engine =create_engine (
f"sqlite:///{DB_PATH }",
echo =False ,
connect_args ={"check_same_thread":False }
)

SessionLocal = sessionmaker(bind=svit_engine, expire_on_commit=False)

try:
    Base.metadata.create_all(bind=svit_engine)
except Exception as e:
                                                     
    pass


def get_svit_db ()->Session :
    db =SessionLocal ()
    try :
        yield db 
    finally :
        db .close ()


def get_svit_db_sync ()->Session :
    db =SessionLocal ()
    return db 

