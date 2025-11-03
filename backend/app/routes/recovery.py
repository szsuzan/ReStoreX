from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
from app.models import RecoveryRequest, RecoveryProgress
from app.services.recovery_service import recovery_service
from app.services.python_recovery_service import PythonRecoveryService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SelectiveRecoveryRequest(BaseModel):
    """Request model for selective file recovery from scan index"""
    files: List[Dict]  # List of file info dicts from scan results
    outputPath: str
    validateHashes: Optional[bool] = True  # Validate files with stored hashes
    createSubdirectories: Optional[bool] = True  # Create subdirectories by file type


class SelectiveRecoveryResponse(BaseModel):
    """Response model for selective recovery"""
    success: bool
    recovered_count: int
    failed_count: int
    total_size: int
    message: str
    results: List[Dict]


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


@router.post("/recover-selected")
async def recover_selected_files(request: SelectiveRecoveryRequest):
    """
    Recover specific files from scan index (File Scavenger-style)
    
    This endpoint:
    1. Takes a list of indexed files from scan results
    2. Reads file data from drive using stored offsets
    3. Validates with stored hashes
    4. Writes only selected files to output directory
    
    Example request:
    {
        "files": [
            {
                "name": "f00012345.jpg",
                "offset": 12345678,
                "size": 2048576,
                "sha256": "e3b0c44...",
                "drive_path": "E:"
            }
        ],
        "outputPath": "C:\\RecoveredFiles",
        "validateHashes": true
    }
    """
    try:
        logger.info(f"📥 Received selective recovery request for {len(request.files)} files")
        logger.info(f"📂 Output directory: {request.outputPath}")
        
        # Validate request
        if not request.files:
            raise HTTPException(status_code=400, detail="No files provided for recovery")
        
        if not request.outputPath:
            raise HTTPException(status_code=400, detail="Output path is required")
        
        # Import WebSocket manager for progress updates
        from app.services.websocket_manager import websocket_manager
        import uuid
        
        # Generate recovery ID for tracking
        recovery_id = str(uuid.uuid4())
        
        # Define progress callback for WebSocket updates
        async def progress_callback(progress_data: dict):
            """Send real-time progress updates via WebSocket"""
            await websocket_manager.broadcast({
                "type": "recovery_progress",
                "data": {
                    "recoveryId": recovery_id,
                    "isRecovering": progress_data.get('progress', 0) < 100,
                    "progress": progress_data.get('progress', 0),
                    "currentFile": f"File {progress_data.get('current_file', 1)} of {progress_data.get('total_files', len(request.files))}",
                    "filesRecovered": progress_data.get('recovered', 0),
                    "totalFiles": progress_data.get('total_files', len(request.files)),
                    "estimatedTimeRemaining": "Calculating...",
                    "status": "running" if progress_data.get('progress', 0) < 100 else "completed"
                }
            })
        
        # Create recovery service instance
        recovery_service_instance = PythonRecoveryService()
        
        # Perform selective recovery with progress callback
        result = await recovery_service_instance.recover_selected_files(
            file_list=request.files,
            output_dir=request.outputPath,
            progress_callback=progress_callback,
            create_subdirectories=request.createSubdirectories
        )
        
        # Send final completion message via WebSocket
        await websocket_manager.broadcast({
            "type": "recovery_progress",
            "data": {
                "recoveryId": recovery_id,
                "isRecovering": False,
                "progress": 100.0,
                "currentFile": "",
                "filesRecovered": result['recovered_count'],
                "totalFiles": len(request.files),
                "estimatedTimeRemaining": "0s",
                "status": "completed"
            }
        })
        
        # Build response
        success = result['recovered_count'] > 0
        message = f"Recovered {result['recovered_count']} of {len(request.files)} files"
        
        if result['failed_count'] > 0:
            message += f" ({result['failed_count']} failed)"
        
        logger.info(f"✅ Selective recovery complete: {message}")
        
        return {
            "success": success,
            "recovered_count": result['recovered_count'],
            "failed_count": result['failed_count'],
            "total_size": result['total_size'],
            "message": message,
            "results": result['results'],
            "recoveryId": recovery_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in selective recovery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")
