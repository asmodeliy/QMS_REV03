

from datetime import datetime 
from enum import Enum 
from sqlalchemy .orm import declarative_base ,Mapped ,mapped_column 
from sqlalchemy import String ,Integer ,Text ,DateTime ,Enum as SAEnum ,ForeignKey ,Index 

Base =declarative_base ()


class IssueStatusEnum (str ,Enum ):
    NEW ="NEW"
    IN_PROGRESS ="IN_PROGRESS"
    PENDING_REVIEW ="PENDING_REVIEW"
    RESOLVED ="RESOLVED"

    def __str__ (self ):
        return self .value 


class Shuttle (Base ):
    __tablename__ ="shuttles"

    id :Mapped [int ]=mapped_column (primary_key =True )
    shuttle_id :Mapped [str ]=mapped_column (String (50 ),index =True )
    ip_ic :Mapped [str ]=mapped_column (String (100 ),nullable =True ,index =True )
    node :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    family :Mapped [str ]=mapped_column (String (100 ),nullable =True )

    power_1 :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    power_2 :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    power_3 :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    power_4 :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    power_5 :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    power_6 :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    power_7 :Mapped [str ]=mapped_column (String (50 ),nullable =True )

    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
    updated_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow ,onupdate =datetime .utcnow )

    __table_args__ =(Index ('ix_shuttle_ip','shuttle_id','ip_ic',unique =True ),)


class Issue (Base ):
    __tablename__ ="issues"

    id :Mapped [int ]=mapped_column (primary_key =True )
    tracking_no :Mapped [str ]=mapped_column (String (50 ),unique =True ,index =True )

    shuttle_id :Mapped [str ]=mapped_column (String (50 ))
    node :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    ip_ic :Mapped [str ]=mapped_column (String (100 ),nullable =True )
    family :Mapped [str ]=mapped_column (String (100 ),nullable =True )

    issue_phenomenon :Mapped [str ]=mapped_column (Text ,nullable =True )

    input_v :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    frequency :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    pattern :Mapped [str ]=mapped_column (String (50 ),nullable =True )

    status :Mapped [str ]=mapped_column (SAEnum (IssueStatusEnum ,native_enum =False ),default =IssueStatusEnum .NEW )

    volt :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    temp :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    freq :Mapped [str ]=mapped_column (String (50 ),nullable =True )
    phs :Mapped [str ]=mapped_column (String (50 ),nullable =True )

    report_date :Mapped [datetime ]=mapped_column (DateTime ,nullable =True )
    log_attach :Mapped [str ]=mapped_column (String (500 ),nullable =True )
    # Attachments specifically uploaded for the expected/root-cause field
    expected_root_attach :Mapped [str ]=mapped_column (String (1000), nullable=True)
    expected_root_cause :Mapped [str ]=mapped_column (Text ,nullable =True )
    # Attachments specifically uploaded for the countermeasure field
    countermeasure_attach :Mapped [str ]=mapped_column (String (1000), nullable=True)
    countermeasure :Mapped [str ]=mapped_column (Text ,nullable =True )
    update_note :Mapped [str ]=mapped_column (Text ,nullable =True )
    resolved_note :Mapped [str ]=mapped_column (Text ,nullable =True )
    resolved :Mapped [bool ]=mapped_column (default =False )

    assignee :Mapped [str ]=mapped_column (String (128 ),nullable =True )
    reviewer :Mapped [str ]=mapped_column (String (128 ),nullable =True )
    creator :Mapped [str ]=mapped_column (String (128 ),nullable =True )

    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
    updated_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow ,onupdate =datetime .utcnow )
    resolved_at :Mapped [datetime ]=mapped_column (nullable =True )

    __table_args__ =(
    Index ('ix_issues_shuttle_id','shuttle_id'),
    Index ('ix_issues_status','status'),
    )

