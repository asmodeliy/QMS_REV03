from datetime import date ,timedelta 

from fastapi import APIRouter ,Request ,Depends 
from fastapi .responses import HTMLResponse 
from sqlalchemy .orm import Session 
from sqlalchemy import func 

from models import Task ,Project ,StatusEnum 
from core .db import get_db 
from core .i18n import get_locale ,t 

router =APIRouter ()


templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 

@router.get("/reports/risk",response_class =HTMLResponse )
def risk_report (request :Request ,db :Session =Depends (get_db ),weeks :int =4 ):
    from fastapi .responses import RedirectResponse 


    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/main",status_code =303 )

    locale =get_locale (request )

    today =date .today ()
    start_date =today -timedelta (weeks =weeks )

    rows =(
    db .query (Task .dept_to ,Task .status ,Task .due_date )
    .filter (Task .due_date !=None )
    .filter (Task .due_date >=start_date )
    .filter (Task .due_date <=today )
    .all ()
    )

    by_dept :dict [str ,dict ]={}
    total_overdue =0 
    total_tasks =0 

    for r in rows :
        raw =(r .dept_to or "").strip ()
        status =r .status .value if isinstance (r .status ,StatusEnum )else (r .status or "N/A")
        due =r .due_date 

        is_overdue =bool (due and due <today and status !=StatusEnum .COMPLETE .value )

        parts =[p .strip ()for p in raw .split ("/")if p .strip ()]or ["(N/A)"]

        for dept in parts :
            total_tasks +=1 
            if is_overdue :
                total_overdue +=1 

            if dept not in by_dept :
                by_dept [dept ]={"total":0 ,"detail":{}}
            by_dept [dept ]["total"]+=1 

            by_dept [dept ]["detail"][status ]=by_dept [dept ]["detail"].get (status ,0 )+1 
            if is_overdue :
                by_dept [dept ]["detail"]["__OVERDUE__"]=by_dept [dept ]["detail"].get ("__OVERDUE__",0 )+1 

    sorted_dept =sorted (
    by_dept .items (),
    key =lambda kv :kv [1 ]["detail"].get ("__OVERDUE__",0 ),
    reverse =True ,
    )

    ctx ={
    "request":request ,
    "locale":locale ,
    "weeks":weeks ,
    "start_date":start_date ,
    "end_date":today ,
    "total_tasks":total_tasks ,
    "total_overdue":total_overdue ,
    "by_dept":sorted_dept ,
    }
    return templates .TemplateResponse ("modules/rpmt/report_risk.html",ctx )
