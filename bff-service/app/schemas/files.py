from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class FileType(str, Enum):
    JSON_SCHEMA = "JSON_SCHEMA"
    XSD_SCHEMA = "XSD_SCHEMA"
    TEST_DATA = "TEST_DATA"
    VM_TEMPLATE = "VM_TEMPLATE"
    IMAGE = "IMAGE"  # Для изображений детекции

class FileUploadResponse(BaseModel):
    id: str
    project_id: str
    file_name: str
    file_type: str
    file_path: str
    file_size: int
    mime_type: str
    checksum: str
    uploaded_by: Optional[str] = None
    created_at: datetime

class FileResponse(BaseModel):
    id: str
    project_id: str
    file_name: str
    file_type: str
    file_size: int
    mime_type: str
    checksum: str
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class FileListResponse(BaseModel):
    files: list[FileResponse]
    total: int

