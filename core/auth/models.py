
from datetime import datetime 
from enum import Enum 
from sqlalchemy .orm import declarative_base ,Mapped ,mapped_column 
from sqlalchemy import String ,Enum as SAEnum, Float
import hashlib 
import secrets 

Base =declarative_base ()

class RoleEnum (str ,Enum ):
    ADMIN ="Admin"
    MANAGER ="Manager"
    USER ="User"

    def __str__ (self ):
        return self .value 


class User (Base ):
    __tablename__ ="users"
    id :Mapped [int ]=mapped_column (primary_key =True )
    email :Mapped [str ]=mapped_column (String (256 ),unique =True ,index =True )
    english_name :Mapped [str ]=mapped_column (String (128 ),default ="")
    password_hash :Mapped [str ]=mapped_column (String (256 ))
    department :Mapped [str ]=mapped_column (String (128 ),default ="")
    role :Mapped [str ]=mapped_column (String (50 ),default ="User")
    is_active :Mapped [bool ]=mapped_column (default =True )
    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
    updated_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow ,onupdate =datetime .utcnow )

    @staticmethod 
    def hash_password (password :str )->str :
        salt =secrets .token_hex (16 )
        hashed =hashlib .pbkdf2_hmac (
        'sha256',
        password .encode ('utf-8'),
        salt .encode ('utf-8'),
        100000 
        )
        return f"{salt }${hashed .hex ()}"

    def verify_password (self ,password :str )->bool :
        try :
            salt ,hashed =self .password_hash .split ('$')
            hashed_input =hashlib .pbkdf2_hmac (
            'sha256',
            password .encode ('utf-8'),
            salt .encode ('utf-8'),
            100000 
            ).hex ()
            return hashed ==hashed_input 
        except :
            return False 


class PendingUser (Base ):
    __tablename__ ="pending_users"
    id :Mapped [int ]=mapped_column (primary_key =True )
    email :Mapped [str ]=mapped_column (String (256 ),unique =True ,index =True )
    english_name :Mapped [str ]=mapped_column (String (128 ),default ="")
    password_hash :Mapped [str ]=mapped_column (String (256 ))
    department :Mapped [str ]=mapped_column (String (128 ),default ="")
    status :Mapped [str ]=mapped_column (String (32 ),default ="Pending")
    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
    reviewed_at :Mapped [datetime |None ]=mapped_column (nullable =True )
    reviewed_by :Mapped [str |None ]=mapped_column (String (128 ),nullable =True )


class ModulePermission (Base ):
    __tablename__ ="module_permissions"
    id :Mapped [int ]=mapped_column (primary_key =True )
    user_id :Mapped [int ]=mapped_column (index =True )
    module_name :Mapped [str ]=mapped_column (String (64 ),index =True )
    role :Mapped [str ]=mapped_column (String (50 ),default ="User")
    is_active :Mapped [bool ]=mapped_column (default =True )
    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
    updated_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow ,onupdate =datetime .utcnow )


class WebToken (Base ):
    __tablename__ ="web_tokens"
    id :Mapped [int ]=mapped_column (primary_key =True )
    token :Mapped [str ]=mapped_column (String (256 ),unique =True ,index =True )
    user_id :Mapped [int ]=mapped_column (index =True )
    expires_at :Mapped [float ]=mapped_column (Float )
    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
