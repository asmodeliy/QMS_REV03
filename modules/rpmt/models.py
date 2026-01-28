from datetime import date ,datetime 
from enum import Enum 
from sqlalchemy .orm import declarative_base ,relationship ,Mapped ,mapped_column 
from sqlalchemy import Column ,Integer ,String ,Date ,Enum as SAEnum ,ForeignKey ,Text 

Base =declarative_base ()


class StatusEnum (str ,Enum ):
    COMPLETE ="Complete"
    IN_PROGRESS ="In-progress"
    NOT_STARTED ="Not Started"
    NA ="N/A"


class Project (Base ):
    __tablename__ ="projects"
    id :Mapped [int ]=mapped_column (Integer ,primary_key =True )
    code :Mapped [str ]=mapped_column (String (128 ),index =True )
    process :Mapped [str ]=mapped_column (String (64 ),default ="")
    metal_option :Mapped [str ]=mapped_column (String (128 ),default ="")
    ip_code :Mapped [str ]=mapped_column (String (128 ),default ="")
    pdk_ver :Mapped [str ]=mapped_column (String (64 ),default ="")
    active :Mapped [bool ]=mapped_column (default =True )
    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )

    tasks :Mapped [list ["Task"]]=relationship (
    back_populates ="project",cascade ="all, delete-orphan"
    )
    pdk_dk_entries :Mapped [list ["PDKDKEntry"]]=relationship (
    back_populates ="project",cascade ="all, delete-orphan"
    )


class Task (Base ):
    __tablename__ ="tasks"
    id :Mapped [int ]=mapped_column (Integer ,primary_key =True )
    project_id :Mapped [int ]=mapped_column (ForeignKey ("projects.id",ondelete ="CASCADE"),index =True )
    cat1 :Mapped [str ]=mapped_column (String (128 ),default ="")
    cat2 :Mapped [str ]=mapped_column (String (256 ),default ="")
    dept_from :Mapped [str ]=mapped_column (String (64 ),default ="")
    dept_to :Mapped [str ]=mapped_column (String (64 ),default ="")
    due_date :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    status :Mapped [StatusEnum ]=mapped_column (default =StatusEnum .NOT_STARTED )
    reason :Mapped [str |None ]=mapped_column (Text ,nullable =True )
    updated_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow ,onupdate =datetime .utcnow )
    ord :Mapped [int |None ]=mapped_column (Integer ,nullable =True )
    file_path =Column (Text ,nullable =True )
    file_name =Column (String (255 ),nullable =True )
    archived :Mapped [bool ]=mapped_column (default =False )

    project :Mapped [Project ]=relationship (back_populates ="tasks")
    files :Mapped [list ["TaskFile"]]=relationship (
    back_populates ="task",cascade ="all, delete-orphan"
    )


class TaskFile (Base ):
    __tablename__ ="task_files"
    id :Mapped [int ]=mapped_column (Integer ,primary_key =True )
    task_id :Mapped [int ]=mapped_column (ForeignKey ("tasks.id",ondelete ="CASCADE"),index =True )
    file_path :Mapped [str ]=mapped_column (Text )
    file_name :Mapped [str ]=mapped_column (String (255 ))
    uploaded_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )

    task :Mapped [Task ]=relationship (back_populates ="files")


class FeedbackTypeEnum (str ,Enum ):
    BUG ="Bug"
    FEATURE ="Feature"
    QUESTION ="Question"
    OTHER ="Other"


class Feedback (Base ):
    __tablename__ ="feedbacks"
    id :Mapped [int ]=mapped_column (Integer ,primary_key =True )
    email :Mapped [str ]=mapped_column (String (256 ),index =True )
    type :Mapped [FeedbackTypeEnum ]=mapped_column (SAEnum (FeedbackTypeEnum ),default =FeedbackTypeEnum .OTHER )
    title :Mapped [str ]=mapped_column (String (256 ),default ="")
    content :Mapped [str ]=mapped_column (Text ,default ="")
    admin_reply :Mapped [str |None ]=mapped_column (Text ,nullable =True )
    status :Mapped [str ]=mapped_column (String (50 ),default ="Pending")
    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
    updated_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow ,onupdate =datetime .utcnow )


class PDKDKEntry (Base ):
    __tablename__ ="pdk_dk_entries"
    id :Mapped [int ]=mapped_column (Integer ,primary_key =True )
    project_id :Mapped [int ]=mapped_column (ForeignKey ("projects.id",ondelete ="CASCADE"),index =True )
    type :Mapped [str |None ]=mapped_column (String (32 ),nullable =True ) 
    category :Mapped [str ]=mapped_column (String (128 ),index =True )
    
    engineer_version_kickoff :Mapped [str |None ]=mapped_column (String (64 ),nullable =True )
    engineer_b2b_date_kickoff :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    engineer_matching_kickoff :Mapped [str |None ]=mapped_column (String (32 ),nullable =True ) 
    engineer_check_date_kickoff :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    
    qa_version_kickoff :Mapped [str |None ]=mapped_column (String (64 ),nullable =True )
    qa_b2b_date_kickoff :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    qa_matching_kickoff :Mapped [str |None ]=mapped_column (String (32 ),nullable =True )
    qa_check_date_kickoff :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    qa_unmatched_reason_kickoff :Mapped [str |None ]=mapped_column (Text ,nullable =True )
    
    engineer_version_tweek :Mapped [str |None ]=mapped_column (String (64 ),nullable =True )
    engineer_b2b_date_tweek :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    engineer_matching_tweek :Mapped [str |None ]=mapped_column (String (32 ),nullable =True )
    engineer_check_date_tweek :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    
    qa_version_tweek :Mapped [str |None ]=mapped_column (String (64 ),nullable =True )
    qa_b2b_date_tweek :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    qa_matching_tweek :Mapped [str |None ]=mapped_column (String (32 ),nullable =True )
    qa_check_date_tweek :Mapped [date |None ]=mapped_column (Date ,nullable =True )
    qa_unmatched_reason_tweek :Mapped [str |None ]=mapped_column (Text ,nullable =True )
    
    created_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow )
    updated_at :Mapped [datetime ]=mapped_column (default =datetime .utcnow ,onupdate =datetime .utcnow )
    
    project :Mapped [Project ]=relationship (back_populates ="pdk_dk_entries")

