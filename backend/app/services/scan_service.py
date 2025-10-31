import asyncio
import subprocess
import uuid
import time
import logging
from typing import Dict, Optional, List
from datetime import datetime
import os
import json

from app.models import ScanProgress, RecoveredFile
from app.services.testdisk_service import testdisk_service
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class ScanService:
    def __init__(self):
        self.active_scans: Dict[str, Dict] = {}
        self.scan_results: Dict[str, List[RecoveredFile]] = {}

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
            
            # Based on scan type, run different operations
            if scan_type == "normal":
                await self._run_normal_scan(scan_id, drive_id, options)
            elif scan_type == "deep":
                await self._run_deep_scan(scan_id, drive_id, options)
            elif scan_type == "cluster":
                await self._run_cluster_scan(scan_id, drive_id, options)
            elif scan_type == "health":
                await self._run_health_scan(scan_id, drive_id, options)
            elif scan_type == "signature":
                await self._run_signature_scan(scan_id, drive_id, options)
            
            scan_info["status"] = "completed"
            scan_info["progress"] = 100.0
            
            # Notify completion
            await self._broadcast_progress(scan_id)
            
        except Exception as e:
            logger.error(f"Error during scan {scan_id}: {e}")
            self.active_scans[scan_id]["status"] = "error"
            self.active_scans[scan_id]["error"] = str(e)
            await self._broadcast_progress(scan_id)

    async def _run_normal_scan(self, scan_id: str, drive_id: str, options: dict):
        """Run a normal/quick scan using PhotoRec"""
        scan_info = self.active_scans[scan_id]
        
        # Simulate scan progress (in real implementation, parse PhotoRec output)
        for i in range(20):
            await asyncio.sleep(0.5)
            scan_info["progress"] = (i + 1) * 5
            scan_info["files_found"] = (i + 1) * 50
            await self._broadcast_progress(scan_id)
            
            if scan_info["status"] == "cancelled":
                return
        
        # Generate mock results (in real implementation, parse actual results)
        self.scan_results[scan_id] = self._generate_mock_files(scan_id, 100)

    async def _run_deep_scan(self, scan_id: str, drive_id: str, options: dict):
        """Run a deep scan"""
        scan_info = self.active_scans[scan_id]
        
        # Deep scan takes longer
        for i in range(50):
            await asyncio.sleep(0.3)
            scan_info["progress"] = (i + 1) * 2
            scan_info["files_found"] = (i + 1) * 30
            await self._broadcast_progress(scan_id)
            
            if scan_info["status"] == "cancelled":
                return
        
        self.scan_results[scan_id] = self._generate_mock_files(scan_id, 200)

    async def _run_cluster_scan(self, scan_id: str, drive_id: str, options: dict):
        """Run a cluster analysis scan"""
        # Similar to normal scan but with cluster-specific logic
        await self._run_normal_scan(scan_id, drive_id, options)

    async def _run_health_scan(self, scan_id: str, drive_id: str, options: dict):
        """Run a disk health scan"""
        scan_info = self.active_scans[scan_id]
        
        for i in range(15):
            await asyncio.sleep(0.4)
            scan_info["progress"] = (i + 1) * 6.67
            await self._broadcast_progress(scan_id)
            
            if scan_info["status"] == "cancelled":
                return
        
        # Health scan doesn't find files, just analyzes disk
        self.scan_results[scan_id] = []

    async def _run_signature_scan(self, scan_id: str, drive_id: str, options: dict):
        """Run a file signature scan"""
        await self._run_normal_scan(scan_id, drive_id, options)

    async def _broadcast_progress(self, scan_id: str):
        """Broadcast scan progress via WebSocket"""
        scan_info = self.active_scans[scan_id]
        
        progress_data = ScanProgress(
            scanId=scan_id,
            isScanning=scan_info["status"] == "running",
            progress=scan_info["progress"],
            currentSector=int(scan_info["progress"] * 1000),
            totalSectors=100000,
            filesFound=scan_info["files_found"],
            estimatedTimeRemaining=self._calculate_eta(scan_info),
            status=scan_info["status"]
        )
        
        await websocket_manager.broadcast({
            "type": "scan_progress",
            "data": progress_data.dict()
        })

    def _calculate_eta(self, scan_info: Dict) -> str:
        """Calculate estimated time remaining"""
        elapsed = time.time() - scan_info["start_time"]
        progress = scan_info["progress"]
        
        if progress <= 0:
            return "Calculating..."
        
        total_time = (elapsed / progress) * 100
        remaining = total_time - elapsed
        
        minutes = int(remaining / 60)
        seconds = int(remaining % 60)
        
        return f"{minutes}m {seconds}s"

    def _generate_mock_files(self, scan_id: str, count: int) -> List[RecoveredFile]:
        """Generate mock recovered files for testing"""
        files = []
        file_types = [
            ("image.jpg", "JPG", "Image", "High"),
            ("document.pdf", "PDF", "Document", "Average"),
            ("video.mp4", "MP4", "Video", "High"),
            ("audio.mp3", "MP3", "Audio", "Average"),
            ("archive.zip", "ZIP", "Archive", "Low"),
        ]
        
        for i in range(count):
            name, ext, ftype, chance = file_types[i % len(file_types)]
            size_bytes = (i + 1) * 1024 * 100
            
            file = RecoveredFile(
                id=f"{scan_id}-file-{i}",
                name=f"{name.split('.')[0]}_{i}.{ext.lower()}",
                type=ext,
                size=self._format_bytes(size_bytes),
                sizeBytes=size_bytes,
                dateModified=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                path=f"\\Recovered\\{ftype}\\{name.split('.')[0]}_{i}.{ext.lower()}",
                recoveryChance=chance,
                sector=1000 + i,
                cluster=500 + i,
                inode=100 + i,
                status="found"
            )
            files.append(file)
        
        return files

    def _format_bytes(self, bytes: int) -> str:
        """Format bytes into human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"

    async def get_scan_status(self, scan_id: str) -> Optional[Dict]:
        """Get the status of a scan"""
        if scan_id not in self.active_scans:
            return None
        
        scan_info = self.active_scans[scan_id]
        
        return {
            "scanId": scan_id,
            "isScanning": scan_info["status"] == "running",
            "progress": scan_info["progress"],
            "currentSector": int(scan_info["progress"] * 1000),
            "totalSectors": 100000,
            "filesFound": scan_info["files_found"],
            "estimatedTimeRemaining": self._calculate_eta(scan_info),
            "status": scan_info["status"]
        }

    async def cancel_scan(self, scan_id: str) -> bool:
        """Cancel a running scan"""
        if scan_id not in self.active_scans:
            return False
        
        self.active_scans[scan_id]["status"] = "cancelled"
        await self._broadcast_progress(scan_id)
        return True

    async def get_scan_results(self, scan_id: str, filters: dict = None) -> List[RecoveredFile]:
        """Get the results of a completed scan"""
        if scan_id not in self.scan_results:
            return []
        
        files = self.scan_results[scan_id]
        
        # Apply filters if provided
        if filters:
            files = self._apply_filters(files, filters)
        
        return files

    def _apply_filters(self, files: List[RecoveredFile], filters: dict) -> List[RecoveredFile]:
        """Apply filters to the file list"""
        filtered = files
        
        # Filter by file type
        if "fileType" in filters and filters["fileType"] != "all":
            filtered = [f for f in filtered if f.type.lower() == filters["fileType"].lower()]
        
        # Filter by recovery chance
        if "recoveryChances" in filters and filters["recoveryChances"]:
            filtered = [f for f in filtered if f.recoveryChance in filters["recoveryChances"]]
        
        # Search by name
        if "searchQuery" in filters and filters["searchQuery"]:
            query = filters["searchQuery"].lower()
            filtered = [f for f in filtered if query in f.name.lower()]
        
        # Sort
        if "sortBy" in filters:
            reverse = filters.get("sortOrder", "asc") == "desc"
            if filters["sortBy"] == "name":
                filtered = sorted(filtered, key=lambda x: x.name, reverse=reverse)
            elif filters["sortBy"] == "size":
                filtered = sorted(filtered, key=lambda x: x.sizeBytes, reverse=reverse)
            elif filters["sortBy"] == "date":
                filtered = sorted(filtered, key=lambda x: x.dateModified, reverse=reverse)
        
        return filtered


scan_service = ScanService()
