from fastapi import APIRouter, HTTPException
from typing import List
from app.models import RecoveryRequest, RecoveryProgress
from app.services.recovery_service import recovery_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/recovery/start")
async def start_recovery(request: RecoveryRequest):
    """Start a new recovery operation"""
    try:
        if not request.fileIds:
            raise HTTPException(status_code=400, detail="No files selected for recovery")
        
        recovery_id = await recovery_service.start_recovery(
            request.fileIds,
            request.outputPath,
            request.options or {}
        )
        
        return {
            "recoveryId": recovery_id,
            "message": f"Recovery started for {len(request.fileIds)} files",
            "totalFiles": len(request.fileIds)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting recovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recovery/{recovery_id}/status")
async def get_recovery_status(recovery_id: str):
    """Get the status of a running or completed recovery"""
    try:
        status = await recovery_service.get_recovery_status(recovery_id)
        if not status:
            raise HTTPException(status_code=404, detail="Recovery not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recovery status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recovery/{recovery_id}/cancel")
async def cancel_recovery(recovery_id: str):
    """Cancel a running recovery operation"""
    try:
        success = await recovery_service.cancel_recovery(recovery_id)
        if not success:
            raise HTTPException(status_code=404, detail="Recovery not found")
        return {"message": "Recovery cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling recovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recovery/{recovery_id}/logs")
async def get_recovery_logs(recovery_id: str):
    """Get the logs for a recovery operation"""
    try:
        logs = await recovery_service.get_recovery_logs(recovery_id)
        return {
            "recoveryId": recovery_id,
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Error getting recovery logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
