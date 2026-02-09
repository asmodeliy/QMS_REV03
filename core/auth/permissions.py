
from typing import Optional ,Tuple 
from fastapi import Request ,HTTPException 
from sqlalchemy import select 
from sqlalchemy .orm import Session 
from core .auth .models import ModulePermission ,User 
from core .auth .db import get_auth_db_sync 


def get_module_role (user_id :int ,module_name :str ,db :Session )->Optional [str ]:
    perm =db .execute (
    select (ModulePermission ).where (
    (ModulePermission .user_id ==user_id )&
    (ModulePermission .module_name ==module_name )&
    (ModulePermission .is_active ==True )
    )
    ).scalars ().first ()

    return perm .role if perm else None 


def check_module_access (request :Request ,module_name :str )->Tuple [bool ,Optional [str ]]:

    if not request .session .get ("is_authenticated"):
        return False ,None 

    user_id =request .session .get ("user_id")
    if not user_id :
        return False ,None 

    db =get_auth_db_sync ()
    try :
        role =get_module_role (user_id ,module_name ,db )
        return role is not None ,role 
    finally :
        db .close ()


def require_module_access (module_name :str ):
    def decorator (func ):
        async def wrapper (request :Request ,*args ,**kwargs ):
            can_access ,role =check_module_access (request ,module_name )
            if not can_access :
                raise HTTPException (status_code =403 ,detail =f"No access to {module_name }")

            request .state .module_role =role 
            return await func (request ,*args ,**kwargs )
        return wrapper 
    return decorator 


def require_module_role (module_name :str ,required_role :str ):
    def decorator (func ):
        async def wrapper (request :Request ,*args ,**kwargs ):
            can_access ,role =check_module_access (request ,module_name )
            if not can_access or role !=required_role :
                raise HTTPException (
                status_code =403 ,
                detail =f"Requires {required_role } role in {module_name }"
                )
            request .state .module_role =role 
            return await func (request ,*args ,**kwargs )
        return wrapper 
    return decorator 
