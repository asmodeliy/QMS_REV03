
"""
공통 인증 DB 연결 관리 (auth_db.db)
"""

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
    """공통 인증 DB 세션 생성 (의존성 주입용)"""
    db =AuthSessionLocal ()
    try :
        yield db 
    finally :
        db .close ()


def get_auth_db_sync ()->Session :
    """동기 코드에서 사용할 인증 DB 세션"""
    db =AuthSessionLocal ()
    return db 
