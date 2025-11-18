from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base

class FileType(str, enum.Enum):
    JSON_SCHEMA = "JSON_SCHEMA"
    XSD_SCHEMA = "XSD_SCHEMA"
    TEST_DATA = "TEST_DATA"
    VM_TEMPLATE = "VM_TEMPLATE"
    IMAGE = "IMAGE"

class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

