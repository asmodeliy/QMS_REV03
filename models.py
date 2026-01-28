from datetime import date, datetime
from enum import Enum
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import Column, Integer, String, Date, Enum as SAEnum, ForeignKey, Text
import hashlib
import secrets

Base = declarative_base()


class StatusEnum(str, Enum):
    COMPLETE = "Complete"
    IN_PROGRESS = "In-progress"
    NOT_STARTED = "Not Started"
    NA = "N/A"


class RoleEnum(str, Enum):
    ADMIN = "Admin"
    MANAGER = "Manager"
    USER = "User"

    def __str__(self):
        return self.value


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    english_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(256))
    department: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[RoleEnum] = mapped_column(
        SAEnum(RoleEnum, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=RoleEnum.USER
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return f"{salt }${hashed .hex ()}"

    def verify_password(self, password: str) -> bool:
        try:
            salt, hashed = self.password_hash.split("$")
            hashed_input = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
            return hashed == hashed_input
        except:
            return False


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    process: Mapped[str] = mapped_column(String(64), default="")
    metal_option: Mapped[str] = mapped_column(String(128), default="")
    ip_code: Mapped[str] = mapped_column(String(128), default="")
    pdk_ver: Mapped[str] = mapped_column(String(64), default="")
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    cat1: Mapped[str] = mapped_column(String(128), default="")
    cat2: Mapped[str] = mapped_column(String(256), default="")
    dept_from: Mapped[str] = mapped_column(String(64), default="")
    dept_to: Mapped[str] = mapped_column(String(64), default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[StatusEnum] = mapped_column(default=StatusEnum.NOT_STARTED)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    ord: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_path = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    archived: Mapped[bool] = mapped_column(default=False)

    project: Mapped[Project] = relationship(back_populates="tasks")
    files: Mapped[list["TaskFile"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskFile(Base):
    __tablename__ = "task_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    task: Mapped[Task] = relationship(back_populates="files")


class FeedbackTypeEnum(str, Enum):
    BUG = "Bug"
    FEATURE = "Feature"
    QUESTION = "Question"
    OTHER = "Other"


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), default="Other")
    email: Mapped[str] = mapped_column(String(256), default="")
    message: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="New")
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(nullable=True)


class PendingUser(Base):
    __tablename__ = "pending_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    english_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(256))
    department: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="Pending")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


from modules.rpmt.models import PDKDKEntry
