import psutil
import platform
import logging
from typing import List, Dict, Optional
from app.models import DriveInfo

logger = logging.getLogger(__name__)


class DriveService:
    def __init__(self):
        self.system = platform.system()

    async def get_all_drives(self) -> List[DriveInfo]:
        """Get all available drives/partitions"""
        drives = []
        
        try:
            partitions = psutil.disk_partitions(all=True)
            
            for partition in partitions:
                try:
                    # Skip certain mount points
                    if self._should_skip_partition(partition):
                        continue
                    
                    # Get disk usage
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    # Determine drive status (simplified)
                    status = self._determine_status(partition, usage)
                    
                    drive_info = DriveInfo(
                        id=self._generate_drive_id(partition),
                        name=f"{partition.device} ({partition.mountpoint})",
                        size=self._format_bytes(usage.total),
                        fileSystem=partition.fstype,
                        status=status
                    )
                    
                    drives.append(drive_info)
                except Exception as e:
                    logger.error(f"Error getting info for partition {partition.device}: {e}")
                    continue
            
            logger.info(f"Found {len(drives)} drives")
            return drives
            
        except Exception as e:
            logger.error(f"Error getting drives: {e}")
            return []

    async def get_drive(self, drive_id: str) -> Optional[DriveInfo]:
        """Get information about a specific drive"""
        drives = await self.get_all_drives()
        for drive in drives:
            if drive.id == drive_id:
                return drive
        return None

    async def validate_drive(self, drive_id: str) -> Dict:
        """Validate if a drive is accessible and ready for scanning"""
        drive = await self.get_drive(drive_id)
        
        if not drive:
            return {
                "valid": False,
                "message": "Drive not found",
                "error": "DRIVE_NOT_FOUND"
            }
        
        if drive.status == "error":
            return {
                "valid": False,
                "message": "Drive has errors and may not be scannable",
                "error": "DRIVE_ERROR"
            }
        
        return {
            "valid": True,
            "message": "Drive is ready for scanning",
            "drive": drive.dict()
        }

    def _should_skip_partition(self, partition) -> bool:
        """Determine if a partition should be skipped"""
        # Skip system pseudo-filesystems on Linux
        skip_fstypes = ['squashfs', 'tmpfs', 'devtmpfs', 'proc', 'sysfs', 'devpts']
        if partition.fstype.lower() in skip_fstypes:
            return True
        
        # Skip empty mount points
        if not partition.mountpoint:
            return True
        
        # On Windows, skip certain system mount points
        if self.system == "Windows":
            if partition.mountpoint in ['\\', 'System Reserved']:
                return False  # Actually keep these
        
        return False

    def _determine_status(self, partition, usage) -> str:
        """Determine the status of a drive"""
        try:
            # Check if drive is accessible
            if usage.percent > 95:
                return "damaged"  # Possibly full or problematic
            
            # Check file system
            if partition.fstype == "":
                return "damaged"
            
            return "healthy"
        except:
            return "error"

    def _generate_drive_id(self, partition) -> str:
        """Generate a unique ID for a drive"""
        # Clean up the device name to create a valid ID
        device = partition.device.replace("\\", "-").replace(":", "").replace("/", "-")
        mountpoint = partition.mountpoint.replace("\\", "-").replace(":", "").replace("/", "-")
        return f"{device}-{mountpoint}".lower().strip("-")

    def _format_bytes(self, bytes: int) -> str:
        """Format bytes into human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} PB"


drive_service = DriveService()
