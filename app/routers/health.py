import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(status_code=status.HTTP_200_OK, content="It is alive!")
