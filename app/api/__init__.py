"""
API Router
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def status():
    return {"status": "operational", "api_version": "v1"}
