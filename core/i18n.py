from fastapi import Request 
from pathlib import Path 
import yaml 

LOCALE_DIR =Path (__file__ ).parent .parent /"locales"
TRANSLATIONS ={}

def load_translations ():
    global TRANSLATIONS 
    for lang_file in LOCALE_DIR .glob ("*.yml"):
        lang =lang_file .stem 
        try :
            with open (lang_file ,'r',encoding ='utf-8')as f :
                TRANSLATIONS [lang ]=yaml .safe_load (f )or {}
            print (f"[OK] Loaded {lang }.yml with {len (TRANSLATIONS [lang ])} keys")
        except Exception as e :
            print (f"[ERROR] Failed to load {lang }.yml: {e }")

load_translations ()

def get_locale (request :Request )->str :
    lang =request .cookies .get ("lang")
    if lang in TRANSLATIONS :
        return lang 

    accept_lang =request .headers .get ("accept-language","").split (",")[0 ].split ("-")[0 ]
    if accept_lang in TRANSLATIONS :
        return accept_lang 

    return "en"

def t (key :str ,locale :str ="en",**kwargs )->str :
    if locale not in TRANSLATIONS :
        locale ="en"

    keys =key .split (".")
    value =TRANSLATIONS [locale ]

    for k in keys :
        if isinstance (value ,dict ):
            value =value .get (k )
        else :
            return ""

    if value is None :
        return ""

    if isinstance (value ,str )and kwargs :
        try :
            return value .format (**kwargs )
        except (KeyError ,ValueError ):
            return value 

    return str (value )if value else ""

def get_all_translations (locale :str ="en")->dict :
    return TRANSLATIONS .get (locale ,{})