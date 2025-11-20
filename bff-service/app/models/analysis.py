import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Enum,
    Integer,
    BigInteger,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


class AnalysisStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(Enum(AnalysisStatus), nullable=False, default=AnalysisStatus.QUEUED)
    route_name = Column(String(250), nullable=True)
    total_files = Column(Integer, nullable=False, default=0)
    total_bytes = Column(BigInteger, nullable=False, default=0)
    processed_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)
    defects_found = Column(Integer, nullable=False, default=0)
    confidence_threshold = Column(Float, nullable=False, default=0.25)
    preview_limit = Column(Integer, nullable=False, default=10)
    message = Column(Text, nullable=True)
    originals_archive_file_id = Column(UUID(as_uuid=True), nullable=True)
    results_archive_file_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    task_metadata = Column(JSON, nullable=True)

    images = relationship(
        "AnalysisImage",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AnalysisImage(Base):
    __tablename__ = "analysis_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("analysis_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    status = Column(Enum(AnalysisStatus), nullable=False, default=AnalysisStatus.QUEUED)
    result_file_id = Column(UUID(as_uuid=True), nullable=True)
    is_preview = Column(Boolean, nullable=False, default=False)
    summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    task = relationship("AnalysisTask", back_populates="images")

