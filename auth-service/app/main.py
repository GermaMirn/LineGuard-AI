from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, users
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Auth Service",
    description="Authentication and User Management Service",
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

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Auth Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

