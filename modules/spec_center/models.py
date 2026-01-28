from datetime import datetime
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index, Boolean

Base = declarative_base()


class SpecCategory(Base):
    """Hierarchical category for specifications"""
    __tablename__ = "spec_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey('spec_categories.id'), nullable=True, index=True)
    icon: Mapped[str] = mapped_column(String(64), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    children: Mapped[list["SpecCategory"]] = relationship(
        "SpecCategory",
        remote_side=[id],
        cascade="all, delete-orphan",
        single_parent=True
    )
    parent: Mapped["SpecCategory"] = relationship(
        "SpecCategory",
        remote_side=[parent_id],
        foreign_keys=[parent_id],
        uselist=False,
        overlaps="children"
    )
    
    files: Mapped[list["SpecFile"]] = relationship(
        "SpecFile",
        back_populates="category",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_spec_categories_parent_id', 'parent_id'),
        Index('ix_spec_categories_is_active', 'is_active'),
    )


class SpecFile(Base):
    """File within a specification category"""
    __tablename__ = "spec_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('spec_categories.id'), index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_type: Mapped[str] = mapped_column(String(32), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(128), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped[SpecCategory] = relationship(
        "SpecCategory",
        back_populates="files"
    )

    __table_args__ = (
        Index('ix_spec_files_category_id', 'category_id'),
        Index('ix_spec_files_is_active', 'is_active'),
    )

