from fastapi import APIRouter, HTTPException
from typing import List
from app.models import DriveInfo
from app.services.drive_service import drive_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/drives", response_model=List[DriveInfo])
async def get_drives():
    """Get all available drives"""
    try:
        drives = await drive_service.get_all_drives()
        return drives
    except Exception as e:
        logger.error(f"Error getting drives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drives/{drive_id}", response_model=DriveInfo)
async def get_drive(drive_id: str):
    """Get information about a specific drive"""
    try:
        drive = await drive_service.get_drive(drive_id)
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        return drive
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting drive {drive_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drives/{drive_id}/validate")
async def validate_drive(drive_id: str):
    """Validate if a drive is ready for scanning"""
    try:
        result = await drive_service.validate_drive(drive_id)
        if not result["valid"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating drive {drive_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
