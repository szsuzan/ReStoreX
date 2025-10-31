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

    async def get_drive_health(self, drive_id: str) -> Optional[Dict]:
        """Get detailed health information for a drive"""
        try:
            drive = await self.get_drive(drive_id)
            if not drive:
                return None
            
            # Get the partition for this drive
            partition = self._find_partition_by_id(drive_id)
            if not partition:
                return None
            
            # Get disk usage
            usage = psutil.disk_usage(partition.mountpoint)
            
            # Get disk I/O statistics
            io_counters = psutil.disk_io_counters(perdisk=False)
            
            # Calculate health score (0-100)
            health_score = 100
            issues = []
            
            # Check disk usage
            if usage.percent > 95:
                health_score -= 30
                issues.append("Disk is almost full (>95%)")
            elif usage.percent > 80:
                health_score -= 10
                issues.append("Disk usage is high (>80%)")
            
            # Check file system
            if not partition.fstype or partition.fstype == "":
                health_score -= 40
                issues.append("File system not recognized")
            
            # Determine health status
            if health_score >= 80:
                health_status = "Excellent"
            elif health_score >= 60:
                health_status = "Good"
            elif health_score >= 40:
                health_status = "Fair"
            else:
                health_status = "Poor"
            
            return {
                "drive_id": drive_id,
                "drive_name": drive.name,
                "health_score": health_score,
                "health_status": health_status,
                "issues": issues if issues else ["No issues detected"],
                "disk_usage": {
                    "total": self._format_bytes(usage.total),
                    "used": self._format_bytes(usage.used),
                    "free": self._format_bytes(usage.free),
                    "percent": round(usage.percent, 1)
                },
                "io_stats": {
                    "read_count": io_counters.read_count if io_counters else 0,
                    "write_count": io_counters.write_count if io_counters else 0,
                    "read_bytes": self._format_bytes(io_counters.read_bytes) if io_counters else "0 B",
                    "write_bytes": self._format_bytes(io_counters.write_bytes) if io_counters else "0 B"
                },
                "recommendations": self._get_health_recommendations(health_score, issues)
            }
        except Exception as e:
            logger.error(f"Error getting drive health for {drive_id}: {e}")
            return None

    async def get_drive_details(self, drive_id: str) -> Optional[Dict]:
        """Get comprehensive details about a drive"""
        try:
            drive = await self.get_drive(drive_id)
            if not drive:
                return None
            
            # Get the partition for this drive
            partition = self._find_partition_by_id(drive_id)
            if not partition:
                return None
            
            # Get disk usage
            usage = psutil.disk_usage(partition.mountpoint)
            
            return {
                "drive_id": drive_id,
                "basic_info": {
                    "name": drive.name,
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "file_system": partition.fstype,
                    "status": drive.status
                },
                "capacity": {
                    "total": self._format_bytes(usage.total),
                    "used": self._format_bytes(usage.used),
                    "free": self._format_bytes(usage.free),
                    "percent_used": round(usage.percent, 1),
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free
                },
                "partition_info": {
                    "mount_options": partition.opts if hasattr(partition, 'opts') else "N/A",
                    "max_file_size": self._get_max_file_size(partition.fstype),
                    "max_volume_size": self._get_max_volume_size(partition.fstype)
                },
                "system_info": {
                    "platform": self.system,
                    "accessible": True,
                    "readable": True,
                    "writable": self._check_writable(partition.mountpoint)
                },
                "recovery_info": {
                    "scannable": drive.status != "error",
                    "recommended_scan_type": self._recommend_scan_type(drive.status, partition.fstype),
                    "estimated_scan_time": self._estimate_scan_time(usage.total)
                }
            }
        except Exception as e:
            logger.error(f"Error getting drive details for {drive_id}: {e}")
            return None

    def _find_partition_by_id(self, drive_id: str):
        """Find partition by drive ID"""
        try:
            partitions = psutil.disk_partitions(all=True)
            for partition in partitions:
                if self._generate_drive_id(partition) == drive_id:
                    return partition
            return None
        except Exception as e:
            logger.error(f"Error finding partition: {e}")
            return None

    def _get_health_recommendations(self, health_score: int, issues: List[str]) -> List[str]:
        """Get health recommendations based on score and issues"""
        recommendations = []
        
        if health_score < 60:
            recommendations.append("⚠️ Consider backing up important data immediately")
        
        if any("full" in issue.lower() for issue in issues):
            recommendations.append("🗑️ Free up disk space by deleting unnecessary files")
            recommendations.append("📦 Move large files to another drive")
        
        if any("file system" in issue.lower() for issue in issues):
            recommendations.append("🔧 Run a disk check utility")
            recommendations.append("💾 Consider reformatting if problems persist")
        
        if not recommendations:
            recommendations.append("✅ Drive is healthy and ready for use")
            recommendations.append("💡 Regular backups are still recommended")
        
        return recommendations

    def _check_writable(self, mountpoint: str) -> bool:
        """Check if drive is writable"""
        try:
            # Try to check write permissions
            import os
            return os.access(mountpoint, os.W_OK)
        except:
            return False

    def _get_max_file_size(self, fstype: str) -> str:
        """Get maximum file size for file system"""
        max_sizes = {
            "ntfs": "16 TB",
            "fat32": "4 GB",
            "exfat": "16 EB",
            "ext4": "16 TB",
            "ext3": "2 TB",
            "ext2": "2 TB",
            "hfs+": "8 EB",
            "apfs": "8 EB"
        }
        return max_sizes.get(fstype.lower(), "Unknown")

    def _get_max_volume_size(self, fstype: str) -> str:
        """Get maximum volume size for file system"""
        max_sizes = {
            "ntfs": "256 TB",
            "fat32": "2 TB",
            "exfat": "128 PB",
            "ext4": "1 EB",
            "ext3": "32 TB",
            "ext2": "32 TB",
            "hfs+": "8 EB",
            "apfs": "8 EB"
        }
        return max_sizes.get(fstype.lower(), "Unknown")

    def _recommend_scan_type(self, status: str, fstype: str) -> str:
        """Recommend scan type based on drive status"""
        if status == "damaged":
            return "Deep Scan (recommended for damaged drives)"
        elif status == "healthy":
            return "Normal Scan (fast and efficient)"
        else:
            return "Health Scan (check drive condition first)"

    def _estimate_scan_time(self, total_bytes: int) -> str:
        """Estimate scan time based on drive size"""
        # Rough estimate: 100 MB/s scan speed
        seconds = total_bytes / (100 * 1024 * 1024)
        
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            return f"{int(seconds / 60)} minutes"
        else:
            return f"{int(seconds / 3600)} hours"


drive_service = DriveService()
