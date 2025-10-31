from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models import ScanRequest, ScanProgress, RecoveredFile
from app.services.scan_service import scan_service
from app.services.recovery_service import recovery_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scan/start")
async def start_scan(request: ScanRequest):
    """Start a new scan operation"""
    try:
        scan_id = await scan_service.start_scan(
            request.driveId,
            request.scanType,
            request.options.dict() if request.options else {}
        )
        
        return {
            "scanId": scan_id,
            "message": f"Scan started successfully",
            "scanType": request.scanType
        }
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan/{scan_id}/status")
async def get_scan_status(scan_id: str):
    """Get the status of a running or completed scan"""
    try:
        status = await scan_service.get_scan_status(scan_id)
        if not status:
            raise HTTPException(status_code=404, detail="Scan not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/{scan_id}/cancel")
async def cancel_scan(scan_id: str):
    """Cancel a running scan"""
    try:
        success = await scan_service.cancel_scan(scan_id)
        if not success:
            raise HTTPException(status_code=404, detail="Scan not found")
        return {"message": "Scan cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan/{scan_id}/results", response_model=List[RecoveredFile])
async def get_scan_results(
    scan_id: str,
    fileType: Optional[str] = Query(None),
    recoveryChances: Optional[str] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: Optional[str] = Query("asc"),
    searchQuery: Optional[str] = Query(None)
):
    """Get the results of a completed scan with optional filters"""
    try:
        filters = {}
        if fileType:
            filters["fileType"] = fileType
        if recoveryChances:
            filters["recoveryChances"] = recoveryChances.split(",")
        if sortBy:
            filters["sortBy"] = sortBy
        if sortOrder:
            filters["sortOrder"] = sortOrder
        if searchQuery:
            filters["searchQuery"] = searchQuery
        
        results = await scan_service.get_scan_results(scan_id, filters)
        
        # Cache file metadata for recovery
        for file in results:
            recovery_service.cache_file_metadata(file.id, {
                'name': file.name,
                'type': file.type,
                'size': file.sizeBytes,
                'path': file.path
            })
        
        return results
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        raise HTTPException(status_code=500, detail=str(e))
