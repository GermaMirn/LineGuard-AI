from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import files
from app.database import engine, Base
from app.core.config import get_settings
from pathlib import Path

settings = get_settings()

# Создать директорию для хранилища
storage_path = Path(settings.STORAGE_PATH)
storage_path.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Files Service",
    description="File Storage and Management Service",
    version="1.0.0",
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

app.include_router(files.router, prefix="/files", tags=["files"])

@app.get("/")
async def root():
    return {"message": "Files Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

