"""
Health Check API
--------------
This module contains the health check endpoint for the application.
"""

from fastapi import APIRouter

# Create router
router = APIRouter(tags=["Health"])

@router.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "ok", "message": "API is running"} 