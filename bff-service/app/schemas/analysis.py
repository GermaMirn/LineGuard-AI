from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.analysis import AnalysisStatus


class AnalysisTaskCreateResponse(BaseModel):
    task_id: UUID = Field(..., description="Идентификатор задачи анализа")
    status: AnalysisStatus


class AnalysisImageSummary(BaseModel):
    id: UUID
    file_id: UUID
    file_name: str
    file_size: int
    status: AnalysisStatus
    is_preview: bool
    summary: Optional[dict] = None
    result_file_id: Optional[UUID] = None
    error_message: Optional[str] = None


class AnalysisTaskResponse(BaseModel):
    id: UUID
    status: AnalysisStatus
    route_name: Optional[str] = None
    total_files: int
    total_bytes: int
    processed_files: int
    failed_files: int
    defects_found: int
    confidence_threshold: float
    preview_limit: int
    message: Optional[str]
    originals_archive_file_id: Optional[UUID]
    results_archive_file_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    metadata: Optional[dict] = None
    preview_files: List[AnalysisImageSummary] = Field(default_factory=list)


class AnalysisTaskListItem(BaseModel):
    id: UUID
    status: AnalysisStatus
    route_name: Optional[str] = None
    total_files: int
    processed_files: int
    defects_found: int
    created_at: datetime
    completed_at: Optional[datetime]


class AnalysisTaskProgress(BaseModel):
    task_id: UUID
    status: AnalysisStatus
    processed_files: int
    total_files: int
    failed_files: int = 0
    defects_found: int = 0
    message: Optional[str] = None

