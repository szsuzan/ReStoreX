from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from app.models import ScanRequest, ScanProgress, RecoveredFile
from app.services.scan_service import scan_service
from app.services.recovery_service import recovery_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scan/start")
async def start_scan(raw_request: Request):
    """Start a new scan operation"""
    try:
        # Log raw request body for debugging
        body = await raw_request.json()
        logger.info(f"Received raw scan request body: {body}")
        
        # Parse with Pydantic
        request = ScanRequest(**body)
        logger.info(f"Parsed scan request - Drive: {request.driveId}, Type: {request.scanType}, Options: {request.options}")
        
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
        status = scan_service.get_scan_status(scan_id)
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
        await scan_service.cancel_scan(scan_id)
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
        
        results = scan_service.get_scan_results(scan_id)
        
        # Apply filters if provided (simple implementation)
        filtered_results = results
        
        # Cache file metadata for recovery
        for file in filtered_results:
            # Cache complete metadata including fields needed for indexed file recovery
            recovery_service.cache_file_metadata(file.id, {
                'name': file.name,
                'type': file.type,
                'size': file.sizeBytes,
                'path': file.path,
                'offset': file.offset if hasattr(file, 'offset') and file.offset else 0,
                'drive_path': file.drive_path if hasattr(file, 'drive_path') and file.drive_path else (file.drivePath if hasattr(file, 'drivePath') and file.drivePath else ''),
                'sha256': file.sha256 if hasattr(file, 'sha256') and file.sha256 else (file.hash if hasattr(file, 'hash') and file.hash else ''),
                'status': file.status if hasattr(file, 'status') else 'unknown',
                'method': file.method if hasattr(file, 'method') else 'unknown',
                'extension': file.extension if hasattr(file, 'extension') else file.type.lower() if hasattr(file, 'type') else ''
            })
        
        return filtered_results
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan/{scan_id}/report")
async def get_scan_report(scan_id: str):
    """Get the cluster map or health report for diagnostic scans"""
    try:
        import json
        import os
        
        scan_status = scan_service.get_scan_status(scan_id)
        if not scan_status:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        report_data = {}
        
        # Check if this is a cluster scan
        if 'cluster_map' in scan_status and scan_status['cluster_map']:
            cluster_file = scan_status['cluster_map']
            if os.path.exists(cluster_file):
                with open(cluster_file, 'r') as f:
                    cluster_data = json.load(f)
                    report_data['type'] = 'cluster'
                    report_data['data'] = cluster_data
                    logger.info(f"Loaded cluster map with {len(cluster_data.get('cluster_map', []))} clusters")
        
        # Check if this is a health scan
        if 'health_data' in scan_status:
            report_data['type'] = 'health'
            report_data['data'] = scan_status['health_data']
            logger.info(f"Loaded health data with score: {scan_status['health_data'].get('health_score', 0)}")
        
        # If we have a health report file, prefer that
        if 'health_report' in scan_status and scan_status['health_report']:
            health_file = scan_status['health_report']
            if os.path.exists(health_file):
                with open(health_file, 'r') as f:
                    health_data = json.load(f)
                    report_data['type'] = 'health'
                    report_data['data'] = health_data
                    logger.info(f"Loaded health report from file")
        
        if not report_data:
            raise HTTPException(status_code=404, detail="No report data available for this scan")
        
        return report_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
