
from sqlalchemy import create_engine 
from sqlalchemy .orm import sessionmaker ,Session 
from pathlib import Path 
from core .auth .models import Base 
from core .config import BASE_DIR 


AUTH_DB_PATH =BASE_DIR /"auth_db.db"


auth_engine =create_engine (f"sqlite:///{AUTH_DB_PATH }",future =True )
AuthSessionLocal =sessionmaker (bind =auth_engine ,expire_on_commit =False ,future =True )


Base .metadata .create_all (auth_engine )


def get_auth_db ()->Session :
    db =AuthSessionLocal ()
    try :
        yield db 
    finally :
        db .close ()


def get_auth_db_sync ()->Session :
    db =AuthSessionLocal ()
    return db 
