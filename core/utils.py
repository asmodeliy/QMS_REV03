
from typing import List ,Tuple ,Dict ,Optional 
from fastapi import Request 
from models import Task 

def build_groups_keep_order (tasks :List [Task ])->List [Tuple [str ,List [Task ]]]:
    base_sorted =sorted (tasks ,key =lambda t :((t .ord or 10 **9 ),t .id ))
    groups :List [Tuple [str ,List [Task ]]]=[]
    index :Dict [str ,int ]={}

    for t in base_sorted :
        k =t .cat1 or ""
        if k not in index :
            index [k ]=len (groups )
            groups .append ((k ,[]))
        groups [index [k ]][1 ].append (t )

    return groups 


def get_client_ip (request :Request )->str :
    if forwarded :=request .headers .get ("x-forwarded-for"):
        return forwarded .split (",")[0 ].strip ()
    if remote_addr :=request .client :
        return remote_addr .host 
    return "unknown"


def get_current_user_email (request :Request )->Optional [str ]:
    if hasattr(request, "session") and request.session:
        return request.session.get("user_email")
    return None


def get_user_info (request :Request )->Dict [str ,Optional [str ]]:
    return {
        "email": get_current_user_email(request),
        "ip": get_client_ip(request)
    }


def get_visit_token (request :Request )->Optional [str ]:
    return request .session .get ("admin_visit")


def build_redirect_url (url :str ,request :Request )->str :
    v =get_visit_token (request )
    if not v :
        return url 
    sep ="&"if ("?"in url )else "?"
    return f"{url }{sep }v={v }"