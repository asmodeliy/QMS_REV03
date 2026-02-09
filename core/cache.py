
from datetime import datetime ,timedelta 
from sqlalchemy .orm import Session 


class CachedValue :
    def __init__ (self ,value ,expires_at ):
        self .value =value 
        self .expires_at =expires_at 

    def is_expired (self ):
        return datetime .now ()>self .expires_at 


cache_store ={}


def cache_result (seconds :int =300 ):
    def decorator (func ):
        def wrapper (*args ,**kwargs ):
            key_args =[]
            for arg in args :
                if isinstance (arg ,Session ):
                    continue 
                key_args .append (arg )

            cache_key =f"{func .__name__ }:{tuple (key_args )}:{tuple (sorted (kwargs .items ()))}"

            if cache_key in cache_store and not cache_store [cache_key ].is_expired ():
                return cache_store [cache_key ].value 

            result =func (*args ,**kwargs )
            cache_store [cache_key ]=CachedValue (
            result ,datetime .now ()+timedelta (seconds =seconds )
            )
            return result 

        return wrapper 

    return decorator 