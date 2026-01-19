from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.router import api_router

settings = get_settings()

app = FastAPI(
    title=settings.api_name,
    version=settings.api_version,
)

# CORS: allow local frontend dev (Vite default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router under /api
app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["system"])
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    return {"status": "ok", "version": settings.api_version}
