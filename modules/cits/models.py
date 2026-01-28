from datetime import datetime
from enum import Enum
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum, Index, ForeignKey

Base = declarative_base()


class IssueStatusEnum(str, Enum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    CLOSE = "CLOSE"

    def __str__(self):
        return self.value


class IssueTagEnum(str, Enum):
    TECHNICAL_SUPPORT = "Technical Support"
    CUSTOMER_CLAIM = "Customer Claim"

    def __str__(self):
        return self.value


class ConversationTypeEnum(str, Enum):
    INQUIRY = "Inquiry"
    REPLY = "Reply"

    def __str__(self):
        return self.value


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class IP(Base):
    __tablename__ = "ips"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class ContactPerson(Base):
    __tablename__ = "contact_persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    position: Mapped[str] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomerIssue(Base):
    __tablename__ = "customer_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(SAEnum(IssueStatusEnum, native_enum=False), default=IssueStatusEnum.OPEN)
    tag: Mapped[str] = mapped_column(SAEnum(IssueTagEnum, native_enum=False), nullable=True)
    customer: Mapped[str] = mapped_column(String(255), nullable=True)
    ip_ic: Mapped[str] = mapped_column(String(128), nullable=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=True)
    reporter: Mapped[str] = mapped_column(String(128), nullable=True)
    assignee: Mapped[str] = mapped_column(String(128), nullable=True)
    attachments: Mapped[str] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_customer_issues_status', 'status'),
    )


class IssueConversation(Base):
    __tablename__ = "issue_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey('customer_issues.id', ondelete='CASCADE'), index=True)
    inquiry_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    type: Mapped[str] = mapped_column(SAEnum(ConversationTypeEnum, native_enum=False))
    content: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index('ix_conversations_issue_id', 'issue_id'),
    )

