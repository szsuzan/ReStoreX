"""
Simplified scan service using only Python-based file recovery
No external dependencies on TestDisk/PhotoRec
"""
import asyncio
import uuid
import time
import logging
from typing import Dict, Optional, List
from datetime import datetime
import os
import hashlib
from fastapi import HTTPException

from app.models import ScanProgress, RecoveredFile
from app.services.python_recovery_service import PythonRecoveryService
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class ScanService:
    def __init__(self):
        self.active_scans: Dict[str, Dict] = {}
        self.scan_results: Dict[str, List[RecoveredFile]] = {}
        
        # Initialize Python recovery service
        from app.config import settings
        self.recovery_service = PythonRecoveryService(settings.TEMP_DIR)

    async def start_scan(self, drive_id: str, scan_type: str, options: dict) -> str:
        """Start a new scan operation"""
        scan_id = str(uuid.uuid4())
        
        scan_info = {
            "scan_id": scan_id,
            "drive_id": drive_id,
            "scan_type": scan_type,
            "options": options,
            "status": "running",
            "progress": 0.0,
            "start_time": time.time(),
            "files_found": 0
        }
        
        self.active_scans[scan_id] = scan_info
        
        # Start the scan in the background
        asyncio.create_task(self._run_scan(scan_id, drive_id, scan_type, options))
        
        return scan_id

    async def _run_scan(self, scan_id: str, drive_id: str, scan_type: str, options: dict):
        """Run the actual scan operation"""
        try:
            logger.info(f"Starting {scan_type} scan for drive {drive_id}")
            
            scan_info = self.active_scans[scan_id]
            
            # All scan types now use Python-based file recovery
            await self._run_python_scan(scan_id, drive_id, scan_type, options)
            
            # Check if scan was cancelled during execution
            if scan_info.get("status") == "cancelled":
                logger.info(f"Scan {scan_id} was cancelled - partial results available: {scan_info.get('files_found', 0)} files")
                # Still broadcast so frontend knows there are partial results
                await self._broadcast_progress(scan_id)
                return
            
            # Mark as completed
            scan_info["status"] = "completed"
            scan_info["progress"] = 100.0
            scan_info["end_time"] = time.time()
            
            # Broadcast final progress
            await self._broadcast_progress(scan_id)
            
        except Exception as e:
            logger.error(f"Error during scan {scan_id}: {e}", exc_info=True)
            # Don't override cancelled status
            if self.active_scans[scan_id].get("status") != "cancelled":
                self.active_scans[scan_id]["status"] = "error"
                self.active_scans[scan_id]["error"] = str(e)
            await self._broadcast_progress(scan_id)

    async def _run_python_scan(self, scan_id: str, drive_id: str, scan_type: str, options: dict):
        """Run Python-based file recovery scan"""
        scan_info = self.active_scans[scan_id]
        
        try:
            logger.info(f"Starting Python-based file recovery scan on drive {drive_id}")
            
            # Get drive path
            drive_path = self._convert_drive_id_to_path(drive_id)
            logger.info(f"Converted drive ID '{drive_id}' to path: '{drive_path}'")
            
            # Get scan options
            from app.config import settings
            output_path = options.get('outputPath')
            
            # Use custom output path if provided, otherwise use temp directory with timestamp
            if output_path:
                scan_output_dir = os.path.abspath(output_path)
            else:
                # Create folder name with date and time: scan_YYYY-MM-DD_HH-MM-SS
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                scan_output_dir = os.path.join(settings.TEMP_DIR, f"scan_{timestamp}")
            
            os.makedirs(scan_output_dir, exist_ok=True)
            logger.info(f"Output directory: {scan_output_dir}")
            
            # Add scan_type to options for filtering
            scan_options = options.copy() if options else {}
            scan_options['scan_type'] = scan_type  # Pass scan type (quick/normal/deep)
            logger.info(f"Scan type: {scan_type}")
            
            # Create progress callback to update scan_info and broadcast
            async def progress_callback(progress_data):
                scan_info['progress'] = progress_data.get('progress', 0)
                scan_info['files_found'] = progress_data.get('files_found', 0)
                scan_info['scan_stats'] = {
                    'total_sectors': progress_data.get('total_sectors', 0),
                    'scanned_sectors': progress_data.get('sectors_scanned', 0),
                    'current_pass': progress_data.get('current_pass', 1),
                    'expected_time': progress_data.get('expected_time', 'Calculating...'),
                }
                # Broadcast to frontend
                await self._broadcast_progress(scan_id)
            
            # Create cancellation checker
            def is_cancelled():
                current_status = self.active_scans.get(scan_id, {}).get('status')
                is_cancelled_result = current_status == 'cancelled'
                if is_cancelled_result:
                    logger.info(f"🚫 is_cancelled() returning True - scan status is '{current_status}'")
                return is_cancelled_result
            
            # Add cancellation checker to options
            scan_options['is_cancelled'] = is_cancelled
            
            # Run the scan with progress tracking
            result = await self.recovery_service.scan_drive(
                drive_path,
                scan_output_dir,
                scan_options,  # Pass modified options with scan_type
                progress_callback
            )
            
            # Get recovered files
            recovered_files = result.get('files', [])
            statistics = result.get('statistics', {})
            
            logger.info(f"Python scan completed/cancelled: {len(recovered_files)} files found so far")
            logger.info(f"💡 NOTE: Files are INDEXED only (0 bytes written to disk)")
            logger.info(f"📋 Use selective recovery to write specific files")
            
            # Convert to RecoveredFile format and save even if cancelled
            # This allows viewing and recovering partial results
            self.scan_results[scan_id] = self._convert_to_recovered_files(recovered_files, scan_id)
            scan_info["files_found"] = len(self.scan_results[scan_id])
            
            # Mark that these are indexed files (not actually recovered yet)
            scan_info["indexed_mode"] = True
            scan_info["disk_space_used"] = 0  # No files written
            scan_info["recovery_mode"] = "selective"  # Requires selective recovery
            
            # Store additional scan-specific data (for cluster and health scans)
            if 'cluster_map' in result:
                scan_info["cluster_map"] = result.get('cluster_map_file')
                logger.info(f"Cluster map saved to: {result.get('cluster_map_file')}")
            
            if 'health_data' in result:
                scan_info["health_data"] = result['health_data']
                scan_info["health_report"] = result.get('health_report_file')
                logger.info(f"Health report saved to: {result.get('health_report_file')}")
            
            # Update statistics in scan_info
            scan_info["scan_stats"] = {
                "total_sectors": statistics.get('total_sectors', 0),
                "scanned_sectors": statistics.get('sectors_scanned', 0),
                "current_pass": 1,
                "expected_time": "Complete" if scan_info.get("status") != "cancelled" else "Cancelled"
            }
            
            # Check if scan was cancelled during execution
            if scan_info.get("status") == "cancelled":
                logger.info(f"Scan {scan_id} was cancelled, but {len(recovered_files)} partial results saved")
                # Don't set progress to 100 if cancelled
                scan_info["progress"] = min(scan_info.get("progress", 0), 99)
                return
            else:
                # Only set to 100% if scan completed normally
                scan_info["progress"] = 100
            
        except PermissionError as e:
            logger.error(f"Permission denied for scan: {e}")
            scan_info["status"] = "error"
            scan_info["error"] = "Administrator rights required to scan physical drives"
            raise
        except Exception as e:
            logger.error(f"Error in Python scan: {e}", exc_info=True)
            scan_info["status"] = "error"
            scan_info["error"] = str(e)
            raise
    
    def _convert_drive_id_to_path(self, drive_id: str) -> str:
        """Convert drive ID to physical drive path"""
        # Handle different drive ID formats
        # e.g., "e--e" -> "E:", "c" -> "C:", "E:" -> "E:"
        
        logger.info(f"Converting drive ID '{drive_id}' to path...")
        
        # If already has colon, just uppercase and return
        if ':' in drive_id:
            result = drive_id.upper()
            logger.info(f"Drive ID already has colon, returning: {result}")
            return result
        
        # Extract just the first letter (handle formats like "e--e")
        drive_letter = drive_id[0].upper()
        result = f"{drive_letter}:"
        logger.info(f"Converted drive ID '{drive_id}' to drive letter: {result}")
        return result
    
    def _format_time(self, seconds: float) -> str:
        """Format time as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}h{minutes:02d}m{secs:02d}s"
    
    def _calculate_expected_time(self, elapsed_seconds: float, progress_percent: float) -> str:
        """
        Calculate expected remaining time based on current progress
        
        Args:
            elapsed_seconds: Time elapsed so far in seconds
            progress_percent: Current progress percentage (0-100)
            
        Returns:
            Formatted expected time remaining as HH:MM:SS
        """
        if progress_percent <= 0 or progress_percent >= 100:
            return "Calculating..."
        
        # Calculate total expected time based on current rate
        total_expected_seconds = (elapsed_seconds / progress_percent) * 100
        
        # Calculate remaining time
        remaining_seconds = total_expected_seconds - elapsed_seconds
        
        # Ensure non-negative
        remaining_seconds = max(0, remaining_seconds)
        
        return self._format_time(remaining_seconds)

    async def _broadcast_progress(self, scan_id: str):
        """Broadcast scan progress via WebSocket"""
        if scan_id in self.active_scans:
            scan_info = self.active_scans[scan_id]
            progress_data = {
                "type": "scan_progress",
                "scanId": scan_id,
                "status": scan_info["status"],
                "progress": scan_info["progress"],
                "filesFound": scan_info.get("files_found", 0),
                "scan_stats": scan_info.get("scan_stats", {})
            }
            await websocket_manager.broadcast(progress_data)
    
    def _convert_to_recovered_files(self, files: List[Dict], scan_id: str) -> List[RecoveredFile]:
        """Convert file dictionaries to RecoveredFile objects"""
        recovered_files = []
        
        for file_dict in files:
            try:
                size_bytes = file_dict.get('size', 0)
                size_str = self._format_file_size(size_bytes)
                file_status = file_dict.get('status', 'found')
                
                # For indexed files, use 'indexed' status; otherwise use 'found'
                if file_status == 'indexed':
                    display_status = 'indexed'
                elif file_status in ['recovered', 'failed', 'recovering']:
                    display_status = file_status
                else:
                    display_status = 'found'
                
                recovered_file = RecoveredFile(
                    id=f"{scan_id}_{file_dict.get('name', 'unknown')}",
                    name=file_dict.get('name', 'unknown'),
                    type=file_dict.get('type', 'DAT').upper(),
                    size=size_str,
                    sizeBytes=size_bytes,
                    dateModified=file_dict.get('recovered_at', file_dict.get('indexed_at', datetime.now().isoformat())),
                    path=file_dict.get('path', ''),
                    recoveryChance=self._estimate_recovery_chance(file_dict),
                    sector=file_dict.get('offset', 0) // 512,  # Convert offset to sector
                    thumbnail=None,
                    isSelected=False,
                    status=display_status,
                    # Additional fields for indexed file recovery
                    offset=file_dict.get('offset', 0),
                    drivePath=file_dict.get('drive_path', ''),
                    drive_path=file_dict.get('drive_path', ''),
                    sha256=file_dict.get('sha256', file_dict.get('hash', '')),
                    hash=file_dict.get('sha256', file_dict.get('hash', '')),
                    method=file_dict.get('method', 'unknown'),
                    extension=file_dict.get('extension', file_dict.get('type', '').lower())
                )
                recovered_files.append(recovered_file)
            except Exception as e:
                logger.error(f"Error converting file {file_dict.get('name')}: {e}")
        
        return recovered_files
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    def _estimate_recovery_chance(self, file_dict: Dict) -> str:
        """Estimate recovery chance based on file characteristics"""
        size = file_dict.get('size', 0)
        
        # Simple heuristic based on file size
        if size == 0:
            return "Low"
        elif size < 1024:  # Very small files
            return "Average"
        elif size > 10 * 1024 * 1024:  # Files > 10MB
            return "High"
        else:
            return "High"
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict]:
        """Get the status of a scan"""
        if scan_id in self.active_scans:
            scan_info = self.active_scans[scan_id].copy()
            scan_info["files_count"] = len(self.scan_results.get(scan_id, []))
            return scan_info
        return None
    
    def get_scan_results(self, scan_id: str) -> List[RecoveredFile]:
        """Get the results of a completed scan"""
        return self.scan_results.get(scan_id, [])
    
    async def cancel_scan(self, scan_id: str):
        """Cancel a running scan"""
        logger.info(f"🛑 Cancel scan request received for scan_id: {scan_id}")
        logger.info(f"📋 Current active scans: {list(self.active_scans.keys())}")
        
        if scan_id in self.active_scans:
            logger.info(f"✅ Found scan {scan_id} in active_scans")
            scan_info = self.active_scans[scan_id]
            logger.info(f"📊 Current scan status: {scan_info['status']}")
            
            # Only cancel if it's actually running
            if scan_info["status"] in ["running", "pending"]:
                logger.info(f"🔄 Changing status from '{scan_info['status']}' to 'cancelled'")
                scan_info["status"] = "cancelled"
                current_progress = scan_info.get("progress", 0)
                scan_info["end_time"] = time.time()
                
                # Broadcast cancellation status
                await self._broadcast_progress(scan_id)
                
                logger.info(f"✅ Scan {scan_id} cancelled successfully at {current_progress}% progress")
                logger.info(f"📡 Cancellation broadcast sent, is_cancelled() should now return True")
                
                # Clean up after a short delay to allow final broadcast
                await asyncio.sleep(0.5)
                
                return True
            else:
                logger.warning(f"⚠️ Scan {scan_id} is not in a cancellable state (status: {scan_info['status']})")
                return False
        else:
            logger.warning(f"❌ Attempted to cancel non-existent scan {scan_id}")
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")


# Global scan service instance
scan_service = ScanService()
