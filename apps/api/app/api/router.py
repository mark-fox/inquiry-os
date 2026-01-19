from fastapi import APIRouter

from app.api.v1.endpoints import research_runs

api_router = APIRouter()

# Versioned API routes
api_router.include_router(research_runs.router, prefix="/v1")

# System / utility routes (unversioned)
@api_router.get("/ping", tags=["system"])
async def ping():
    """
    Basic ping endpoint; useful as a quick sanity check.
    """
    return {"message": "pong"}
