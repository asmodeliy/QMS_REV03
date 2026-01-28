from fastapi import APIRouter ,Request 
from fastapi .responses import HTMLResponse ,JSONResponse 
from core .config import BASE_DIR ,OUTLOOK_EMAIL ,OUTLOOK_PASSWORD ,ADMIN_NOTIFICATION_EMAIL 
from pathlib import Path 
from datetime import datetime 
import time 
import json 
import smtplib 
from email .mime .text import MIMEText 
from email .mime .multipart import MIMEMultipart 
from core .i18n import get_locale 

router =APIRouter ()

templates =None 

def set_templates (tmpl ):
    global templates 
    templates =tmpl 

FEEDBACK_DIR =BASE_DIR /"data"
FEEDBACK_DIR .mkdir (parents =True ,exist_ok =True )
FEEDBACK_FILE =FEEDBACK_DIR /"feedback.json"

def load_feedbacks ():
    if not FEEDBACK_FILE .exists ():
        return []
    try :
        return json .loads (FEEDBACK_FILE .read_text (encoding ="utf-8"))
    except :
        return []

def save_feedbacks (feedbacks ):
    FEEDBACK_FILE .write_text (json .dumps (feedbacks ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")

def send_admin_notification (feedback ):
    if not OUTLOOK_EMAIL or not OUTLOOK_PASSWORD :
        return 

    try :
        msg =MIMEMultipart ()
        msg ['From']=OUTLOOK_EMAIL 
        msg ['To']=ADMIN_NOTIFICATION_EMAIL 
        msg ['Subject']=f"[RPMT] 새 피드백: {feedback .get ('type','Other')}"

        body =f"새로운 피드백이 도착했습니다.\n\n유형: {feedback .get ('type','Other')}\n발신자: {feedback .get ('email')or '(익명)'}\n내용: {feedback .get ('message','')}\nURL: {feedback .get ('url')or '(없음)'}\n시간: {feedback .get ('timestamp','')}\n\n확인하기: http://localhost:8000/admin/feedback"

        msg .attach (MIMEText (body ,'plain','utf-8'))

        with smtplib .SMTP ('smtp.office365.com',587 )as server :
            server .starttls ()
            server .login (OUTLOOK_EMAIL ,OUTLOOK_PASSWORD )
            server .send_message (msg )
    except Exception as e :
        pass 

def send_reply_email (feedback_id ,reply_message ):
    feedbacks =load_feedbacks ()
    feedback =next ((f for f in feedbacks if f .get ('id')==feedback_id ),None )

    if not feedback or not feedback .get ('email'):
        return 

    if not OUTLOOK_EMAIL or not OUTLOOK_PASSWORD :
        return 

    try :
        msg =MIMEMultipart ()
        msg ['From']=OUTLOOK_EMAIL 
        msg ['To']=feedback ['email']
        msg ['Subject']='[RPMT] 피드백 답변'

        body =f"안녕하세요,\n\n보내주신 피드백에 대한 답변입니다:\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n원본 메시지:\n{feedback .get ('message','')}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n답변:\n{reply_message }\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n감사합니다.\nRAMSCHIP RPMT 팀"

        msg .attach (MIMEText (body ,'plain','utf-8'))

        with smtplib .SMTP ('smtp.office365.com',587 )as server :
            server .starttls ()
            server .login (OUTLOOK_EMAIL ,OUTLOOK_PASSWORD )
            server .send_message (msg )
    except Exception as e :
        pass 

@router .get ("/help",response_class =HTMLResponse )
def help_page (request :Request ):
    locale =get_locale (request )
    return templates .TemplateResponse ("shared/help.html",{"request":request ,"locale":locale })

@router .post ("/help/feedback")
def submit_feedback (request :Request ):
    try :
        feedbacks =load_feedbacks ()
        feedback ={
        "id":int (time .time ()*1000 ),
        "type":request .form .get ("type","Bug"),
        "email":request .form .get ("email",""),
        "message":request .form .get ("message",""),
        "url":request .url .path ,
        "timestamp":datetime .now ().isoformat (),
        "status":"Unread"
        }
        feedbacks .append (feedback )
        save_feedbacks (feedbacks )
        send_admin_notification (feedback )
        return JSONResponse ({"success":True })
    except Exception as e :
        return JSONResponse ({"success":False ,"error":str (e )},status_code =500 )

@router .get ("/help/feedback")
def get_feedbacks (request :Request ):
    feedbacks =load_feedbacks ()
    return feedbacks 

@router .post ("/help/feedback/{feedback_id}/reply")
def reply_feedback (feedback_id :int ,request :Request ):
    try :
        reply_message =request .form .get ("reply_message","")
        feedbacks =load_feedbacks ()
        feedback =next ((f for f in feedbacks if f .get ('id')==feedback_id ),None )

        if feedback :
            feedback ['status']='Resolved'
            save_feedbacks (feedbacks )
            send_reply_email (feedback_id ,reply_message )

        return JSONResponse ({"success":True })
    except Exception as e :
        return JSONResponse ({"success":False },status_code =500 )
