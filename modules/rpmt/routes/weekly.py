from datetime import date ,timedelta 
import datetime as dt 
from typing import Dict ,List ,Tuple 

from fastapi import APIRouter ,Request ,Depends ,Query 
from fastapi .responses import HTMLResponse 
from sqlalchemy import select 
from sqlalchemy .orm import Session 

from core .db import get_db 
from core .config import BASE_DIR 
from models import Task ,Project ,StatusEnum 
from core .i18n import get_locale ,t 

router =APIRouter ()

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 
    templates .env .globals .update (
    datetime =dt ,
    timedelta =dt .timedelta ,
    enumerate =enumerate ,
    len =len ,
    )

def monday_of (d :date )->date :
    return d -timedelta (days =d .weekday ())

def week_key (d :date )->Tuple [int ,int ]:
    iso =d .isocalendar ()
    return (iso [0 ],iso [1 ])

def daterange_weeks (start_monday :date ,weeks :int )->List [Tuple [int ,int ,date ,date ]]:

    out :List [Tuple [int ,int ,date ,date ]]=[]
    s =start_monday 
    for _ in range (weeks ):
        e =s +timedelta (days =7 )
        y ,w =week_key (s )
        out .append ((y ,w ,s ,e ))
        s =e 
    return out 

def pick_variant (pid :int )->int :
    return ((pid %8 )or 8 )

@router.get("/weekly",response_class =HTMLResponse )
def weekly (
request :Request ,
weeks :int =Query (6 ,ge =1 ,le =12 ,description ="표시할 주 수"),
start :str |None =Query (None ,description ="YYYY-MM-DD (기준일, 해당 주의 월요일로 정렬)"),
db :Session =Depends (get_db ),
):
    from fastapi .responses import RedirectResponse 

    if not request .session .get ("is_authenticated"):
        return RedirectResponse (url ="/main",status_code =303 )

    locale =get_locale (request )
    if start :
        try :
            start_monday =monday_of (date .fromisoformat (start ))
        except Exception :
            start_monday =monday_of (dt .date .today ())
    else :
        start_monday =monday_of (dt .date .today ())

    week_rows =daterange_weeks (start_monday ,weeks )
    start_date =week_rows [0 ][2 ]
    end_date =week_rows [-1 ][3 ]

    q =(
    select (Task ,Project )
    .join (Project ,Project .id ==Task .project_id )
    .where (Task .due_date !=None )
    .where (Task .due_date >=start_date ,Task .due_date <end_date )
    .order_by (Project .id .asc (),Task .due_date .asc (),Task .id .asc ())
    )
    rows =db .execute (q ).all ()

    proj_order :List [Project ]=[]
    seen_pid :set [int ]=set ()
    for t ,p in rows :
        if p .id not in seen_pid :
            proj_order .append (p )
            seen_pid .add (p .id )

    pivot :Dict [Tuple [int ,int ],Dict [int ,List [Task ]]]={}
    for t ,p in rows :
        y ,w =week_key (t .due_date )
        pivot .setdefault ((y ,w ),{}).setdefault (p .id ,[]).append (t )

    variants ={p .id :pick_variant (p .id )for p in proj_order }

    return templates .TemplateResponse (
    "modules/rpmt/weekly.html",
    {
    "request":request ,
    "week_rows":week_rows ,
    "projects":proj_order ,
    "pivot":pivot ,
    "variants":variants ,
    "StatusEnum":StatusEnum ,
    "start_monday":start_monday ,
    "weeks":weeks ,
    "timedelta":timedelta ,
    "locale":locale ,
    },
    )
