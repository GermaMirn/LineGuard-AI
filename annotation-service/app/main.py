from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import annotations
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Annotation Service",
    description="Image Annotation Service for drawing bboxes on images",
    version=settings.SERVICE_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(annotations.router, prefix="/annotations", tags=["annotations"])


@app.get("/")
async def root():
    return {
        "message": "Annotation Service is running",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}




