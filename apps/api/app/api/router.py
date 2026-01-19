from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/ping", tags=["system"])
async def ping():
    """
    Basic ping endpoint; useful as a quick sanity check.
    """
    return {"message": "pong"}
