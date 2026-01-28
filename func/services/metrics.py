
from sqlalchemy .orm import Session 
from sqlalchemy import func ,Integer 
from models import Task ,StatusEnum 
from datetime import date 
from core .cache import cache_result 


@cache_result (seconds =300 )
def get_project_metrics (db :Session ,project_id :int ):

    row =(
    db .query (
    func .count (Task .id ).label ("total"),
    func .sum (
    (Task .status ==StatusEnum .COMPLETE ).cast (Integer )
    ).label ("completed"),
    func .sum (
    (
    (Task .due_date !=None )
    &(Task .due_date <date .today ())
    &(Task .status !=StatusEnum .COMPLETE )
    ).cast (Integer )
    ).label ("overdue"),
    )
    .filter (Task .project_id ==project_id )
    .one ()
    )

    total =row .total or 0 
    completed =row .completed or 0 
    overdue =row .overdue or 0 

    if total ==0 :
        return {
        "total":0 ,
        "completed":0 ,
        "completion_rate":0.0 ,
        "overdue_count":0 ,
        "on_track":0 ,
        "health":"⚪",
        }

    completion_rate =round (completed /total *100 ,1 )
    on_track =max (total -completed -overdue ,0 )

    return {
    "total":total ,
    "completed":completed ,
    "completion_rate":completion_rate ,
    "overdue_count":overdue ,
    "on_track":on_track ,
    "health":"🟢"if overdue ==0 else "🔴"if overdue >2 else "🟡",
    }

def get_all_project_metrics (db :Session )->dict [int ,dict ]:
    rows =(
    db .query (
    Task .project_id .label ("project_id"),
    func .count (Task .id ).label ("total"),
    func .sum (
    (Task .status ==StatusEnum .COMPLETE ).cast (Integer )
    ).label ("completed"),
    func .sum (
    (
    (Task .due_date !=None )
    &(Task .due_date <date .today ())
    &(Task .status !=StatusEnum .COMPLETE )
    ).cast (Integer )
    ).label ("overdue"),
    )
    .group_by (Task .project_id )
    .all ()
    )

    metrics_by_project :dict [int ,dict ]={}

    for r in rows :
        total =r .total or 0 
        completed =r .completed or 0 
        overdue =r .overdue or 0 

        if total ==0 :
            metrics_by_project [r .project_id ]={
            "total":0 ,
            "completed":0 ,
            "completion_rate":0.0 ,
            "overdue_count":0 ,
            "on_track":0 ,
            "health":"⚪",
            }
            continue 

        completion_rate =round (completed /total *100 ,1 )
        on_track =max (total -completed -overdue ,0 )

        metrics_by_project [r .project_id ]={
        "total":total ,
        "completed":completed ,
        "completion_rate":completion_rate ,
        "overdue_count":overdue ,
        "on_track":on_track ,
        "health":"🟢"if overdue ==0 else "🔴"if overdue >2 else "🟡",
        }

    return metrics_by_project 