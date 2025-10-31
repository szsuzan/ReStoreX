import subprocess
import shutil
import platform
import logging
from typing import Optional, List, Dict
import re

logger = logging.getLogger(__name__)


class TestDiskService:
    def __init__(self):
        self.testdisk_cmd = self._find_testdisk()
        self.photorec_cmd = self._find_photorec()
        self.system = platform.system()

    def _find_testdisk(self) -> Optional[str]:
        """Find TestDisk executable"""
        from app.config import settings
        
        if settings.TESTDISK_PATH:
            return settings.TESTDISK_PATH
        
        # Try to find in system PATH
        # On Windows, try both testdisk and testdisk_win.exe
        testdisk_names = ["testdisk", "testdisk_win.exe", "testdisk.exe"]
        
        for name in testdisk_names:
            testdisk = shutil.which(name)
            if testdisk:
                logger.info(f"TestDisk found at: {testdisk}")
                return testdisk
        
        logger.warning("TestDisk not found in system PATH")
        return None

    def _find_photorec(self) -> Optional[str]:
        """Find PhotoRec executable"""
        from app.config import settings
        
        if settings.PHOTOREC_PATH:
            return settings.PHOTOREC_PATH
        
        # Try to find in system PATH
        # On Windows, try both photorec and photorec_win.exe
        photorec_names = ["photorec", "photorec_win.exe", "photorec.exe"]
        
        for name in photorec_names:
            photorec = shutil.which(name)
            if photorec:
                logger.info(f"PhotoRec found at: {photorec}")
                return photorec
        
        logger.warning("PhotoRec not found in system PATH")
        return None

    async def check_testdisk(self) -> bool:
        """Check if TestDisk is available"""
        if not self.testdisk_cmd:
            return False
        try:
            result = subprocess.run(
                [self.testdisk_cmd, "/version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking TestDisk: {e}")
            return False

    async def check_photorec(self) -> bool:
        """Check if PhotoRec is available"""
        if not self.photorec_cmd:
            return False
        try:
            result = subprocess.run(
                [self.photorec_cmd, "/version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking PhotoRec: {e}")
            return False

    async def list_disks(self) -> List[str]:
        """List available disks using TestDisk"""
        if not self.testdisk_cmd:
            logger.error("TestDisk not available")
            return []
        
        try:
            # Create a temporary file for testdisk to write to
            result = subprocess.run(
                [self.testdisk_cmd, "/list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse the output to extract disk information
            disks = []
            output_lines = result.stdout.split('\n')
            
            for line in output_lines:
                # Look for disk patterns (e.g., /dev/sda, PhysicalDrive0, etc.)
                if 'Disk' in line or '/dev/' in line or 'PhysicalDrive' in line:
                    disks.append(line.strip())
            
            return disks
        except Exception as e:
            logger.error(f"Error listing disks: {e}")
            return []

    def parse_testdisk_output(self, output: str) -> List[Dict]:
        """Parse TestDisk output to extract file information"""
        files = []
        # This is a simplified parser - actual implementation would be more complex
        # depending on TestDisk's output format
        
        lines = output.split('\n')
        for line in lines:
            # Parse file information from TestDisk output
            # Format varies, this is a placeholder
            if line.strip() and not line.startswith('#'):
                # Extract file details
                pass
        
        return files


testdisk_service = TestDiskService()
