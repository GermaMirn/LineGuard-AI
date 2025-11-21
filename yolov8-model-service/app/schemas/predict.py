from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class BboxSize(BaseModel):
    width: int
    height: int
    area: int
    is_small: bool

class DefectFeatures(BaseModel):
    type: str
    severity: str
    description: str
    confidence_level: str

class DefectSummary(BaseModel):
    type: str
    severity: str
    description: str

class Detection(BaseModel):
    class_name: str = Field(..., alias="class")
    class_ru: str
    confidence: float
    bbox: List[int]
    bbox_size: BboxSize
    defect_summary: DefectSummary
    defect_features: Optional[DefectFeatures] = None

    class Config:
        populate_by_name = True
        from_attributes = True

class PredictResponse(BaseModel):
    detections: List[Detection]
    statistics: Dict[str, int]
    total_objects: int
    defects_count: int
    has_defects: bool

class ModelInfoResponse(BaseModel):
    model_path: str
    model_exists: bool
    classes: List[str]
    num_classes: int
    metrics: Dict[str, Any]
    requirements_met: Dict[str, Any]
    supported_formats: List[str]
    max_resolution: str

    model_config = {
        'protected_namespaces': ()
    }

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    service: str
    error: Optional[str] = None

    model_config = {
        'protected_namespaces': ()
    }

class BatchPredictResponse(BaseModel):
    """Response for batch prediction"""
    results: List[PredictResponse]
    total: int
    failed: int = 0
    errors: Optional[List[Dict[str, Any]]] = None

