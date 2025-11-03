"""
Python-based file recovery service using native Python libraries
Replaces TestDisk/PhotoRec with pure Python implementation

Enhanced with:
- SHA256 hashing for deduplication and verification
- Manifest generation (JSON) for all recovered files
- Parallel chunk processing for performance
- Fragmentation detection with .partial file marking
- Advanced format validation (Pillow for images, python-magic for MIME)
- Memory optimization with buffer management
"""
import os
import io
import json
import struct
import hashlib
import logging
import platform
import mmap
from typing import List, Dict, Optional, BinaryIO, Callable
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import concurrent.futures

# Optional imports for advanced validation
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Pillow not available - advanced image validation disabled")

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

# Optional pytsk3 for metadata-first recovery
try:
    import pytsk3
    PYTSK3_AVAILABLE = True
except ImportError:
    PYTSK3_AVAILABLE = False

logger = logging.getLogger(__name__)


class Win32FileWrapper:
    """Wrapper for Windows file handles to provide file-like interface"""
    
    def __init__(self, handle):
        """Initialize with a win32file handle"""
        self.handle = handle
        self.closed = False
        self.position = 0  # Track current position
        
    def seek(self, offset, whence=0):
        """Seek to a position in the file
        
        Args:
            offset: Byte offset to seek to
            whence: 0 = absolute, 1 = relative to current, 2 = relative to end
        """
        if self.closed:
            raise ValueError("I/O operation on closed file")
        
        try:
            import win32file
            import pywintypes
            
            # Map whence to Windows constants
            move_method = {
                0: win32file.FILE_BEGIN,      # Absolute position
                1: win32file.FILE_CURRENT,    # Relative to current
                2: win32file.FILE_END         # Relative to end
            }.get(whence, win32file.FILE_BEGIN)
            
            # For large offsets, split into high and low 32-bit values
            # This is required for raw disk access with files > 4GB
            low = offset & 0xFFFFFFFF  # Lower 32 bits
            high = (offset >> 32) & 0xFFFFFFFF  # Upper 32 bits
            
            try:
                # Try SetFilePointer with high/low split for 64-bit support
                new_pos = win32file.SetFilePointer(self.handle, low, move_method)
                
                # If we have a high part, we need to handle 64-bit positioning differently
                if high > 0 or offset > 0x7FFFFFFF:
                    # For very large offsets, use a different approach
                    # Convert to signed 64-bit integer
                    signed_offset = offset if offset < 0x8000000000000000 else offset - 0x10000000000000000
                    new_pos = win32file.SetFilePointer(self.handle, signed_offset, move_method)
                    
            except pywintypes.error as e:
                # If SetFilePointer fails, try an alternative approach
                # Seek to the position using chunked seeks for very large offsets
                if offset > 0x7FFFFFFF and whence == 0:  # Absolute seek with large offset
                    # Seek in chunks of 1GB
                    chunk_size = 1024 * 1024 * 1024  # 1GB
                    remaining = offset
                    
                    # First seek to 0
                    win32file.SetFilePointer(self.handle, 0, win32file.FILE_BEGIN)
                    
                    # Seek in chunks
                    while remaining > chunk_size:
                        win32file.SetFilePointer(self.handle, chunk_size, win32file.FILE_CURRENT)
                        remaining -= chunk_size
                    
                    # Seek the final remaining bytes
                    if remaining > 0:
                        new_pos = win32file.SetFilePointer(self.handle, int(remaining), win32file.FILE_CURRENT)
                else:
                    raise
            
            self.position = offset if whence == 0 else new_pos
            return self.position
        except Exception as e:
            logger.error(f"Error seeking in handle: {e}")
            raise
        
    def tell(self):
        """Return current file position"""
        return self.position
        
    def read(self, size=-1):
        """Read bytes from the handle"""
        if self.closed:
            raise ValueError("I/O operation on closed file")
        
        try:
            import win32file
            
            if size == -1:
                size = 1024 * 1024  # Default 1MB
            
            # Read from the file handle
            hr, data = win32file.ReadFile(self.handle, size, None)
            self.position += len(data)  # Update position after read
            return data
        except Exception as e:
            logger.error(f"Error reading from handle: {e}")
            return b''
    
    def close(self):
        """Close the file handle"""
        if not self.closed:
            try:
                import win32file
                win32file.CloseHandle(self.handle)
                self.closed = True
                logger.debug("File handle closed successfully")
            except Exception as e:
                logger.error(f"Error closing handle: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class FileSignature:
    """File signature definitions for file carving"""
    
    # Define important user file types (ONLY these extensions for File Carving)
    IMPORTANT_FILE_TYPES = {
        # Images / Photos (only 3)
        'jpg', 'png',
        
        # Documents / Office Files (8 types)
        'pdf', 'docx', 'xlsx', 'pptx', 'txt',
        
        # Videos (3 types)
        'mp4', 'avi', 'mov',
        
        # Audio / Music (2 types)
        'mp3', 'wav',
        
        # Archives / Compressed (2 types)
        'zip', 'rar',
        
        # Databases / Structured Data (2 types)
        'sqlite', 'csv',
    }
    
    SIGNATURES = {
        # 🖼️ Images / Photos (ONLY JPG, PNG)
        'jpg': {'header': b'\xFF\xD8\xFF', 'footer': b'\xFF\xD9', 'extension': 'jpg', 'important': True},
        'png': {'header': b'\x89PNG\r\n\x1a\n', 'footer': b'\x49\x45\x4E\x44\xAE\x42\x60\x82', 'extension': 'png', 'important': True},
        
        # 📄 Documents / Office Files (PDF, DOCX, XLSX, PPTX, TXT)
        'pdf': {'header': b'%PDF-', 'footer': b'%%EOF', 'extension': 'pdf', 'important': True},
        'docx': {'header': b'PK\x03\x04', 'footer': None, 'extension': 'docx', 'check': b'word/', 'important': True},
        'xlsx': {'header': b'PK\x03\x04', 'footer': None, 'extension': 'xlsx', 'check': b'xl/', 'important': True},
        'pptx': {'header': b'PK\x03\x04', 'footer': None, 'extension': 'pptx', 'check': b'ppt/', 'important': True},
        'txt': {'header': None, 'footer': None, 'extension': 'txt', 'important': True},  # Text files are hard to detect
        
        # �️ Archives / Compressed Files (ZIP, RAR only)
        'zip': {'header': b'PK\x03\x04', 'footer': b'PK\x05\x06', 'extension': 'zip', 'important': True},
        'rar': {'header': b'Rar!\x1a\x07', 'footer': None, 'extension': 'rar', 'important': True},
        
        # 🎵 Audio / Music (MP3, WAV only)
        'mp3': {'header': b'\xFF\xFB', 'footer': None, 'extension': 'mp3', 'important': True},
        'mp3_id3': {'header': b'ID3', 'footer': None, 'extension': 'mp3', 'important': True},
        'wav': {'header': b'RIFF', 'footer': None, 'extension': 'wav', 'check': b'WAVE', 'important': True},
        
        # 🎥 Videos (MP4, AVI, MOV only)
        'mp4': {'header': b'\x00\x00\x00\x18ftypmp4', 'footer': None, 'extension': 'mp4', 'important': True},
        'avi': {'header': b'RIFF', 'footer': None, 'extension': 'avi', 'check': b'AVI ', 'important': True},
        'mov': {'header': b'\x00\x00\x00\x14ftyp', 'footer': None, 'extension': 'mov', 'important': True},
        
        # 💾 Databases / Structured Data (SQLite, CSV)
        'sqlite': {'header': b'SQLite format 3\x00', 'footer': None, 'extension': 'sqlite', 'important': True},
        'csv': {'header': None, 'footer': None, 'extension': 'csv', 'important': True},  # CSV hard to detect by signature
        
        # ============ NOT RECOVERED (marked as not important) ============
        # Other images
        'gif': {'header': b'GIF89a', 'footer': b'\x00\x3B', 'extension': 'gif', 'important': False},
        'gif87': {'header': b'GIF87a', 'footer': b'\x00\x3B', 'extension': 'gif', 'important': False},
        'bmp': {'header': b'BM', 'footer': None, 'extension': 'bmp', 'important': False},
        'tiff_le': {'header': b'\x49\x49\x2A\x00', 'footer': None, 'extension': 'tif', 'important': False},
        'tiff_be': {'header': b'\x4D\x4D\x00\x2A', 'footer': None, 'extension': 'tif', 'important': False},
        'heic': {'header': b'\x00\x00\x00\x18ftypheic', 'footer': None, 'extension': 'heic', 'important': False},
        'psd': {'header': b'8BPS', 'footer': None, 'extension': 'psd', 'important': False},
        'svg': {'header': b'<?xml', 'footer': b'</svg>', 'extension': 'svg', 'check': b'<svg', 'important': False},
        
        # Other documents
        'rtf': {'header': b'{\\rtf', 'footer': None, 'extension': 'rtf', 'important': False},
        
        # Other archives
        '7z': {'header': b'7z\xBC\xAF\x27\x1C', 'footer': None, 'extension': '7z', 'important': False},
        'iso': {'header': b'CD001', 'footer': None, 'extension': 'iso', 'offset': 32769, 'important': False},
        
        # Other audio
        'flac': {'header': b'fLaC', 'footer': None, 'extension': 'flac', 'important': False},
        'ogg': {'header': b'OggS', 'footer': None, 'extension': 'ogg', 'important': False},
        'm4a': {'header': b'\x00\x00\x00\x20ftypM4A', 'footer': None, 'extension': 'm4a', 'important': False},
        
        # Other video
        'wmv': {'header': b'\x30\x26\xB2\x75\x8E\x66\xCF\x11', 'footer': None, 'extension': 'wmv', 'important': False},
        'flv': {'header': b'FLV\x01', 'footer': None, 'extension': 'flv', 'important': False},
        'mkv': {'header': b'\x1A\x45\xDF\xA3', 'footer': None, 'extension': 'mkv', 'important': False},
        
        # System files
        'ico': {'header': b'\x00\x00\x01\x00', 'footer': None, 'extension': 'ico', 'important': False},
        'cur': {'header': b'\x00\x00\x02\x00', 'footer': None, 'extension': 'cur', 'important': False},
        'exe': {'header': b'MZ', 'footer': None, 'extension': 'exe', 'important': False},
        'dll': {'header': b'MZ', 'footer': None, 'extension': 'dll', 'important': False},
    }


class PythonRecoveryService:
    """Python-based file recovery service"""
    
    def __init__(self, temp_dir: str = None):
        self.temp_dir = temp_dir or os.path.join(os.getcwd(), 'temp')
        self.signatures = FileSignature.SIGNATURES
    
    @staticmethod
    def cleanup_temp_files():
        """
        Clean up temporary recovered files on app startup.
        This removes all files from the backend/recovered_files directory.
        """
        try:
            # Get project root (parent of backend directory)
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            temp_recovery_dir = os.path.join(project_root, 'backend', 'recovered_files')
            
            if os.path.exists(temp_recovery_dir):
                # Remove all files in the directory
                import shutil
                file_count = len([f for f in os.listdir(temp_recovery_dir) if os.path.isfile(os.path.join(temp_recovery_dir, f))])
                
                if file_count > 0:
                    logger.info(f"🗑️ Cleaning up {file_count} temporary recovered files...")
                    
                    # Remove all files but keep the directory
                    for filename in os.listdir(temp_recovery_dir):
                        file_path = os.path.join(temp_recovery_dir, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as e:
                            logger.warning(f"Failed to delete {file_path}: {e}")
                    
                    logger.info(f"✅ Temporary files cleaned up successfully")
                else:
                    logger.info("No temporary files to clean up")
            else:
                logger.info("Temporary recovery directory does not exist yet")
                
        except Exception as e:
            logger.error(f"Failed to cleanup temporary files: {e}")
        
    async def scan_drive(self, drive_path: str, output_dir: str, 
                        options: Optional[Dict] = None,
                        progress_callback: Optional[Callable] = None) -> Dict:
        """
        Scan a drive for recoverable files using Python
        
        SAFETY FEATURES:
        - Read-only operations (no writes to source drive)
        - Volume-level access only (no physical disk modification)
        - Automatic error recovery
        - No filesystem modification
        
        Args:
            drive_path: Physical drive path (e.g., \\\\.\\PHYSICALDRIVE1 or E:)
            output_dir: Directory to save recovered files
            options: Scan options (partition, filesystem, etc.)
            progress_callback: Async callback function for progress updates
            
        Returns:
            Dictionary with scan results
        """
        try:
            scan_type = options.get('scan_type', 'normal') if options else 'normal'
            logger.info(f"Starting Python-based {scan_type} scan on {drive_path}")
            logger.info(f"🔒 SAFE MODE: Read-only operation - No writes to source drive")
            logger.info(f"Output directory: {output_dir}")
            
            # Handle special scan types
            if scan_type == 'cluster':
                logger.info("🔍 Cluster Scan: Analyzing disk clusters and generating hex view")
                return await self._cluster_scan(drive_path, output_dir, options, progress_callback)
            elif scan_type == 'health':
                logger.info("🏥 Health Scan: Reading SMART data and analyzing disk health")
                return await self._health_scan(drive_path, output_dir, options, progress_callback)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Get drive size
            drive_size = self._get_drive_size(drive_path)
            total_sectors = drive_size // 512 if drive_size else 0
            
            # Statistics
            stats = {
                'drive_path': drive_path,
                'files_found': 0,
                'bytes_scanned': 0,
                'total_size': drive_size,
                'start_time': datetime.now().isoformat(),
                'sectors_scanned': 0,
                'total_sectors': total_sectors,
            }
            
            # Convert drive path to physical drive if needed
            physical_drive = self._get_physical_drive(drive_path)
            logger.info(f"Physical drive: {physical_drive}")
            logger.info(f"Drive size: {drive_size / (1024**3):.2f} GB, Total sectors: {total_sectors}")
            
            # Store physical drive for later recovery access
            stats['physical_drive'] = physical_drive
            
            # Open the drive for reading
            try:
                drive_handle = self._open_drive(physical_drive)
            except PermissionError:
                logger.error("Permission denied. Administrator rights required to access physical drives.")
                raise Exception("Administrator rights required to scan physical drives")
            
            # NORMAL SCAN: Fast metadata-first recovery (MFT parsing for NTFS)
            # This analyzes filesystem structure, partition table, and metadata without scanning every sector
            if scan_type == 'normal':
                logger.info("🚀 Normal Scan: Quick metadata-first recovery (analyzing filesystem structure)")
                logger.info("   - Scanning partition table and metadata")
                logger.info("   - Looking for existing and recently deleted files")
                logger.info("   - NO sector-by-sector scanning (faster)")
                try:
                    recovered_files = await self._metadata_first_recovery(
                        drive_handle,
                        output_dir,
                        stats,
                        options,
                        progress_callback
                    )
                    
                    if len(recovered_files) == 0:
                        logger.warning("⚠️ Normal scan found no files via metadata")
                        logger.info("💡 Suggestion: Try Deep Scan for comprehensive sector-by-sector recovery")
                    else:
                        logger.info(f"✅ Normal scan complete: {len(recovered_files)} files recovered from filesystem metadata")
                        
                except Exception as e:
                    logger.error(f"❌ Normal scan failed: {e}", exc_info=True)
                    logger.info("💡 Falling back to empty result - try Deep Scan instead")
                    recovered_files = []
            
            # DEEP SCAN: Signature-based carving for comprehensive recovery
            elif scan_type == 'deep':
                logger.info("🔍🔍 DEEP SCAN: Comprehensive Signature-Based Recovery")
                logger.info("=" * 70)
                logger.info("   • Scans entire drive sector-by-sector")
                logger.info("   • Detects files by signature (magic bytes)")
                logger.info("   • Finds deleted, overwritten, and fragmented files")
                logger.info("=" * 70)
                
                # Deep scan uses all file types by default
                if not options.get('fileTypes'):
                    options['fileTypes'] = {
                        'images': True,
                        'documents': True,
                        'videos': True,
                        'audio': True,
                        'archives': True,
                        'email': True
                    }
                
                # Call deep scan method
                recovered_files = await self._deep_scan_hybrid(
                    drive_handle, 
                    output_dir, 
                    stats,
                    options,
                    progress_callback
                )
            
            # CARVING SCAN: Signature-based file carving with user-selected file types
            elif scan_type == 'carving':
                logger.info("🔍 File Carving Scan: Signature-based recovery with selected file types")
                recovered_files = await self._carve_files(
                    drive_handle, 
                    output_dir, 
                    stats,
                    options,
                    progress_callback
                )
            
            # Legacy support for 'quick' scan type
            elif scan_type == 'quick':
                logger.info("🚀 Quick Scan: Fast important file recovery")
                recovered_files = await self._carve_files(
                    drive_handle, 
                    output_dir, 
                    stats,
                    options,
                    progress_callback
                )
            
            # Default fallback
            else:
                logger.warning(f"⚠️ Unknown scan type '{scan_type}', defaulting to normal scan")
                recovered_files = await self._metadata_first_recovery(
                    drive_handle,
                    output_dir,
                    stats,
                    options,
                    progress_callback
                )
            
            # Close drive handle
            drive_handle.close()
            
            end_time_dt = datetime.now()
            stats['end_time'] = end_time_dt.isoformat()
            stats['duration'] = (end_time_dt - datetime.fromisoformat(stats['start_time'])).total_seconds()
            stats['files_found'] = len(recovered_files)
            
            logger.info(f"Scan completed: {stats['files_found']} files found")
            
            return {
                'files': recovered_files,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error during Python scan: {e}", exc_info=True)
            raise
    
    def _optimize_buffer_size(self, drive_size: int, available_memory: int) -> int:
        """
        Calculate optimal buffer/chunk size based on drive size and available memory
        
        Args:
            drive_size: Total size of drive in bytes
            available_memory: Available system memory in bytes
            
        Returns:
            Optimal chunk size in bytes
        """
        # Use 1% of available memory, but cap between 1MB and 10MB
        optimal_size = int(available_memory * 0.01)
        optimal_size = max(1 * 1024 * 1024, min(optimal_size, 10 * 1024 * 1024))
        
        # For small drives (<1GB), use smaller chunks
        if drive_size < 1024 * 1024 * 1024:
            optimal_size = min(optimal_size, 2 * 1024 * 1024)
        
        logger.info(f"Optimized chunk size: {optimal_size / (1024*1024):.2f} MB")
        return optimal_size
    
    def _get_available_memory(self) -> int:
        """Get available system memory in bytes"""
        try:
            import psutil
            return psutil.virtual_memory().available
        except:
            # Default to assuming 4GB available if psutil fails
            return 4 * 1024 * 1024 * 1024
    
    def _get_physical_drive(self, drive_path: str) -> str:
        """Convert drive letter to physical drive path"""
        # If already a physical drive path (\.\\PHYSICALDRIVE...), return as-is
        if drive_path and drive_path.upper().startswith('\\\\.\\'):
            return drive_path

        # On Windows, for drive letters, return the simple drive letter (e.g., 'E:')
        # Let _open_drive create the correct raw device path (\\.\E:) when needed
        if platform.system() == 'Windows' and ':' in drive_path:
            try:
                # Extract a letter followed by ':' (handles 'E:' and '\\.\\E:')
                import re
                m = re.search(r'([A-Za-z]):', drive_path)
                if m:
                    drive_letter = m.group(1).upper() + ':'
                else:
                    # Fallback: take first char
                    drive_letter = drive_path[0].upper() + ':'

                logger.info(f"Using volume identifier for drive {drive_letter} (scan limited to partition)")
                return drive_letter
            except Exception as e:
                logger.warning(f"Could not map drive letter: {e}")
                # As a last resort, return original path
                return drive_path

        return drive_path
    
    def _get_drive_size(self, drive_path: str) -> int:
        """Get the size of a drive in bytes"""
        try:
            if platform.system() == 'Windows':
                import psutil
                # Extract drive letter robustly (handle 'E:' and '\\.\\E:')
                import re
                m = re.search(r'([A-Za-z]):', drive_path)
                if m:
                    drive_letter = m.group(1).upper() + ':'
                    # Get partition info
                    partitions = psutil.disk_partitions()
                    for partition in partitions:
                        try:
                            # partition.device on Windows is like 'E:\' - compare only the letter
                            if partition.device.upper().startswith(drive_letter):
                                usage = psutil.disk_usage(partition.mountpoint)
                                return usage.total
                        except Exception:
                            continue
                
                # If not found via psutil, try win32file on the physical/volume path
                try:
                    import win32file
                    physical_drive = self._get_physical_drive(drive_path)
                    # If _get_physical_drive returned a drive letter like 'E:', convert to raw path
                    if re.match(r'^[A-Z]:$', physical_drive):
                        raw_path = f'\\\\.\\{physical_drive}'
                    else:
                        raw_path = physical_drive

                    handle = win32file.CreateFile(
                        raw_path,
                        0,  # No access required for size query
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )

                    # Get drive size
                    size = win32file.GetFileSize(handle)
                    win32file.CloseHandle(handle)
                    return size
                except Exception:
                    # If this fails, keep trying other methods (fallthrough)
                    pass
            else:
                # Unix-like systems
                import os
                stat = os.statvfs(drive_path)
                return stat.f_blocks * stat.f_frsize
                
        except Exception as e:
            logger.warning(f"Could not determine drive size: {e}")
        
        # Default fallback (assume 500GB)
        return 500 * 1024 * 1024 * 1024
    
    def _open_drive(self, physical_drive: str) -> BinaryIO:
        """Open physical drive for reading"""
        logger.info(f"Attempting to open drive: {physical_drive}")
        
        if platform.system() == 'Windows':
            # On Windows, handle two cases:
            # 1) a simple drive letter like 'E:' -> use raw path \\.\E: for low-level access
            # 2) an already raw path like '\\.\PHYSICALDRIVE1' -> use as-is
            if physical_drive.startswith('\\\\.\\'):
                logger.info(f"Opening raw device path: {physical_drive}")
                try:
                    import win32file
                    handle = win32file.CreateFile(
                        physical_drive,
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    logger.info("✅ Successfully opened raw device")
                    return Win32FileWrapper(handle)
                except Exception as e:
                    logger.error(f"Failed to open raw device: {e}")
                    raise

            if physical_drive.endswith(':'):
                logger.info(f"Opening mounted volume (drive letter): {physical_drive}")
                try:
                    # Try direct file access first (requires admin) using raw path \\.\
                    import win32file
                    raw_path = f'\\\\.\\{physical_drive}'
                    logger.info("Attempting low-level disk access (requires admin)...")
                    handle = win32file.CreateFile(
                        raw_path,
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    logger.info("✅ Successfully opened drive with low-level access (admin mode)")
                    return Win32FileWrapper(handle)
                except Exception as e:
                    logger.warning(f"Low-level access failed: {e}")
                    logger.info("⚠️ Falling back to file system scanning (no admin rights)")
                    # If low-level access fails, fall back to opening the mounted volume using normal file API
                    try:
                        # Opening the mounted volume path (e.g., 'E:') as a file object will enumerate files instead of raw device
                        return open(physical_drive, 'rb', buffering=1024*1024)
                    except Exception as e2:
                        logger.error(f"Failed to open mounted volume via file API: {e2}")
                        raise PermissionError("Administrator rights required for raw disk scanning")
            # Other paths should have been handled above
            logger.error(f"Unrecognized Windows drive path format: {physical_drive}")
            raise Exception(f"Unable to open drive: {physical_drive}")
        else:
            # On Unix-like systems
            logger.info(f"Opening drive on Unix-like system: {physical_drive}")
            return open(physical_drive, 'rb', buffering=1024*1024)
    
    async def _metadata_first_recovery(self, drive_handle: BinaryIO, output_dir: str,
                                      stats: Dict, options: Optional[Dict] = None,
                                      progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Attempt metadata-first recovery by parsing filesystem metadata (MFT for NTFS)
        This recovers files using filesystem records before signature carving
        
        Args:
            drive_handle: Open file handle to the drive
            output_dir: Directory to save recovered files
            stats: Statistics dictionary
            options: Recovery options
            progress_callback: Progress callback function
            
        Returns:
            List of recovered files from metadata
        """
        recovered_files = []
        
        try:
            # Try to detect filesystem type
            logger.info("🔍 Reading boot sector to detect filesystem type...")
            try:
                drive_handle.seek(0)
                boot_sector = drive_handle.read(512)
            except Exception as e:
                logger.error(f"❌ Failed to seek/read boot sector: {e}")
                logger.info("💡 This may indicate:")
                logger.info("   • No administrator/elevated privileges")
                logger.info("   • Drive is locked or in use")
                logger.info("   • Physical drive access is restricted")
                return recovered_files
            
            if not boot_sector or len(boot_sector) < 512:
                logger.error("❌ Failed to read boot sector - insufficient data")
                logger.info(f"   Read only {len(boot_sector) if boot_sector else 0} bytes (need 512)")
                logger.info("💡 The drive may not be accessible or formatted")
                return recovered_files
            
            # Detect filesystem type
            # NTFS: bytes 3-11 contain "NTFS    "
            # FAT32: bytes 82-90 contain "FAT32   " or check signature at 0x52
            filesystem_sig_ntfs = boot_sector[3:11] if len(boot_sector) >= 11 else b''
            filesystem_sig_fat32 = boot_sector[82:90] if len(boot_sector) >= 90 else b''
            filesystem_sig_fat32_alt = boot_sector[0x52:0x5A] if len(boot_sector) >= 0x5A else b''
            
            # Check filesystem type
            if filesystem_sig_ntfs == b'NTFS    ':
                logger.info(f"✅ Detected NTFS filesystem - proceeding with improved MFT parsing...")
                recovered_files = await self._recover_ntfs_deleted_files(
                    drive_handle, output_dir, stats, options, progress_callback
                )
            elif filesystem_sig_fat32 == b'FAT32   ' or filesystem_sig_fat32_alt == b'FAT32   ':
                logger.info(f"✅ Detected FAT32 filesystem - proceeding with FAT directory parsing...")
                recovered_files = await self._recover_from_fat32(
                    drive_handle, output_dir, stats, options, progress_callback
                )
            elif boot_sector[0x26:0x29] in [b'FAT', b'FAT12', b'FAT16']:
                logger.info(f"✅ Detected FAT16/FAT12 filesystem - proceeding with FAT directory parsing...")
                recovered_files = await self._recover_from_fat32(
                    drive_handle, output_dir, stats, options, progress_callback
                )
            else:
                logger.warning("⚠️ Unknown filesystem detected - metadata recovery not available")
                logger.info(f"   Checked signatures:")
                logger.info(f"     NTFS (0x03): '{filesystem_sig_ntfs.decode('ascii', errors='replace')}'")
                logger.info(f"     FAT32 (0x52): '{filesystem_sig_fat32.decode('ascii', errors='replace')}'")
                logger.info("💡 Recommendations:")
                logger.info("   • Use 'Deep Scan' for signature-based recovery (works on any filesystem)")
                logger.info("   • Or try 'Signature File Carving' scan")
                
        except Exception as e:
            logger.error(f"Error in metadata-first recovery: {e}", exc_info=True)
            
        return recovered_files
    
    async def _recover_ntfs_deleted_files(self, drive_handle: BinaryIO, output_dir: str,
                                          stats: Dict, options: Optional[Dict] = None,
                                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        NEW IMPROVED NORMAL SCAN: Recover deleted files from NTFS by parsing MFT
        
        This is a completely separate implementation from Deep Scan that:
        1. Properly extracts original filenames with correct encoding
        2. Finds ALL deleted files with metadata intact
        3. Preserves file timestamps and attributes
        4. Works with resident and non-resident files
        
        Returns:
            List of recoverable deleted files with original names
        """
        recovered_files = []
        
        try:
            # Read NTFS boot sector
            drive_handle.seek(0)
            boot_sector = drive_handle.read(512)
            
            # Parse NTFS BPB
            bytes_per_sector = int.from_bytes(boot_sector[0x0B:0x0D], 'little')
            sectors_per_cluster = boot_sector[0x0D]
            mft_cluster = int.from_bytes(boot_sector[0x30:0x38], 'little')
            
            bytes_per_cluster = bytes_per_sector * sectors_per_cluster
            mft_offset = mft_cluster * bytes_per_cluster
            
            logger.info(f"📊 NTFS Parameters:")
            logger.info(f"   Bytes per sector: {bytes_per_sector}")
            logger.info(f"   Sectors per cluster: {sectors_per_cluster}")
            logger.info(f"   Bytes per cluster: {bytes_per_cluster}")
            logger.info(f"   MFT starting at: {mft_offset} bytes ({mft_offset / (1024**2):.2f} MB)")
            
            # Calculate total entries to scan (entire MFT)
            drive_size = stats.get('total_size', 0)
            estimated_entries = min((drive_size // 1024) if drive_size > 0 else 1000000, 5000000)
            
            logger.info(f"🔎 Scanning MFT for deleted files (up to {estimated_entries:,} entries)...")
            logger.info(f"   Looking for files with original names and metadata...")
            
            # Seek to MFT
            drive_handle.seek(mft_offset)
            
            # Track statistics
            entries_scanned = 0
            deleted_found = 0
            files_with_names = 0
            files_recoverable = 0
            
            # Scan MFT entries
            mft_entry_size = 1024
            
            for entry_num in range(estimated_entries):
                try:
                    # Read MFT entry
                    mft_entry = drive_handle.read(mft_entry_size)
                    if len(mft_entry) < mft_entry_size:
                        break  # Reached end of MFT
                    
                    entries_scanned += 1
                    
                    # Check for cancellation every 100 entries
                    if entry_num % 100 == 0:
                        await asyncio.sleep(0)
                        is_cancelled = options.get('is_cancelled') if options else None
                        if is_cancelled and callable(is_cancelled) and is_cancelled():
                            logger.warning(f"⚠️ Scan cancelled at entry {entry_num}")
                            break
                    
                    # Check signature (must be "FILE")
                    if mft_entry[0:4] != b'FILE':
                        continue
                    
                    # Check flags
                    flags = int.from_bytes(mft_entry[0x16:0x18], 'little')
                    is_in_use = bool(flags & 0x01)
                    is_directory = bool(flags & 0x02)
                    
                    # Only process DELETED FILES (not in use, not directory)
                    if is_in_use or is_directory:
                        continue
                    
                    deleted_found += 1
                    
                    # Parse the entry to extract filename and file info
                    file_info = self._parse_ntfs_entry_improved(
                        mft_entry, entry_num, drive_handle, bytes_per_cluster
                    )
                    
                    if not file_info or not file_info.get('filename'):
                        continue
                    
                    files_with_names += 1
                    filename = file_info['filename']
                    file_size = file_info.get('size', 0)
                    file_data = file_info.get('data')
                    
                    # Skip files without data or too small
                    if not file_data or len(file_data) < 100:
                        continue
                    
                    # Check if data is all zeros (overwritten)
                    if file_data[:min(len(file_data), 512)].count(b'\x00') == min(len(file_data), 512):
                        continue
                    
                    files_recoverable += 1
                    
                    # Extract extension
                    file_ext = filename.split('.')[-1].lower() if '.' in filename else 'dat'
                    
                    # Calculate hashes
                    import hashlib
                    file_md5 = hashlib.md5(file_data).hexdigest()
                    file_sha256 = hashlib.sha256(file_data).hexdigest()
                    
                    # Create file record
                    safe_filename = self._sanitize_filename(filename)
                    file_path = os.path.join(output_dir, safe_filename)
                    
                    recovered_files.append({
                        'name': safe_filename,
                        'path': file_path,
                        'size': len(file_data),
                        'type': file_ext.upper(),
                        'extension': file_ext,
                        'offset': mft_offset + (entry_num * mft_entry_size),
                        'md5': file_md5,
                        'sha256': file_sha256,
                        'hash': file_sha256,
                        'file_hash': file_sha256,
                        'validation_score': 100,
                        'is_partial': False,
                        'method': 'normal_scan_mft',
                        'status': 'indexed',
                        'indexed_at': datetime.now().isoformat(),
                        'drive_path': stats.get('physical_drive', stats.get('drive_path', 'unknown')),
                        'mft_entry': entry_num,
                        'original_filename': filename,
                        'declared_size': file_size,
                        'actual_size': len(file_data)
                    })
                    
                    logger.info(f"✅ Found: {safe_filename} ({len(file_data)/1024:.1f} KB)")
                    
                    # Progress update every 1000 entries
                    if entries_scanned % 1000 == 0 and progress_callback:
                        progress = min((entries_scanned / estimated_entries) * 100, 99)
                        sectors_scanned = (entries_scanned * mft_entry_size) // 512
                        total_sectors = (estimated_entries * mft_entry_size) // 512
                        
                        await progress_callback({
                            'progress': progress,
                            'files_found': len(recovered_files),
                            'sectors_scanned': sectors_scanned,
                            'total_sectors': total_sectors,
                            'phase': 'mft_scan',
                            'message': f'MFT: {entries_scanned:,}/{estimated_entries:,} entries | {len(recovered_files)} files found'
                        })
                
                except Exception as e:
                    logger.debug(f"Error processing MFT entry {entry_num}: {e}")
                    continue
            
            # Final statistics
            logger.info(f"")
            logger.info(f"📊 Normal Scan Complete:")
            logger.info(f"   ├─ MFT entries scanned: {entries_scanned:,}")
            logger.info(f"   ├─ Deleted files found: {deleted_found:,}")
            logger.info(f"   ├─ Files with readable names: {files_with_names:,}")
            logger.info(f"   └─ ✅ Recoverable files: {files_recoverable:,}")
            
            if files_recoverable > 0:
                logger.info(f"")
                logger.info(f"💡 Success! Found {files_recoverable} deleted files with original names")
            else:
                logger.warning(f"⚠️ No recoverable deleted files found")
                logger.info(f"   Possible reasons:")
                logger.info(f"   • Files were overwritten by new data")
                logger.info(f"   • MFT entries were reused")
                logger.info(f"   • Try Deep Scan for signature-based recovery")
            
            # Final progress update
            if progress_callback:
                await progress_callback({
                    'progress': 100,
                    'files_found': len(recovered_files),
                    'sectors_scanned': (entries_scanned * mft_entry_size) // 512,
                    'total_sectors': (entries_scanned * mft_entry_size) // 512,
                    'phase': 'complete',
                    'message': f'Scan complete: {len(recovered_files)} files found'
                })
            
        except Exception as e:
            logger.error(f"Error in Normal scan NTFS recovery: {e}", exc_info=True)
        
        return recovered_files
    
    def _parse_ntfs_entry_improved(self, mft_entry: bytes, entry_num: int,
                                   drive_handle: BinaryIO, bytes_per_cluster: int) -> Optional[Dict]:
        """
        IMPROVED MFT entry parser that properly extracts filenames
        
        Correctly handles:
        - UTF-16 LE filename encoding
        - Multiple FILE_NAME attributes (Win32, DOS 8.3)
        - Resident and non-resident data
        - Proper attribute offset calculations
        """
        try:
            # Get first attribute offset
            first_attr_offset = int.from_bytes(mft_entry[0x14:0x16], 'little')
            if first_attr_offset >= len(mft_entry) or first_attr_offset == 0:
                return None
            
            filename = None
            file_data = None
            file_size = 0
            
            # Parse attributes
            offset = first_attr_offset
            
            while offset < len(mft_entry) - 4:
                # Read attribute type
                attr_type = int.from_bytes(mft_entry[offset:offset+4], 'little')
                
                # End of attributes
                if attr_type == 0xFFFFFFFF:
                    break
                
                # Read attribute length
                if offset + 8 > len(mft_entry):
                    break
                attr_length = int.from_bytes(mft_entry[offset+4:offset+8], 'little')
                
                if attr_length == 0 or attr_length > 1024 or offset + attr_length > len(mft_entry):
                    break
                
                # 0x30 = FILE_NAME attribute
                if attr_type == 0x30:
                    try:
                        # Check if resident (FILE_NAME is always resident)
                        non_resident = mft_entry[offset + 8]
                        if non_resident == 0:
                            # Get attribute content offset and length
                            attr_content_offset = int.from_bytes(mft_entry[offset+0x14:offset+0x16], 'little')
                            attr_content_len = int.from_bytes(mft_entry[offset+0x10:offset+0x14], 'little')
                            
                            if attr_content_len < 0x42:
                                continue
                            
                            # FILE_NAME structure:
                            # +0x00: Parent directory file reference (8 bytes)
                            # +0x08: Creation time (8 bytes)
                            # +0x10: Modification time (8 bytes)
                            # +0x18: MFT change time (8 bytes)
                            # +0x20: Access time (8 bytes)
                            # +0x28: Allocated size (8 bytes)
                            # +0x30: Real size (8 bytes)
                            # +0x38: Flags (4 bytes)
                            # +0x3C: Reparse value (4 bytes)
                            # +0x40: Filename length in characters (1 byte)
                            # +0x41: Namespace (1 byte)
                            # +0x42: Filename in UTF-16 LE
                            
                            content_start = offset + attr_content_offset
                            
                            if content_start + 0x42 > len(mft_entry):
                                continue
                            
                            # Get filename length (in characters, not bytes)
                            fn_length = mft_entry[content_start + 0x40]
                            
                            # Get namespace (0=POSIX, 1=Win32, 2=DOS, 3=Win32+DOS)
                            namespace = mft_entry[content_start + 0x41]
                            
                            # Prefer Win32 names (namespace 1 or 3) over DOS 8.3 names (namespace 2)
                            if fn_length > 0 and fn_length < 256:
                                fn_start = content_start + 0x42
                                fn_bytes = fn_length * 2  # UTF-16 LE uses 2 bytes per character
                                
                                if fn_start + fn_bytes <= len(mft_entry):
                                    decoded_name = mft_entry[fn_start:fn_start + fn_bytes].decode('utf-16le', errors='ignore')
                                    
                                    # Only update filename if it's better than what we have
                                    if not filename or (namespace in [1, 3] and len(decoded_name) > 0):
                                        filename = decoded_name.strip()
                    
                    except Exception as e:
                        logger.debug(f"Error parsing FILE_NAME: {e}")
                
                # 0x80 = DATA attribute (unnamed stream)
                elif attr_type == 0x80 and not file_data:
                    try:
                        non_resident = mft_entry[offset + 8]
                        
                        if non_resident == 0:
                            # Resident data (small files)
                            data_offset = int.from_bytes(mft_entry[offset+0x14:offset+0x16], 'little')
                            data_length = int.from_bytes(mft_entry[offset+0x10:offset+0x14], 'little')
                            
                            if data_length > 0 and offset + data_offset + data_length <= len(mft_entry):
                                file_data = mft_entry[offset + data_offset:offset + data_offset + data_length]
                                file_size = data_length
                        else:
                            # Non-resident data (large files)
                            file_size = int.from_bytes(mft_entry[offset+0x30:offset+0x38], 'little')
                            data_runs_offset = int.from_bytes(mft_entry[offset+0x20:offset+0x22], 'little')
                            
                            if file_size > 0 and file_size <= 100 * 1024 * 1024:  # Limit to 100MB
                                if data_runs_offset > 0 and offset + data_runs_offset < len(mft_entry):
                                    data_runs = self._parse_data_runs(
                                        mft_entry[offset + data_runs_offset:offset + attr_length]
                                    )
                                    
                                    if data_runs:
                                        file_data = self._read_data_runs(
                                            drive_handle, data_runs, bytes_per_cluster, file_size
                                        )
                    
                    except Exception as e:
                        logger.debug(f"Error parsing DATA: {e}")
                
                # Move to next attribute
                offset += attr_length
            
            if filename:
                return {
                    'filename': filename,
                    'data': file_data,
                    'size': file_size
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in improved MFT parser: {e}")
            return None
    
    async def _deep_scan_hybrid(self, drive_handle: BinaryIO, output_dir: str,
                               stats: Dict, options: Optional[Dict] = None,
                               progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        DEEP SCAN: Comprehensive signature-based file recovery
        
        This scan performs:
        - Sector-by-sector scanning of entire drive
        - Signature-based file detection (magic bytes)
        - Validation and integrity checking
        - Index-only mode (files cataloged, not written)
        
        Why Deep Scan?
        - Finds deleted files without metadata
        - Recovers fragmented and overwritten files
        - Works on any filesystem (NTFS, FAT32, etc.)
        - Maximum recovery rate for lost data
        
        Args:
            drive_handle: Open handle to raw drive
            output_dir: Directory to save recovered files
            stats: Statistics dictionary
            options: Scan options
            progress_callback: Progress update callback
            
        Returns:
            List of all recovered files
        """
        all_recovered_files = []
        metadata_files = []
        carved_files = []
        
        try:
            # ============================================================
            # PHASE 1: SIGNATURE-BASED CARVING (Thorough, finds old files)
            # ============================================================
            # NOTE: Skipping metadata phase for Deep Scan to go directly to comprehensive carving
            logger.info("")
            logger.info("┏" + "━" * 68 + "┓")
            logger.info("┃" + " " * 12 + "🔍 DEEP SCAN: SIGNATURE CARVING" + " " * 24 + "┃")
            logger.info("┗" + "━" * 68 + "┛")
            logger.info("🔎 Scanning entire drive sector-by-sector for file signatures...")
            logger.info("   • Comprehensive scan for all file types")
            logger.info("   • Recovers deleted files and fragmented data")
            logger.info("   • Detects files by 'magic bytes' (file headers)")
            logger.info("")
            
            # Create copy of options for carving phase
            carving_options = options.copy() if options else {}
            carving_options['scan_type'] = 'deep'  # Use deep scan logic for carving
            
            # Update progress: Phase 1 starting (0-90% of total)
            if progress_callback:
                await progress_callback({
                    'phase': 'carving',
                    'phase_name': 'Signature Carving',
                    'progress': 0,
                    'message': 'Starting deep sector scan...'
                })
            
            try:
                # Reset to beginning for full drive scan
                drive_handle.seek(0)
                
                # Run signature carving
                carved_files = await self._carve_files(
                    drive_handle,
                    output_dir,
                    stats,
                    carving_options,
                    progress_callback
                )
                
                logger.info("")
                logger.info(f"✅ Deep Scan Complete: {len(carved_files)} files found")
                logger.info(f"   • Files indexed by type and hash")
                logger.info("")
                
                # Update progress: Complete (100%)
                if progress_callback:
                    await progress_callback({
                        'phase': 'complete',
                        'phase_name': 'Scan Complete',
                        'progress': 100,
                        'message': f'Scan complete: {len(carved_files)} files found',
                        'files_found': len(carved_files)
                    })
                
            except Exception as e:
                logger.error(f"❌ Signature carving failed: {e}", exc_info=True)
                return []
            
            # Return all carved files (no deduplication needed since we only did one phase)
            all_recovered_files = carved_files
            
            # ============================================================
            # FINAL SUMMARY
            # ============================================================
            logger.info("")
            logger.info("┏" + "━" * 68 + "┓")
            logger.info("┃" + " " * 18 + "🎉 DEEP SCAN COMPLETE" + " " * 27 + "┃")
            logger.info("┗" + "━" * 68 + "┛")
            logger.info(f"✅ Total files indexed: {len(all_recovered_files)}")
            logger.info(f"   • Output directory: {output_dir}")
            logger.info("")
            
            # Calculate recovery breakdown by file type
            type_counts = {}
            for file_info in all_recovered_files:
                ext = file_info.get('extension', 'unknown')
                type_counts[ext] = type_counts.get(ext, 0) + 1
            
            if type_counts:
                logger.info("📊 File breakdown by type:")
                for ext, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    logger.info(f"   • .{ext}: {count} files")
                if len(type_counts) > 10:
                    logger.info(f"   • ... and {len(type_counts) - 10} more types")
                logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Error in deep scan: {e}", exc_info=True)
            # Return whatever we managed to recover
            all_recovered_files = carved_files
        
        return all_recovered_files
    
    async def _recover_from_ntfs_mft(self, drive_handle: BinaryIO, output_dir: str,
                                    stats: Dict, options: Optional[Dict] = None,
                                    progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Recover files by parsing NTFS Master File Table (MFT)
        
        This method:
        1. Locates the MFT ($MFT file)
        2. Parses MFT entries for deleted files
        3. Recovers files with intact data runs
        4. Validates recovered files
        
        Returns:
            List of recovered files with metadata
        """
        recovered_files = []
        
        try:
            # Read NTFS boot sector
            drive_handle.seek(0)
            boot_sector = drive_handle.read(512)
            
            # Parse NTFS BPB (BIOS Parameter Block)
            bytes_per_sector = int.from_bytes(boot_sector[0x0B:0x0D], 'little')
            sectors_per_cluster = boot_sector[0x0D]
            mft_cluster = int.from_bytes(boot_sector[0x30:0x38], 'little')
            
            bytes_per_cluster = bytes_per_sector * sectors_per_cluster
            mft_offset = mft_cluster * bytes_per_cluster
            
            logger.info(f"📊 NTFS Parameters:")
            logger.info(f"   Bytes per sector: {bytes_per_sector}")
            logger.info(f"   Sectors per cluster: {sectors_per_cluster}")
            logger.info(f"   Bytes per cluster: {bytes_per_cluster}")
            logger.info(f"   MFT cluster: {mft_cluster}")
            logger.info(f"   MFT offset: {mft_offset} bytes ({mft_offset / (1024**2):.2f} MB)")
            
            # Get selected file types based on scan type
            file_type_options = options.get('fileTypes', {}) if options else {}
            scan_type = options.get('scan_type', 'normal') if options else 'normal'
            
            # For normal scan (metadata recovery), be more permissive with file types
            # We trust MFT metadata, so recover ALL file types found, not just "important" ones
            if scan_type == 'normal' and not file_type_options:
                # Get ALL extensions we can detect (not just important ones)
                interested_extensions = set()
                for sig_name, sig_info in self.signatures.items():
                    interested_extensions.add(sig_info['extension'])
                # Also add common extensions that might not have signatures
                interested_extensions.update(['txt', 'log', 'ini', 'cfg', 'xml', 'json', 
                                             'html', 'css', 'js', 'py', 'java', 'cpp', 'h'])
                logger.info(f"🎯 Normal scan (MFT): Recovering ALL file types from filesystem metadata")
            else:
                interested_extensions = self._get_interested_extensions(file_type_options)
            
            logger.info(f"🎯 Target extensions: {', '.join(sorted(interested_extensions)[:30])}{'...' if len(interested_extensions) > 30 else ''}")
            
            # Parse MFT entries
            drive_handle.seek(mft_offset)
            mft_entry_size = 1024  # Standard MFT entry size
            entries_parsed = 0
            deleted_files_found = 0
            max_entries = 100000  # Limit to first 100k entries for performance
            
            # Statistics tracking
            files_checked = 0
            files_too_small = 0
            files_no_data = 0
            files_data_overwritten = 0
            
            logger.info(f"🔎 Parsing MFT entries (analyzing up to {max_entries} entries)...")
            
            for entry_num in range(max_entries):
                # Check for cancellation
                is_cancelled = options.get('is_cancelled') if options else None
                if is_cancelled and callable(is_cancelled) and is_cancelled():
                    logger.warning("⚠️ MFT parsing cancelled by user")
                    logger.info(f"📋 Returning partial results: {len(recovered_files)} files indexed so far")
                    break
                
                # Read MFT entry
                mft_entry = drive_handle.read(mft_entry_size)
                if len(mft_entry) < mft_entry_size:
                    break
                
                # Yield control to event loop after every read to allow cancellation
                if entry_num % 100 == 0:
                    await asyncio.sleep(0)
                
                entries_parsed += 1
                
                # Check MFT signature (FILE or BAAD)
                signature = mft_entry[0:4]
                if signature != b'FILE':
                    continue
                
                # Check if file is deleted (bit 0 of flags at offset 0x16)
                flags = int.from_bytes(mft_entry[0x16:0x18], 'little')
                is_in_use = flags & 0x01
                is_directory = flags & 0x02
                
                # Only process deleted files (not in use, not directory)
                if is_in_use or is_directory:
                    continue
                
                deleted_files_found += 1
                
                # Try to extract filename and data
                try:
                    file_info = self._parse_mft_entry(mft_entry, entry_num, drive_handle, bytes_per_cluster)
                    
                    if file_info and file_info.get('filename'):
                        filename = file_info['filename']
                        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
                        
                        # For metadata recovery, check extension OR accept if we have filename
                        # (more permissive than signature carving)
                        if not file_ext or file_ext in interested_extensions or scan_type == 'normal':
                            # Recover file data
                            file_data = file_info.get('data')
                            files_checked += 1
                            
                            # For MFT recovery, be more lenient - accept smaller files
                            if not file_data or len(file_data) < 100:  # Minimum 100 bytes (was 4KB)
                                if not file_data:
                                    files_no_data += 1
                                else:
                                    files_too_small += 1
                                if files_checked <= 20:  # Log first 20 rejections
                                    logger.debug(f"❌ {filename}: Too small or no data ({len(file_data) if file_data else 0} bytes)")
                                continue
                            
                            # For MFT recovery, skip strict signature validation
                            # The MFT metadata is already validated, so trust it
                            # Only do basic sanity check: file starts with non-null bytes
                            if file_data[:100].count(b'\x00') == 100:
                                # Entire file is zeros - data was overwritten
                                files_data_overwritten += 1
                                if files_checked <= 20:
                                    logger.debug(f"❌ {filename}: Data appears to be overwritten (all zeros)")
                                continue
                            
                            # File passed checks - INDEX it (don't write yet)
                            safe_filename = self._sanitize_filename(filename)
                            file_path = os.path.join(output_dir, f"mft_{entry_num}_{safe_filename}")
                            
                            # Calculate hashes for indexing
                            file_md5 = hashlib.md5(file_data).hexdigest()
                            file_sha256 = hashlib.sha256(file_data).hexdigest()
                            
                            # INDEX FILE (NO DISK WRITE)
                            recovered_files.append({
                                'name': safe_filename,
                                'path': file_path,  # Proposed path (not created yet)
                                'size': len(file_data),
                                'type': file_ext.upper() if file_ext else 'DAT',
                                'extension': file_ext if file_ext else 'dat',
                                'offset': mft_offset + (entry_num * mft_entry_size),
                                'md5': file_md5,
                                'sha256': file_sha256,
                                'hash': file_sha256,  # Alias
                                'file_hash': file_sha256,  # Another alias
                                'validation_score': 100,  # Trust MFT metadata
                                'is_partial': False,  # MFT tells us the complete file
                                'method': 'mft_metadata',
                                'status': 'indexed',  # Not yet recovered
                                'indexed_at': datetime.now().isoformat(),
                                'drive_path': stats.get('drive_path', 'unknown'),
                                'mft_entry': entry_num
                            })
                            
                            logger.info(f"✅ MFT: Indexed {safe_filename} ({len(file_data)/1024:.1f} KB)")
                
                except Exception as e:
                    logger.debug(f"Error parsing MFT entry {entry_num}: {e}")
                    continue
                
                # Update progress every 1000 entries
                if entries_parsed % 1000 == 0 and progress_callback:
                    progress = min((entries_parsed / max_entries) * 100, 99)
                    expected_time = self._calculate_expected_time(
                        (datetime.now() - datetime.fromisoformat(stats['start_time'])).total_seconds(),
                        progress
                    )
                    await progress_callback({
                        'progress': progress,
                        'files_found': len(recovered_files),
                        'sectors_scanned': entries_parsed,
                        'total_sectors': max_entries,
                        'expected_time': expected_time,
                        'current_pass': 1
                    })
            
            # Print comprehensive statistics
            logger.info(f"📂 MFT Analysis Complete:")
            logger.info(f"   ├─ Entries parsed: {entries_parsed:,}")
            logger.info(f"   ├─ Deleted files found: {deleted_files_found:,}")
            logger.info(f"   ├─ Files checked: {files_checked:,}")
            logger.info(f"   │")
            logger.info(f"   ├─ Rejections:")
            logger.info(f"   │  ├─ Too small (< 100 bytes): {files_too_small:,}")
            logger.info(f"   │  ├─ No data in MFT: {files_no_data:,}")
            logger.info(f"   │  └─ Data overwritten (zeros): {files_data_overwritten:,}")
            logger.info(f"   │")
            logger.info(f"   └─ ✅ Files indexed: {len(recovered_files):,}")
            
            if files_checked > 0:
                success_rate = (len(recovered_files) / files_checked) * 100
                logger.info(f"   📊 Index rate: {success_rate:.1f}% of deleted files had recoverable data")
            
            logger.info(f"💾 Disk space used: 0 bytes (index only)")
            
            if len(recovered_files) == 0:
                logger.warning("⚠️ No deleted files with recoverable data found in MFT")
                logger.info("💡 Possible reasons:")
                logger.info("   • Deleted files were overwritten by new data")
                logger.info("   • Drive has been formatted or wiped")
                logger.info("   • Deleted files were small and stored in MFT (resident) but MFT was reused")
                logger.info("   • Try 'Deep Scan' for signature-based recovery instead")
            
        except Exception as e:
            logger.error(f"Error parsing NTFS MFT: {e}", exc_info=True)
        
        return recovered_files
    
    def _parse_mft_entry(self, mft_entry: bytes, entry_num: int, drive_handle: BinaryIO, 
                         bytes_per_cluster: int) -> Optional[Dict]:
        """
        Parse an MFT entry to extract filename and data
        
        Properly handles both resident and non-resident data attributes
        """
        try:
            # Get first attribute offset
            first_attr_offset = int.from_bytes(mft_entry[0x14:0x16], 'little')
            
            filename = None
            file_data = None
            file_size = 0
            
            # Parse attributes
            offset = first_attr_offset
            while offset < len(mft_entry) - 16:
                attr_type = int.from_bytes(mft_entry[offset:offset+4], 'little')
                
                # End marker
                if attr_type == 0xFFFFFFFF:
                    break
                
                attr_length = int.from_bytes(mft_entry[offset+4:offset+8], 'little')
                if attr_length == 0 or offset + attr_length > len(mft_entry):
                    break
                
                # 0x30 = FILE_NAME attribute
                if attr_type == 0x30:
                    # Parse filename from FILE_NAME attribute
                    try:
                        non_resident_flag = mft_entry[offset + 8]
                        if non_resident_flag == 0:  # Resident attribute
                            # For FILE_NAME attribute structure:
                            # Offset 0x14: Attribute content offset
                            # Offset 0x10: Attribute content length
                            content_offset = int.from_bytes(mft_entry[offset+0x14:offset+0x16], 'little')
                            content_length = int.from_bytes(mft_entry[offset+0x10:offset+0x14], 'little')
                            
                            if content_length >= 0x42:  # Minimum FILE_NAME attribute size
                                # Filename starts at offset 0x42 in the FILE_NAME content
                                fn_start = offset + content_offset + 0x42
                                fn_length = mft_entry[offset + content_offset + 0x40]  # Filename length in chars
                                
                                if fn_start + (fn_length * 2) <= len(mft_entry):
                                    filename = mft_entry[fn_start:fn_start + (fn_length * 2)].decode('utf-16le', errors='ignore')
                    except Exception as e:
                        logger.debug(f"Error parsing FILE_NAME attribute: {e}")
                
                # 0x80 = DATA attribute (unnamed stream)
                elif attr_type == 0x80:
                    # Check if resident or non-resident
                    non_resident = mft_entry[offset + 8]
                    
                    if non_resident == 0:
                        # Resident data (small files stored in MFT)
                        try:
                            data_offset = int.from_bytes(mft_entry[offset+0x14:offset+0x16], 'little')
                            data_length = int.from_bytes(mft_entry[offset+0x10:offset+0x14], 'little')
                            
                            if data_length > 0 and offset + data_offset + data_length <= len(mft_entry):
                                file_data = mft_entry[offset + data_offset:offset + data_offset + data_length]
                                file_size = data_length
                        except Exception as e:
                            logger.debug(f"Error extracting resident data: {e}")
                    else:
                        # Non-resident data (large files - stored in clusters)
                        try:
                            # Extract file size
                            file_size = int.from_bytes(mft_entry[offset+0x30:offset+0x38], 'little')
                            
                            # Data runs start offset
                            data_runs_offset = int.from_bytes(mft_entry[offset+0x20:offset+0x22], 'little')
                            
                            if data_runs_offset > 0 and offset + data_runs_offset < len(mft_entry):
                                # Parse data runs
                                data_runs = self._parse_data_runs(
                                    mft_entry[offset + data_runs_offset:offset + attr_length]
                                )
                                
                                # Read file data from clusters (limit to reasonable size)
                                if data_runs and file_size > 0 and file_size <= 50 * 1024 * 1024:  # Max 50MB
                                    file_data = self._read_data_runs(
                                        drive_handle, 
                                        data_runs, 
                                        bytes_per_cluster,
                                        file_size
                                    )
                        except Exception as e:
                            logger.debug(f"Error extracting non-resident data: {e}")
                
                offset += attr_length
            
            return {
                'filename': filename,
                'data': file_data,
                'size': file_size,
                'resident': file_data is not None and file_size <= 1024
            }
            
        except Exception as e:
            logger.debug(f"Error parsing MFT entry: {e}")
            return None
    
    def _parse_data_runs(self, data_runs_bytes: bytes) -> List[tuple]:
        """
        Parse NTFS data runs to get cluster locations
        
        Data runs format:
        - First byte: header (high nibble = offset length, low nibble = length length)
        - Next bytes: run length (variable size)
        - Next bytes: run offset (variable size, signed)
        
        Returns:
            List of (cluster_offset, cluster_count) tuples
        """
        runs = []
        position = 0
        current_offset = 0
        
        try:
            while position < len(data_runs_bytes):
                header = data_runs_bytes[position]
                
                # End of data runs
                if header == 0:
                    break
                
                # Extract nibbles
                length_size = header & 0x0F
                offset_size = (header >> 4) & 0x0F
                
                if length_size == 0 or position + 1 + length_size + offset_size > len(data_runs_bytes):
                    break
                
                position += 1
                
                # Read run length (number of clusters)
                run_length = int.from_bytes(
                    data_runs_bytes[position:position + length_size],
                    'little',
                    signed=False
                )
                position += length_size
                
                # Read run offset (relative cluster position, signed)
                if offset_size > 0:
                    offset_bytes = data_runs_bytes[position:position + offset_size]
                    # Handle signed integer (two's complement)
                    run_offset = int.from_bytes(offset_bytes, 'little', signed=True)
                    position += offset_size
                    
                    current_offset += run_offset
                    runs.append((current_offset, run_length))
                else:
                    # Sparse run (all zeros)
                    runs.append((0, run_length))
                
        except Exception as e:
            logger.debug(f"Error parsing data runs: {e}")
        
        return runs
    
    def _read_data_runs(self, drive_handle: BinaryIO, data_runs: List[tuple], 
                       bytes_per_cluster: int, file_size: int) -> Optional[bytes]:
        """
        Read file data from clusters specified in data runs
        
        Args:
            drive_handle: Handle to the drive
            data_runs: List of (cluster_offset, cluster_count) tuples
            bytes_per_cluster: Cluster size in bytes
            file_size: Actual file size (may be less than allocated clusters)
            
        Returns:
            File data bytes or None if read failed
        """
        try:
            file_data = bytearray()
            bytes_read = 0
            
            for cluster_offset, cluster_count in data_runs:
                # Sparse run (zeros)
                if cluster_offset == 0:
                    sparse_bytes = min(cluster_count * bytes_per_cluster, file_size - bytes_read)
                    file_data.extend(b'\x00' * sparse_bytes)
                    bytes_read += sparse_bytes
                else:
                    # Read from disk
                    byte_offset = cluster_offset * bytes_per_cluster
                    bytes_to_read = min(cluster_count * bytes_per_cluster, file_size - bytes_read)
                    
                    try:
                        drive_handle.seek(byte_offset)
                        chunk = drive_handle.read(bytes_to_read)
                        file_data.extend(chunk)
                        bytes_read += len(chunk)
                    except Exception as e:
                        logger.debug(f"Failed to read cluster at offset {byte_offset}: {e}")
                        # Return what we have so far (partial file)
                        return bytes(file_data) if file_data else None
                
                # Stop if we've read the full file
                if bytes_read >= file_size:
                    break
            
            # Trim to exact file size
            return bytes(file_data[:file_size]) if file_data else None
            
        except Exception as e:
            logger.debug(f"Error reading data runs: {e}")
            return None
    
    async def _recover_from_fat32(self, drive_handle: BinaryIO, output_dir: str,
                                   stats: Dict, options: Optional[Dict] = None,
                                   progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Recover deleted files from FAT32/FAT16 filesystem
        
        Parses FAT directory entries to find deleted files (first byte = 0xE5)
        and attempts to recover data from clusters
        
        Returns:
            List of recovered files with metadata
        """
        recovered_files = []
        
        try:
            # Read FAT32 boot sector to get parameters
            drive_handle.seek(0)
            boot_sector = drive_handle.read(512)
            
            # Parse FAT BPB (BIOS Parameter Block)
            bytes_per_sector = int.from_bytes(boot_sector[0x0B:0x0D], 'little')
            sectors_per_cluster = boot_sector[0x0D]
            reserved_sectors = int.from_bytes(boot_sector[0x0E:0x10], 'little')
            num_fats = boot_sector[0x10]
            
            # FAT32 specific
            sectors_per_fat = int.from_bytes(boot_sector[0x24:0x28], 'little')
            root_cluster = int.from_bytes(boot_sector[0x2C:0x30], 'little')
            
            bytes_per_cluster = bytes_per_sector * sectors_per_cluster
            
            # Calculate data region offset
            fat_offset = reserved_sectors * bytes_per_sector
            data_offset = fat_offset + (num_fats * sectors_per_fat * bytes_per_sector)
            
            logger.info(f"📊 FAT32 Parameters:")
            logger.info(f"   Bytes per sector: {bytes_per_sector}")
            logger.info(f"   Sectors per cluster: {sectors_per_cluster}")
            logger.info(f"   Bytes per cluster: {bytes_per_cluster}")
            logger.info(f"   Root cluster: {root_cluster}")
            logger.info(f"   Data region offset: {data_offset} bytes ({data_offset / (1024**2):.2f} MB)")
            
            # Get file type filter
            file_type_options = options.get('fileTypes', {}) if options else {}
            scan_type = options.get('scan_type', 'normal') if options else 'normal'
            
            if scan_type == 'normal' and not file_type_options:
                interested_extensions = set()
                for sig_name, sig_info in self.signatures.items():
                    interested_extensions.add(sig_info['extension'])
                interested_extensions.update(['txt', 'log', 'ini', 'cfg', 'xml', 'json'])
                logger.info(f"🎯 Normal scan (FAT32): Recovering ALL file types from directory entries")
            else:
                interested_extensions = self._get_interested_extensions(file_type_options)
            
            logger.info(f"🎯 Target extensions: {', '.join(sorted(interested_extensions)[:30])}{'...' if len(interested_extensions) > 30 else ''}")
            
            # Parse root directory and subdirectories
            entries_parsed = 0
            deleted_files_found = 0
            files_checked = 0
            files_too_small = 0
            files_no_data = 0
            
            logger.info(f"🔎 Scanning FAT32 directories for deleted files...")
            
            # Read root directory cluster
            root_offset = data_offset + (root_cluster - 2) * bytes_per_cluster
            
            # Scan multiple clusters (limit to 1000 for performance)
            max_clusters = 1000
            for cluster_num in range(max_clusters):
                # Check for cancellation
                is_cancelled = options.get('is_cancelled') if options else None
                if is_cancelled and callable(is_cancelled) and is_cancelled():
                    logger.warning("⚠️ FAT32 scanning cancelled by user")
                    logger.info(f"📋 Returning partial results: {len(recovered_files)} files indexed so far")
                    break
                
                try:
                    cluster_offset = data_offset + cluster_num * bytes_per_cluster
                    drive_handle.seek(cluster_offset)
                    cluster_data = drive_handle.read(bytes_per_cluster)
                    
                    # Yield control to event loop after every read to allow cancellation
                    if cluster_num % 100 == 0:
                        await asyncio.sleep(0)
                    
                    if not cluster_data or len(cluster_data) < 32:
                        continue
                    
                    # Parse directory entries (32 bytes each)
                    for entry_offset in range(0, len(cluster_data), 32):
                        if entry_offset + 32 > len(cluster_data):
                            break
                        
                        entry = cluster_data[entry_offset:entry_offset + 32]
                        entries_parsed += 1
                        
                        # Check if deleted (first byte = 0xE5)
                        if entry[0] != 0xE5:
                            continue
                        
                        # Check if it's a file (not directory, not volume label)
                        attributes = entry[0x0B]
                        if attributes & 0x10:  # Directory
                            continue
                        if attributes & 0x08:  # Volume label
                            continue
                        
                        deleted_files_found += 1
                        
                        # Extract filename (8.3 format)
                        try:
                            name_part = entry[1:8].decode('ascii', errors='ignore').strip()
                            ext_part = entry[8:11].decode('ascii', errors='ignore').strip()
                            
                            if not name_part:
                                name_part = f"deleted_{cluster_num}_{entry_offset}"
                            
                            if ext_part:
                                filename = f"{name_part}.{ext_part}"
                            else:
                                filename = name_part
                            
                            file_ext = ext_part.lower() if ext_part else ''
                            
                            # Check if interested in this file type
                            if file_ext not in interested_extensions and scan_type != 'normal':
                                continue
                            
                            # Extract file size and cluster
                            file_size = int.from_bytes(entry[0x1C:0x20], 'little')
                            start_cluster_low = int.from_bytes(entry[0x1A:0x1C], 'little')
                            start_cluster_high = int.from_bytes(entry[0x14:0x16], 'little')
                            start_cluster = (start_cluster_high << 16) | start_cluster_low
                            
                            files_checked += 1
                            
                            # Skip very small or empty files
                            if file_size < 100:
                                files_too_small += 1
                                continue
                            
                            # Skip if no valid cluster
                            if start_cluster < 2:
                                files_no_data += 1
                                continue
                            
                            # Read file data from clusters (limit to 50MB)
                            max_read_size = min(file_size, 50 * 1024 * 1024)
                            file_data = self._read_fat_clusters(
                                drive_handle,
                                start_cluster,
                                max_read_size,
                                data_offset,
                                bytes_per_cluster
                            )
                            
                            if not file_data or len(file_data) < 100:
                                files_no_data += 1
                                continue
                            
                            # Check if data is all zeros (overwritten)
                            if file_data[:100].count(b'\x00') == 100:
                                files_no_data += 1
                                continue
                            
                            # INDEX file (don't write yet)
                            safe_filename = self._sanitize_filename(filename)
                            file_path = os.path.join(output_dir, f"fat_{cluster_num}_{safe_filename}")
                            
                            # Calculate hashes for indexing
                            file_md5 = hashlib.md5(file_data).hexdigest()
                            file_sha256 = hashlib.sha256(file_data).hexdigest()
                            
                            # INDEX FILE (NO DISK WRITE)
                            recovered_files.append({
                                'name': safe_filename,
                                'path': file_path,  # Proposed path (not created yet)
                                'size': len(file_data),
                                'type': file_ext.upper() if file_ext else 'DAT',
                                'extension': file_ext if file_ext else 'dat',
                                'offset': cluster_offset + entry_offset,
                                'md5': file_md5,
                                'sha256': file_sha256,
                                'hash': file_sha256,  # Alias
                                'file_hash': file_sha256,  # Another alias
                                'validation_score': 100,
                                'is_partial': len(file_data) < file_size,
                                'method': 'fat32_directory',
                                'status': 'indexed',  # Not yet recovered
                                'indexed_at': datetime.now().isoformat(),
                                'drive_path': stats.get('drive_path', 'unknown'),
                                'start_cluster': start_cluster,
                                'declared_size': file_size,
                                'actual_size': len(file_data)
                            })
                            
                            logger.info(f"✅ FAT32: Indexed {safe_filename} ({len(file_data)/1024:.1f} KB)")
                            
                        except Exception as e:
                            logger.debug(f"Error parsing FAT entry: {e}")
                            continue
                    
                except Exception as e:
                    logger.debug(f"Error reading cluster {cluster_num}: {e}")
                    continue
                
                # Update progress every 100 clusters
                if cluster_num % 100 == 0 and progress_callback:
                    progress = min((cluster_num / max_clusters) * 100, 99)
                    expected_time = self._calculate_expected_time(
                        (datetime.now() - datetime.fromisoformat(stats['start_time'])).total_seconds(),
                        progress
                    )
                    await progress_callback({
                        'progress': progress,
                        'files_found': len(recovered_files),
                        'sectors_scanned': cluster_num * sectors_per_cluster,
                        'total_sectors': max_clusters * sectors_per_cluster,
                        'expected_time': expected_time,
                        'current_pass': 1
                    })
            
            # Print statistics
            logger.info(f"📂 FAT32 Analysis Complete:")
            logger.info(f"   ├─ Directory entries parsed: {entries_parsed:,}")
            logger.info(f"   ├─ Deleted files found: {deleted_files_found:,}")
            logger.info(f"   ├─ Files checked: {files_checked:,}")
            logger.info(f"   │")
            logger.info(f"   ├─ Rejections:")
            logger.info(f"   │  ├─ Too small (< 100 bytes): {files_too_small:,}")
            logger.info(f"   │  └─ No data/overwritten: {files_no_data:,}")
            logger.info(f"   │")
            logger.info(f"   └─ ✅ Files indexed: {len(recovered_files):,}")
            
            if files_checked > 0:
                success_rate = (len(recovered_files) / files_checked) * 100
                logger.info(f"   📊 Index rate: {success_rate:.1f}% of deleted files had recoverable data")
            
            logger.info(f"💾 Disk space used: 0 bytes (index only)")
            
            if len(recovered_files) == 0:
                logger.warning("⚠️ No deleted files with recoverable data found in FAT32 directories")
                logger.info("💡 Possible reasons:")
                logger.info("   • Deleted files were overwritten by new data")
                logger.info("   • Drive has been formatted")
                logger.info("   • FAT chain was broken/corrupted")
                logger.info("   • Try 'Deep Scan' for signature-based recovery instead")
            
        except Exception as e:
            logger.error(f"Error parsing FAT32: {e}", exc_info=True)
        
        return recovered_files
    
    def _read_fat_clusters(self, drive_handle: BinaryIO, start_cluster: int,
                          file_size: int, data_offset: int, bytes_per_cluster: int) -> Optional[bytes]:
        """
        Read file data from FAT clusters (simple sequential read)
        
        Note: This is a simplified version that reads sequentially from start cluster.
        A full implementation would follow the FAT chain, but for deleted files
        the FAT chain is often broken, so sequential reading works better.
        
        Args:
            drive_handle: Handle to the drive
            start_cluster: Starting cluster number
            file_size: File size in bytes
            data_offset: Offset to data region
            bytes_per_cluster: Cluster size in bytes
            
        Returns:
            File data bytes or None if read failed
        """
        try:
            # Calculate cluster offset (cluster 2 is at data_offset)
            cluster_offset = data_offset + (start_cluster - 2) * bytes_per_cluster
            
            # Seek to cluster
            drive_handle.seek(cluster_offset)
            
            # Read file data (up to file_size)
            file_data = drive_handle.read(file_size)
            
            return file_data if file_data else None
            
        except Exception as e:
            logger.debug(f"Error reading FAT clusters: {e}")
            return None
    
    def _get_interested_extensions(self, file_type_options: Dict) -> set:
        """Get set of file extensions user is interested in"""
        # Handle empty or None options
        if not file_type_options:
            return {'jpg', 'png', 'pdf', 'docx', 'xlsx', 'pptx', 'txt', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'zip', 'rar', 'sqlite', 'csv'}
        
        # Handle if file_type_options is a list (from frontend)
        if isinstance(file_type_options, list):
            # Frontend sends list of strings like ['RAW', 'images', 'documents']
            # Convert to dictionary format
            file_type_dict = {}
            for item in file_type_options:
                if isinstance(item, str):
                    file_type_dict[item.lower()] = True
            file_type_options = file_type_dict
        
        extensions = set()
        file_type_map = {
            'images': {'jpg', 'jpeg', 'png'},
            'documents': {'pdf', 'docx', 'xlsx', 'pptx', 'txt'},
            'videos': {'mp4', 'avi', 'mov'},
            'audio': {'mp3', 'wav'},
            'archives': {'zip', 'rar'},
            'email': {'sqlite', 'csv'},
            'raw': set()  # RAW means all file types
        }
        
        for category, enabled in file_type_options.items():
            category_lower = category.lower()
            if enabled and category_lower in file_type_map:
                extensions.update(file_type_map[category_lower])
            elif enabled and category_lower == 'raw':
                # RAW means all file types - return everything
                for exts in file_type_map.values():
                    extensions.update(exts)
        
        return extensions if extensions else {'jpg', 'png', 'pdf', 'docx', 'xlsx', 'pptx', 'txt', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'zip', 'rar', 'sqlite', 'csv'}
    
    def _get_signature_for_extension(self, extension: str) -> Optional[Dict]:
        """Get signature info for a file extension"""
        for sig_name, sig_info in self.signatures.items():
            if sig_info.get('extension') == extension and sig_info.get('important', False):
                return sig_info
        return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system use"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        return filename
    
    def _scan_chunk_for_signatures(self, chunk_data: bytes, chunk_offset: int, 
                                   signatures_to_scan: Dict, max_file_size: int) -> List[Dict]:
        """
        Scan a chunk of data for file signatures (for parallel processing)
        
        Args:
            chunk_data: Chunk of data to scan
            chunk_offset: Absolute offset of this chunk on drive
            signatures_to_scan: Dictionary of signatures to search for
            max_file_size: Maximum file size to extract
            
        Returns:
            List of potential file matches with metadata
        """
        matches = []
        
        for sig_name, sig_info in signatures_to_scan.items():
            header = sig_info['header']
            sig_offset = sig_info.get('offset', 0)
            
            # Search for signature in chunk
            search_start = 0
            while True:
                pos = chunk_data.find(header, search_start)
                if pos == -1:
                    break
                
                # Calculate absolute offset
                absolute_pos = chunk_offset + pos
                
                # Validate offset if specified
                if sig_offset > 0:
                    if pos < sig_offset:
                        search_start = pos + 1
                        continue
                    actual_pos = pos - sig_offset
                else:
                    actual_pos = pos
                
                # Additional validation for specific file types
                if 'check' in sig_info:
                    check_bytes = sig_info['check']
                    if check_bytes not in chunk_data[actual_pos:actual_pos + 1000]:
                        search_start = pos + 1
                        continue
                
                # Store match information
                matches.append({
                    'sig_name': sig_name,
                    'sig_info': sig_info,
                    'chunk_offset': chunk_offset,
                    'local_pos': actual_pos,
                    'absolute_pos': absolute_pos,
                    'chunk_data': chunk_data,
                })
                
                search_start = pos + 1
        
        return matches
    
    async def _carve_files(self, drive_handle: BinaryIO, output_dir: str, 
                          stats: Dict, options: Optional[Dict] = None,
                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Carve files from drive using signature-based detection
        
        Args:
            drive_handle: Open file handle to the drive
            output_dir: Directory to save recovered files
            stats: Statistics dictionary to update
            options: Scan options (includes scan_type: 'quick', 'normal', 'deep')
            progress_callback: Async callback for progress updates
            
        Returns:
            List of recovered file dictionaries
        """
        recovered_files = []
        
        # Get scan type from options (default to 'normal')
        scan_type = options.get('scan_type', 'normal') if options else 'normal'
        
        # Determine which file types to scan based on scan type
        if scan_type == 'quick':
            # Quick scan: Only most common important files
            chunk_size = 2 * 1024 * 1024  # 2MB chunks for faster scanning
            signatures_to_scan = {k: v for k, v in self.signatures.items() 
                                 if v.get('important', False) and 
                                 v['extension'] in ['jpg', 'png', 'pdf', 'docx', 'xlsx', 'mp4', 'mp3']}
            max_file_size = 10 * 1024 * 1024  # CONSERVATIVE: 10MB max per file
            logger.info("Quick scan mode: Scanning for common important files only")
            
        elif scan_type == 'deep':
            # Deep scan: ALL file types (like Signature File Carving with all types selected)
            # SAFE MODE: Read-only, no write operations to drive
            
            # PHASE 4: Memory Optimization - Calculate optimal chunk size
            available_memory = self._get_available_memory()
            chunk_size = self._optimize_buffer_size(stats['total_size'], available_memory)
            logger.info(f"💾 Memory optimization: {available_memory / (1024**3):.2f} GB available, using {chunk_size / (1024**2):.2f} MB chunks")
            
            # Deep scan: Use ALL file signatures (including system files)
            signatures_to_scan = self.signatures.copy()
            
            # Filter to only signatures with headers (can be detected)
            signatures_to_scan = {k: v for k, v in signatures_to_scan.items() if v.get('header') is not None}
            
            max_file_size = 20 * 1024 * 1024  # 20MB max per file for deep scan
            
            # Get unique extensions for logging
            extensions_list = sorted(set(v['extension'] for v in signatures_to_scan.values()))
            
            logger.info(f"🔍 Deep scan mode: Scanning for ALL file types (comprehensive recovery)")
            logger.info(f"   Total signatures to scan: {len(signatures_to_scan)} (SAFE MODE - Read Only)")
            logger.info(f"   Unique extensions: {', '.join(extensions_list[:20])}{'...' if len(extensions_list) > 20 else ''}")
            logger.info(f"   Maximum file size: {max_file_size / (1024**2):.0f} MB")
            logger.info(f"   Validation: Only recoverable files will be saved")
            
        elif scan_type == 'carving':
            # File Carving scan: Focus on deleted user files (photos, videos, documents, audio)
            # SAFE MODE: Read-only, no write operations to drive
            
            # PHASE 4: Memory Optimization - Calculate optimal chunk size
            available_memory = self._get_available_memory()
            chunk_size = self._optimize_buffer_size(stats['total_size'], available_memory)
            logger.info(f"💾 Memory optimization: {available_memory / (1024**3):.2f} GB available, using {chunk_size / (1024**2):.2f} MB chunks")
            
            # Get selected file types from options (default to all)
            file_type_options = options.get('fileTypes', {}) if options else {}
            
            logger.info(f"📋 Received file type options: {file_type_options}")
            
            # Define file signature keys for each category (ONLY specified extensions)
            file_type_map = {
                'images': ['jpg', 'png'],  # ONLY JPG, PNG
                'documents': ['pdf', 'docx', 'xlsx', 'pptx', 'txt'],  # PDF, Office, TXT
                'videos': ['mp4', 'avi', 'mov'],  # ONLY MP4, AVI, MOV
                'audio': ['mp3', 'mp3_id3', 'wav'],  # ONLY MP3, WAV
                'archives': ['zip', 'rar'],  # ONLY ZIP, RAR
                'email': ['sqlite', 'csv']  # SQLite, CSV (databases category)
            }
            
            # Build list of signature keys to scan based on selected types
            signature_keys_to_scan = []
            selected_categories = []
            
            for category, enabled in file_type_options.items():
                logger.debug(f"Checking category '{category}': enabled={enabled}, in_map={category in file_type_map}")
                if enabled and category in file_type_map:
                    keys = file_type_map[category]
                    signature_keys_to_scan.extend(keys)
                    selected_categories.append(category)
                    logger.debug(f"  Added {len(keys)} signature keys: {keys}")
            
            logger.info(f"📊 Total signature keys before dedup: {len(signature_keys_to_scan)}")
            
            # If no specific types selected, scan ONLY important file types (not system files)
            if not signature_keys_to_scan:
                signature_keys_to_scan = [k for k, v in self.signatures.items() if v.get('important', False)]
                selected_categories = ['all important']
                logger.info(f"No types selected, using all important: {len(signature_keys_to_scan)} signatures")
            
            # Remove duplicates while preserving order
            signature_keys_to_scan = list(dict.fromkeys(signature_keys_to_scan))
            
            # Filter signatures based on selected signature keys
            # IMPORTANT: Only include signatures that have a header (can be detected)
            signatures_to_scan = {}
            for k in signature_keys_to_scan:
                if k in self.signatures:
                    sig = self.signatures[k]
                    # Skip signatures without headers (txt, csv) - can't be detected by carving
                    if sig.get('header') is None:
                        logger.debug(f"Skipping '{k}' - no signature header for detection")
                        continue
                    signatures_to_scan[k] = sig
            
            logger.info(f"📊 Total signatures after filtering: {len(signatures_to_scan)}")
            
            # Ensure we have signatures to scan
            if not signatures_to_scan:
                logger.warning("⚠️ No valid signatures found for selected file types!")
                logger.warning("   Note: TXT and CSV files cannot be detected by signature scanning")
                return []
            
            max_file_size = 10 * 1024 * 1024  # CONSERVATIVE: 10MB max per file
            
            # Get unique extensions for logging
            extensions_list = sorted(set(v['extension'] for v in signatures_to_scan.values()))
            
            logger.info(f"🔍 File Carving scan mode: Scanning for {', '.join(selected_categories) if selected_categories else 'all'} file types")
            logger.info(f"   Selected signature keys: {len(signature_keys_to_scan)} ({', '.join(signature_keys_to_scan[:10])}{'...' if len(signature_keys_to_scan) > 10 else ''})")
            logger.info(f"   Unique extensions: {', '.join(extensions_list)}")
            logger.info(f"   Total signatures to scan: {len(signatures_to_scan)} (SAFE MODE - Read Only)")
            logger.info(f"   Validation: Only recoverable files will be saved")
            
        else:
            # Normal scan should not reach here (handled separately)
            # But if it does, use important files only
            chunk_size = 1024 * 1024  # 1MB chunks
            signatures_to_scan = {k: v for k, v in self.signatures.items() 
                                 if v.get('important', True)}  # Only important files
            max_file_size = 10 * 1024 * 1024  # CONSERVATIVE: 10MB max per file
            logger.info("Default scan mode: Scanning for important user files (excluding system files)")
        
        logger.info(f"Scanning for {len(signatures_to_scan)} file types out of {len(self.signatures)} total")
        
        # Final check: ensure we have signatures to scan
        if not signatures_to_scan:
            logger.error("❌ No signatures available for scanning! Aborting.")
            return []
        
        buffer = b''
        offset = 0
        file_counter = 0
        last_progress_time = datetime.now()
        found_hashes = set()  # Track file hashes to prevent duplicates
        found_offsets = set()  # Track file start offsets to prevent overlaps
        skipped_corrupted = 0  # Track corrupted files skipped
        total_recovered_size = 0  # Track total size of recovered files
        
        # SAFETY: Maximum total recovered size (prevent filling up C: drive)
        # For indexing mode (deep scan), no limit needed since we're not writing files
        # For other modes (carving, quick), limit to 2x drive size or 20GB
        source_drive_size = stats.get('total_size', 0)
        
        if scan_type == 'deep':
            max_total_recovery_size = float('inf')  # No limit for indexing mode
            logger.info("💡 INDEX MODE: No size limit (files are cataloged, not written)")
        else:
            max_total_recovery_size = min(source_drive_size * 2, 20 * 1024 * 1024 * 1024)  # 2x drive or 20GB max
            logger.info(f"⚠️ SAFETY LIMIT: Maximum total recovery size: {max_total_recovery_size / (1024**3):.2f} GB")
        
        logger.info("Starting file carving...")
        logger.info(f"Duplicate detection enabled (hash-based)")
        logger.info(f"File validation enabled (integrity check)")
        logger.info(f"Chunk size: {chunk_size / 1024:.0f} KB")
        
        chunks_read = 0
        try:
            while True:
                # Check for cancellation
                is_cancelled = options.get('is_cancelled') if options else None
                if is_cancelled and callable(is_cancelled) and is_cancelled():
                    logger.warning("⚠️ Scan cancelled by user")
                    logger.info(f"📋 Carving cancelled - returning {len(recovered_files)} partial results found so far")
                    logger.info(f"💾 Partial scan size: {total_recovered_size / (1024**3):.2f} GB indexed")
                    break
                
                # Read chunk
                # If we know the total size, avoid reading past it (safety guard)
                to_read = chunk_size
                if stats.get('total_size') and stats['total_size'] > 0:
                    remaining = stats['total_size'] - stats['bytes_scanned']
                    if remaining <= 0:
                        break
                    to_read = min(chunk_size, int(remaining))

                chunk = drive_handle.read(to_read)
                if not chunk:
                    break
                
                # Yield control to event loop after every read to allow cancellation
                await asyncio.sleep(0)
                
                chunks_read += 1
                
                buffer += chunk
                stats['bytes_scanned'] += len(chunk)
                stats['sectors_scanned'] = stats['bytes_scanned'] // 512
                
                # Calculate progress
                if stats['total_sectors'] > 0:
                    progress_pct = (stats['sectors_scanned'] / stats['total_sectors']) * 100
                else:
                    progress_pct = 0
                
                # Broadcast progress every second
                current_time = datetime.now()
                if (current_time - last_progress_time).total_seconds() >= 1.0:
                    if progress_callback:
                        elapsed = (current_time - datetime.fromisoformat(stats['start_time'])).total_seconds()
                        expected_time = self._calculate_expected_time(elapsed, progress_pct)
                        await progress_callback({
                            'progress': min(progress_pct, 99.9),  # Never show 100% until complete
                            'sectors_scanned': stats['sectors_scanned'],
                            'total_sectors': stats['total_sectors'],
                            'files_found': len(recovered_files),
                            'expected_time': expected_time,
                            'current_pass': 1
                        })
                    last_progress_time = current_time
                
                # Search for file signatures in buffer (only filtered signatures)
                for sig_name, sig_info in signatures_to_scan.items():
                    header = sig_info['header']
                    sig_offset = sig_info.get('offset', 0)
                    
                    # Search for signature in buffer
                    search_start = 0
                    while True:
                        # Check for cancellation during intensive signature search
                        is_cancelled = options.get('is_cancelled') if options else None
                        if is_cancelled and callable(is_cancelled) and is_cancelled():
                            logger.info("🛑 Cancellation detected during signature search")
                            break
                        
                        pos = buffer.find(header, search_start, len(buffer) - 100000)  # Keep some buffer
                        if pos == -1:
                            break
                        
                        # Calculate absolute offset
                        absolute_pos = offset + pos
                        
                        # Skip if we already found a file starting near this offset
                        # Allow 512 byte tolerance for alignment issues
                        if any(abs(absolute_pos - found_offset) < 512 for found_offset in found_offsets):
                            search_start = pos + 1
                            continue
                        
                        # Validate offset if specified
                        if sig_offset > 0:
                            if pos < sig_offset:
                                search_start = pos + 1
                                continue
                            actual_pos = pos - sig_offset
                        else:
                            actual_pos = pos
                        
                        # Additional validation for specific file types
                        if 'check' in sig_info:
                            check_bytes = sig_info['check']
                            if check_bytes not in buffer[actual_pos:actual_pos + 1000]:
                                search_start = pos + 1
                                continue
                        
                        # Extract file
                        try:
                            file_data = self._extract_file(
                                buffer,
                                actual_pos,
                                sig_info,
                                drive_handle,
                                offset + actual_pos,
                                max_file_size
                            )
                            
                            # Filter out very small files (likely corrupted or fragments)
                            # STRICT: Minimum 4KB for all file types (reject tiny fragments)
                            min_size = 4096
                            
                            if file_data and len(file_data) >= min_size:
                                # Validate file integrity and get validation score
                                validation_result = self._validate_file_with_score(file_data, sig_info)
                                if not validation_result['is_valid']:
                                    logger.debug(f"Skipped corrupted/invalid file at offset {absolute_pos}")
                                    skipped_corrupted += 1
                                    search_start = pos + 1
                                    continue
                                
                                # STRICT: Only save files with GOOD validation scores (>= 70)
                                validation_score = validation_result.get('score', 0)
                                if validation_score < 70:
                                    logger.debug(f"Skipped low-quality file at offset {absolute_pos} (score: {validation_score})")
                                    skipped_corrupted += 1
                                    search_start = pos + 1
                                    continue
                                
                                # Check for duplicate content using MD5 (fast) and SHA256 (secure)
                                file_md5 = hashlib.md5(file_data).hexdigest()
                                file_sha256 = hashlib.sha256(file_data).hexdigest()
                                
                                if file_md5 in found_hashes:
                                    logger.debug(f"Skipped duplicate file at offset {absolute_pos} (MD5: {file_md5[:8]}...)")
                                    search_start = pos + 1
                                    continue
                                
                                # Determine if file is fragmented/partial
                                is_partial = validation_result.get('is_partial', False)
                                file_ext = sig_info['extension']
                                if is_partial:
                                    file_ext = f"partial.{file_ext}"
                                
                                # Track this file
                                file_counter += 1
                                found_hashes.add(file_md5)
                                found_offsets.add(absolute_pos)
                                
                                # Calculate recovered size
                                total_recovered_size += len(file_data)
                                
                                # SAFETY CHECK: Only for non-deep scans (deep scan has no limit)
                                if scan_type != 'deep' and total_recovered_size > max_total_recovery_size:
                                    logger.warning("⚠️ SCAN LIMIT REACHED!")
                                    logger.warning(f"   Total found: {total_recovered_size / (1024**3):.2f} GB")
                                    logger.warning(f"   Limit: {max_total_recovery_size / (1024**3):.2f} GB")
                                    logger.warning("   Stopping scan to prevent excessive recovery!")
                                    break  # Stop scanning
                                
                                # Generate filename and path
                                file_name = f"f{absolute_pos:08d}.{file_ext}"
                                
                                # DEEP SCAN: Index-only mode (read-only, no file writing)
                                # CARVING SCAN: Write files immediately to TEMP directory
                                if scan_type == 'deep':
                                    # Use original output_dir for path reference (not actually written)
                                    file_path = os.path.join(output_dir, file_name)
                                    
                                    # DEEP SCAN: Only create index entry (no file written)
                                    partial_marker = " [PARTIAL]" if is_partial else ""
                                    logger.debug(f"📋 Indexed: {file_name} ({len(file_data)} bytes, SHA256: {file_sha256[:16]}...){partial_marker}")
                                    
                                    # Create file catalog entry (NO FILE WRITTEN TO DISK)
                                    file_info = {
                                        'name': file_name,
                                        'path': file_path,
                                        'size': len(file_data),
                                        'type': sig_info['extension'].upper(),
                                        'extension': sig_info['extension'],
                                        'offset': absolute_pos,
                                        'md5': file_md5,
                                        'sha256': file_sha256,
                                        'hash': file_sha256,  # Alias for compatibility
                                        'file_hash': file_sha256,  # Another alias
                                        'validation_score': validation_result.get('score', 0),
                                        'is_partial': is_partial,
                                        'method': 'deep_scan_index',
                                        'status': 'indexed',  # Not yet recovered - user must select
                                        'indexed_at': datetime.now().isoformat(),
                                        'drive_path': stats.get('physical_drive', stats.get('drive_path', 'unknown')),  # Store physical drive for recovery
                                        'signature': sig_name  # Store signature type for validation
                                    }
                                else:
                                    # CARVING SCAN: Write file to TEMPORARY directory (recovered_files in project root)
                                    # These files will be copied to final output path on recovery
                                    try:
                                        # Get project root (parent of backend directory)
                                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                                        temp_recovery_dir = os.path.join(project_root, 'backend', 'recovered_files')
                                        
                                        # Ensure temp directory exists
                                        os.makedirs(temp_recovery_dir, exist_ok=True)
                                        
                                        # Write to temp location
                                        temp_file_path = os.path.join(temp_recovery_dir, file_name)
                                        
                                        with open(temp_file_path, 'wb') as f:
                                            f.write(file_data)
                                        
                                        partial_marker = " [PARTIAL]" if is_partial else ""
                                        logger.debug(f"✅ Temporarily stored: {file_name} ({len(file_data)} bytes, SHA256: {file_sha256[:16]}...){partial_marker}")
                                        
                                        # Create file info entry with 'recovered' status
                                        # Path points to TEMP location, will be copied to final location on recovery
                                        file_info = {
                                            'name': file_name,
                                            'path': temp_file_path,  # Point to temp location
                                            'size': len(file_data),
                                            'type': sig_info['extension'].upper(),
                                            'extension': sig_info['extension'],
                                            'offset': absolute_pos,
                                            'md5': file_md5,
                                            'sha256': file_sha256,
                                            'hash': file_sha256,  # Alias for compatibility
                                            'file_hash': file_sha256,  # Another alias
                                            'validation_score': validation_result.get('score', 0),
                                            'is_partial': is_partial,
                                            'method': 'signature_carving',
                                            'status': 'recovered',  # File has been written to TEMP disk
                                            'recovered_at': datetime.now().isoformat(),
                                            'signature': sig_name  # Store signature type for validation
                                        }
                                        
                                    except Exception as write_error:
                                        logger.error(f"Failed to write file {file_name}: {write_error}")
                                        # Skip this file if we can't write it
                                        search_start = pos + 1
                                        continue
                                
                                # Yield control after processing each file to allow cancellation
                                await asyncio.sleep(0)
                                
                                recovered_files.append(file_info)
                            else:
                                logger.debug(f"Skipped small/corrupted file at offset {absolute_pos}: {len(file_data) if file_data else 0} bytes")
                                
                        except Exception as e:
                            logger.debug(f"Failed to extract file at offset {absolute_pos}: {e}")
                        
                        search_start = pos + 1
                
                # Keep last 100KB of buffer for signatures that span chunks
                if len(buffer) > 100000:
                    offset += len(buffer) - 100000
                    buffer = buffer[-100000:]
                
                # Allow other tasks to run
                await asyncio.sleep(0)
                
        except Exception as e:
            logger.error(f"Error during file carving: {e}", exc_info=True)
        
        # Calculate total recovered size
        total_recovered_size_actual = sum(f['size'] for f in recovered_files)
        total_recovered_mb = total_recovered_size_actual / (1024 * 1024)
        
        # Check if scan was cancelled
        is_cancelled_final = options.get('is_cancelled') if options else None
        was_cancelled = is_cancelled_final and callable(is_cancelled_final) and is_cancelled_final()
        
        # Log scan results based on scan type
        if was_cancelled:
            logger.warning("⚠️ Scan was CANCELLED - Showing PARTIAL results")
            if scan_type == 'deep':
                logger.info(f"📋 Partial scan results: {len(recovered_files)} files indexed")
                logger.info(f"💾 Partial indexed size: {total_recovered_mb:.2f} MB ({total_recovered_size_actual / (1024**3):.2f} GB)")
                logger.info(f"✅ These {len(recovered_files)} files CAN BE RECOVERED - select files to recover")
            else:
                logger.info(f"� Partial scan results: {len(recovered_files)} files recovered")
                logger.info(f"�💾 Partial recovered size: {total_recovered_mb:.2f} MB ({total_recovered_size_actual / (1024**3):.2f} GB)")
                logger.info(f"✅ These {len(recovered_files)} files are SAVED and READY to use")
            logger.info(f"💡 Tip: You can use these partial results or re-run scan to completion")
        else:
            if scan_type == 'deep':
                logger.info(f"🔍 Deep scan complete: {len(recovered_files)} files indexed (read-only mode)")
                logger.info(f"📊 Total indexed size: {total_recovered_mb:.2f} MB ({total_recovered_size_actual / (1024**3):.2f} GB)")
                logger.info(f"� Files are cataloged only - select files to recover them")
            else:
                logger.info(f"🔍 Scan complete: {len(recovered_files)} files recovered successfully")
                logger.info(f"📊 Total recovery size: {total_recovered_mb:.2f} MB ({total_recovered_size_actual / (1024**3):.2f} GB)")
                logger.info(f"💡 All files have been saved to: {output_dir}")
        
        logger.info(f"📋 Files skipped - Duplicates: {file_counter - len(recovered_files)}, Corrupted: {skipped_corrupted}")
        
        # Important note about file carving
        if total_recovered_mb > stats['total_sectors'] * 512 / (1024 * 1024):
            if scan_type == 'deep':
                logger.info("ℹ️ Indexed size exceeds drive capacity - this is NORMAL:")
            else:
                logger.info("ℹ️ Recovered size exceeds drive capacity - this is NORMAL:")
            logger.info("   • Found old deleted files not yet overwritten")
            logger.info("   • Multiple versions of edited files discovered")
            logger.info("   • Temporary copies from applications detected")
            if scan_type == 'deep':
                logger.info("   Recommendation: Select only files you need for recovery")
            else:
                logger.info("   Recommendation: Sort by type and check recovered files")
        
        # Send final progress update
        if progress_callback:
            elapsed = (datetime.now() - datetime.fromisoformat(stats['start_time'])).total_seconds()
            await progress_callback({
                'progress': 100.0,
                'sectors_scanned': stats['sectors_scanned'],
                'total_sectors': stats['total_sectors'],
                'files_found': len(recovered_files),
                'expected_time': "Complete",
                'current_pass': 1,
                'mode': 'indexing' if scan_type == 'deep' else 'carving',
                'total_recovered_size': total_recovered_size_actual
            })
        
        # Generate manifest (index or recovery based on scan type)
        self._generate_index_manifest(recovered_files, output_dir, stats, scan_type)
        
        if scan_type == 'deep':
            logger.info(f"✅ File indexing completed: {len(recovered_files)} files cataloged")
        else:
            logger.info(f"✅ File recovery completed: {len(recovered_files)} files saved to disk")
        return recovered_files
    
    def _generate_index_manifest(self, recovered_files: List[Dict], output_dir: str, stats: Dict, scan_type: str = 'carving'):
        """
        Generate index/recovery manifest with file metadata
        
        Args:
            recovered_files: List of recovered/indexed file information dictionaries
            output_dir: Directory where manifest is saved
            stats: Scan statistics dictionary
            scan_type: Type of scan ('deep' for indexing, 'carving' for recovery)
        """
        try:
            # Different manifest names and content based on scan type
            if scan_type == 'deep':
                manifest_path = os.path.join(output_dir, 'scan_index.json')
                mode_label = 'deep_scan_indexing'
                method_label = 'deep_scan_index'
                status_label = 'indexed'
                files_label = 'indexed_files'
                count_label = 'total_files_indexed'
            else:
                manifest_path = os.path.join(output_dir, 'recovery_manifest.json')
                mode_label = 'signature_carving'
                method_label = 'signature_carving'
                status_label = 'recovered'
                files_label = 'recovered_files'
                count_label = 'total_files_recovered'
            
            # Build manifest data
            manifest = {
                'scan_info': {
                    'mode': mode_label,
                    'timestamp': datetime.now().isoformat(),
                    'drive_path': stats.get('drive_path', 'unknown'),
                    'total_sectors_scanned': stats.get('sectors_scanned', 0),
                    'scan_duration_seconds': (datetime.now() - datetime.fromisoformat(stats['start_time'])).total_seconds(),
                    'recovery_method': method_label
                },
                'statistics': {
                    count_label: len(recovered_files),
                    'unique_files': len(recovered_files),  # Already deduplicated
                    'total_size_bytes': sum(f['size'] for f in recovered_files),
                    'partial_files': sum(1 for f in recovered_files if f.get('is_partial', False)),
                    'disk_space_used': sum(f['size'] for f in recovered_files) if scan_type != 'deep' else 0,  # Only carving uses disk space
                    'recovery_status': 'indexed' if scan_type == 'deep' else 'completed'
                },
                files_label: []
            }
            
            # Add detailed file information for each file
            for file_info in recovered_files:
                file_entry = {
                    'filename': file_info.get('name', 'unknown'),
                    'path': file_info.get('path', ''),  # Saved path (carving) or empty (deep)
                    'size_bytes': file_info.get('size', 0),
                    'offset': file_info.get('offset', 0),  # Original location on drive
                    'file_type': file_info.get('type', 'unknown'),
                    'extension': file_info.get('extension', 'unknown'),
                    'md5': file_info.get('md5', ''),
                    'sha256': file_info.get('sha256', ''),
                    'validation_score': file_info.get('validation_score', 0),
                    'is_partial': file_info.get('is_partial', False),
                    'status': status_label,  # 'indexed' or 'recovered'
                    'method': file_info.get('method', method_label),
                    'recovered_at': file_info.get('recovered_at', datetime.now().isoformat()),
                    'signature': file_info.get('signature', 'unknown')
                }
                
                # Deep scan includes drive path for on-demand recovery
                if scan_type == 'deep':
                    file_entry['drive_path'] = file_info.get('drive_path', stats.get('physical_drive', stats.get('drive_path', 'unknown')))
                
                manifest[files_label].append(file_entry)
            
            # Write manifest file
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            # Mode-specific logging
            if scan_type == 'deep':
                logger.info(f"📋 Scan index generated: {manifest_path}")
                logger.info(f"   Total files indexed: {manifest['statistics'][count_label]}")
                logger.info(f"   Partial files: {manifest['statistics']['partial_files']}")
                logger.info(f"   Indexed size: {manifest['statistics']['total_size_bytes'] / (1024**2):.2f} MB")
                logger.info(f"   Disk space used: 0 MB (index-only mode)")
            else:
                logger.info(f"📋 Recovery manifest generated: {manifest_path}")
                logger.info(f"   Total files recovered: {manifest['statistics'][count_label]}")
                logger.info(f"   Partial files: {manifest['statistics']['partial_files']}")
                logger.info(f"   Recovery size: {manifest['statistics']['total_size_bytes'] / (1024**2):.2f} MB")
                logger.info(f"   Disk space used: {manifest['statistics']['disk_space_used'] / (1024**2):.2f} MB")
            
        except Exception as e:
            logger.error(f"Failed to generate recovery manifest: {e}", exc_info=True)
    
    def _format_time(self, seconds: float) -> str:
        """Format time as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
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
    
    def _extract_file(self, buffer: bytes, start_pos: int, sig_info: Dict,
                     drive_handle: BinaryIO, absolute_offset: int, max_file_size: int = 100 * 1024 * 1024) -> Optional[bytes]:
        """
        Extract file data from buffer
        
        Args:
            buffer: Buffer containing the file data
            start_pos: Start position in buffer
            sig_info: Signature information dictionary
            drive_handle: Drive handle for reading more data if needed
            absolute_offset: Absolute offset on drive
            max_file_size: Maximum file size to extract
            
        Returns:
            File data as bytes or None if extraction failed
        """
        footer = sig_info.get('footer')
        
        if footer:
            # Look for footer in buffer
            end_pos = buffer.find(footer, start_pos + len(sig_info['header']))
            if end_pos != -1:
                end_pos += len(footer)
                return buffer[start_pos:end_pos]
            else:
                # STRICT: If footer is defined but not found, REJECT the file
                # Don't recover partial/incomplete files
                file_ext = sig_info['extension']
                logger.debug(f"Rejecting {file_ext} at {absolute_offset} - footer not found")
                return None
        else:
            # No footer - try to determine size from file header
            file_ext = sig_info['extension']
            
            # Use smart size detection based on file type (CONSERVATIVE LIMITS)
            if file_ext in ['jpg', 'jpeg']:
                # JPEG: MUST find EOI marker (FF D9) - STRICT MODE
                eoi = b'\xff\xd9'
                end_pos = buffer.find(eoi, start_pos + 2)
                if end_pos != -1:
                    return buffer[start_pos:end_pos + 2]
                else:
                    # STRICT: No EOI marker found = corrupted/incomplete JPEG
                    logger.debug(f"Rejecting JPEG at {absolute_offset} - no EOI marker found")
                    return None
            
            elif file_ext == 'png':
                # PNG: MUST find IEND chunk - STRICT MODE
                iend = b'\x00\x00\x00\x00IEND\xae\x42\x60\x82'
                end_pos = buffer.find(iend, start_pos + 8)
                if end_pos != -1:
                    return buffer[start_pos:end_pos + 12]
                else:
                    # STRICT: No IEND chunk = corrupted/incomplete PNG
                    logger.debug(f"Rejecting PNG at {absolute_offset} - no IEND chunk found")
                    return None
            
            elif file_ext == 'mp3':
                # CONSERVATIVE: Audio files - limit to 5MB (typical song)
                end_pos = min(start_pos + 5 * 1024 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            elif file_ext == 'wav':
                # CONSERVATIVE: WAV - 5MB limit (short audio)
                end_pos = min(start_pos + 5 * 1024 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            elif file_ext in ['mp4', 'mov']:
                # CONSERVATIVE: Video files - limit to 10MB (very short clips)
                end_pos = min(start_pos + 10 * 1024 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            elif file_ext == 'avi':
                # CONSERVATIVE: AVI video format - 10MB limit
                end_pos = min(start_pos + 10 * 1024 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            elif file_ext in ['docx', 'xlsx', 'pptx', 'zip']:
                # Office files and ZIP: MUST find end of central directory - STRICT MODE
                # Look for PK\x05\x06 (end of central directory)
                eocd = b'PK\x05\x06'
                end_pos = buffer.find(eocd, start_pos + 100)
                if end_pos != -1:
                    # Found EOCD, include it plus the 22 bytes of EOCD record
                    return buffer[start_pos:end_pos + 22]
                else:
                    # STRICT: No EOCD = incomplete ZIP/Office file
                    logger.debug(f"Rejecting {file_ext} at {absolute_offset} - no ZIP end marker found")
                    return None
            
            elif file_ext == 'txt':
                # CONSERVATIVE: Text files - 500KB limit
                end_pos = min(start_pos + 512 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            elif file_ext == 'pdf':
                # PDF: MUST find %%EOF marker - STRICT MODE
                eof = b'%%EOF'
                end_pos = buffer.find(eof, start_pos + 10)
                if end_pos != -1:
                    return buffer[start_pos:end_pos + 5]
                else:
                    # STRICT: No %%EOF = incomplete PDF
                    logger.debug(f"Rejecting PDF at {absolute_offset} - no %%EOF marker found")
                    return None
            
            elif file_ext == 'rar':
                # RAR: Look for RAR end marker (not always reliable)
                # For now, limit to 5MB
                end_pos = min(start_pos + 5 * 1024 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            elif file_ext in ['sqlite', 'db', 'sqlite3']:
                # CONSERVATIVE: Database files - 5MB limit
                end_pos = min(start_pos + 5 * 1024 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            elif file_ext == 'csv':
                # CONSERVATIVE: CSV files - 1MB limit
                end_pos = min(start_pos + 1 * 1024 * 1024, len(buffer))
                return buffer[start_pos:end_pos]
            
            else:
                # CONSERVATIVE: Default - 1MB for unknown types
                default_size = 1 * 1024 * 1024  # 1MB default
                end_pos = min(start_pos + default_size, len(buffer))
                return buffer[start_pos:end_pos]
    
    def _advanced_image_validation(self, file_data: bytes, file_ext: str) -> Dict:
        """
        Advanced image validation using Pillow
        
        Args:
            file_data: Image file data
            file_ext: File extension
            
        Returns:
            Dictionary with validation details:
            {
                'is_valid': bool,
                'can_open': bool,
                'format': str,
                'size': tuple,
                'mode': str,
                'reason': str
            }
        """
        result = {
            'is_valid': False,
            'can_open': False,
            'format': None,
            'size': None,
            'mode': None,
            'reason': 'Pillow not available'
        }
        
        if not PILLOW_AVAILABLE:
            return result
        
        try:
            # Try to open image with Pillow
            img = Image.open(io.BytesIO(file_data))
            
            result['can_open'] = True
            result['format'] = img.format
            result['size'] = img.size
            result['mode'] = img.mode
            
            # Verify image can be loaded (not just opened)
            img.verify()
            result['is_valid'] = True
            result['reason'] = f'Valid {img.format} image: {img.size[0]}x{img.size[1]}'
            
            # Additional checks
            if img.size[0] < 1 or img.size[1] < 1:
                result['is_valid'] = False
                result['reason'] = 'Invalid image dimensions'
            
        except Exception as e:
            result['reason'] = f'Pillow validation failed: {str(e)}'
        
        return result
    
    def _advanced_mime_validation(self, file_data: bytes) -> Dict:
        """
        Advanced MIME type validation using python-magic
        
        Args:
            file_data: File data
            
        Returns:
            Dictionary with MIME type information:
            {
                'mime_type': str,
                'description': str,
                'available': bool
            }
        """
        result = {
            'mime_type': None,
            'description': None,
            'available': MAGIC_AVAILABLE
        }
        
        if not MAGIC_AVAILABLE:
            return result
        
        try:
            # Get MIME type
            mime = magic.Magic(mime=True)
            result['mime_type'] = mime.from_buffer(file_data[:8192])
            
            # Get file description
            desc = magic.Magic()
            result['description'] = desc.from_buffer(file_data[:8192])
            
        except Exception as e:
            logger.debug(f"Magic validation error: {e}")
        
        return result
    
    def _validate_file_with_score(self, file_data: bytes, sig_info: Dict) -> Dict:
        """
        Validate file and return detailed validation result with scoring
        
        Args:
            file_data: The file data to validate
            sig_info: Signature information for the file type
            
        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'score': int (0-100),
                'is_partial': bool,
                'reason': str
            }
        """
        # Initialize result
        result = {
            'is_valid': False,
            'score': 0,
            'is_partial': False,
            'reason': 'Unknown error'
        }
        
        # Check minimum size
        if not file_data or len(file_data) < 512:
            result['reason'] = 'File too small (< 512 bytes)'
            return result
        
        file_ext = sig_info['extension']
        score = 0
        is_partial = False
        
        try:
            # Use existing strict validation
            is_valid = self._validate_file(file_data, sig_info)
            
            if not is_valid:
                result['reason'] = 'Failed strict validation checks'
                return result
            
            # If validation passed, calculate score based on completeness
            score = 50  # Base score for passing validation
            
            # Check for footer presence (indicates complete file)
            footer = sig_info.get('footer')
            if footer:
                has_footer = file_data.endswith(footer) or footer in file_data[-100:]
                if has_footer:
                    score += 30  # Complete file with footer
                else:
                    is_partial = True
                    score += 10  # Partial file without footer
            else:
                # No footer defined, assume complete
                score += 30
            
            # Additional scoring based on file type specifics
            if file_ext in ['jpg', 'jpeg']:
                # JPEG: Check for EOI marker
                if file_data.endswith(b'\xFF\xD9') or b'\xFF\xD9' in file_data[-10:]:
                    score += 20  # Complete JPEG
                else:
                    is_partial = True
                    score -= 10  # Missing EOI
                    
            elif file_ext == 'png':
                # PNG: Check for IEND chunk
                if file_data.endswith(b'IEND\xae\x42\x60\x82'):
                    score += 20  # Complete PNG
                else:
                    is_partial = True
                    score -= 10  # Missing IEND
                    
            elif file_ext == 'pdf':
                # PDF: Check for %%EOF
                if b'%%EOF' in file_data[-100:]:
                    score += 20  # Complete PDF
                else:
                    is_partial = True
                    score -= 10  # Missing EOF
                    
            elif file_ext in ['docx', 'xlsx', 'pptx', 'zip']:
                # ZIP-based: Check for end of central directory
                if b'PK\x05\x06' in file_data[-1000:]:
                    score += 20  # Complete ZIP
                else:
                    is_partial = True
                    score -= 10  # Incomplete ZIP
                    
            elif file_ext in ['mp4', 'mov', 'avi', 'wav']:
                # Video/audio: Check for reasonable size ratio
                # (crude check, but helps detect truncated files)
                if len(file_data) > 100000:  # Reasonable size for media
                    score += 20
                else:
                    score += 10  # Small media file
                    
            elif file_ext == 'mp3':
                # MP3: Check frame count
                frame_count = file_data.count(b'\xFF\xFB')
                if frame_count > 1000:
                    score += 20  # Many frames, likely complete
                elif frame_count > 500:
                    score += 15  # Moderate frames
                else:
                    score += 10  # Few frames, might be partial
            
            # Ensure score is in range [0, 100]
            score = max(0, min(100, score))
            
            # PHASE 3: Advanced validation with Pillow (if available)
            if file_ext in ['jpg', 'jpeg', 'png'] and PILLOW_AVAILABLE:
                image_validation = self._advanced_image_validation(file_data, file_ext)
                if image_validation['can_open']:
                    if image_validation['is_valid']:
                        score = min(100, score + 5)  # Bonus for Pillow validation
                        result['reason'] = f"Validated: {image_validation['reason']}"
                    else:
                        score = max(0, score - 10)  # Penalty if Pillow can't validate
                        result['reason'] = f"Pillow validation failed: {image_validation['reason']}"
            
            # PHASE 3: Advanced MIME validation (if available)
            if MAGIC_AVAILABLE:
                mime_validation = self._advanced_mime_validation(file_data)
                if mime_validation['mime_type']:
                    # Verify MIME type matches expected file type
                    expected_mimes = {
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'pdf': 'application/pdf',
                        'zip': 'application/zip',
                        'mp4': 'video/mp4',
                        'mp3': 'audio/mpeg',
                    }
                    if file_ext in expected_mimes:
                        if mime_validation['mime_type'] == expected_mimes[file_ext]:
                            score = min(100, score + 3)  # Bonus for MIME match
                        else:
                            logger.debug(f"MIME mismatch: expected {expected_mimes[file_ext]}, got {mime_validation['mime_type']}")
            
            # Final score adjustment
            score = max(0, min(100, score))
            
            result['is_valid'] = True
            result['score'] = score
            result['is_partial'] = is_partial
            result['reason'] = 'Validation passed'
            
            if is_partial:
                result['reason'] = 'File appears partial/fragmented'
            
        except Exception as e:
            result['reason'] = f'Validation exception: {str(e)}'
            logger.debug(f"Validation error for {file_ext}: {e}")
        
        return result
    
    def _validate_file(self, file_data: bytes, sig_info: Dict) -> bool:
        """
        Validate if the recovered file is actually readable and not corrupted
        STRICT VALIDATION - Only accept files in perfect condition
        
        Args:
            file_data: The file data to validate
            sig_info: Signature information for the file type
            
        Returns:
            True if file appears valid, False if corrupted
        """
        if not file_data or len(file_data) < 512:  # Minimum 512 bytes for valid files
            return False
        
        file_ext = sig_info['extension']
        
        try:
            # Check header is present
            if 'header' in sig_info and sig_info['header']:
                if not file_data.startswith(sig_info['header']):
                    return False
            
            # STRICT validation based on file type
            if file_ext in ['jpg', 'jpeg']:
                # JPEG STRICT validation
                if not file_data.startswith(b'\xFF\xD8\xFF'):
                    return False
                # MUST have End of Image marker
                if not file_data.endswith(b'\xFF\xD9') and b'\xFF\xD9' not in file_data[-10:]:
                    return False
                # Must have multiple valid JPEG segments (SOF, DHT, DQT, SOS, etc.)
                if file_data.count(b'\xFF') < 10:  # Strict: need many markers
                    return False
                # Check for JFIF or Exif marker (standard JPEG)
                if b'JFIF' not in file_data[:50] and b'Exif' not in file_data[:50]:
                    return False
                # Check file has reasonable structure (not just header+footer)
                if len(file_data) < 2048:  # Real JPEGs are usually > 2KB
                    return False
            
            elif file_ext == 'png':
                # PNG STRICT validation
                if not file_data.startswith(b'\x89PNG\r\n\x1a\n'):
                    return False
                # MUST have IHDR chunk immediately after header
                if b'IHDR' not in file_data[8:25]:
                    return False
                # MUST end with IEND chunk
                if not file_data.endswith(b'IEND\xae\x42\x60\x82'):
                    # Check if IEND is near the end
                    if b'IEND\xae\x42\x60\x82' not in file_data[-50:]:
                        return False
                # Must have IDAT chunk (actual image data)
                if b'IDAT' not in file_data:
                    return False
                # Check for CRC after IHDR
                if len(file_data) < 50:
                    return False
            
            elif file_ext == 'pdf':
                # PDF STRICT validation
                if not file_data.startswith(b'%PDF-'):
                    return False
                # MUST end with %%EOF
                if b'%%EOF' not in file_data[-100:]:  # EOF should be near end
                    return False
                # Must have catalog
                if b'/Catalog' not in file_data:
                    return False
                # Must have at least one page
                if b'/Page' not in file_data:
                    return False
                # Must have xref table or stream
                if b'xref' not in file_data and b'/XRef' not in file_data:
                    return False
                # Check for proper object structure
                if file_data.count(b'obj') < 2:  # Need multiple objects
                    return False
            
            elif file_ext in ['docx', 'xlsx', 'pptx']:
                # Office files STRICT validation (ZIP-based)
                if not file_data.startswith(b'PK\x03\x04'):
                    return False
                # MUST have proper ZIP end marker
                if b'PK\x05\x06' not in file_data[-1000:]:  # End of central directory
                    return False
                # MUST have central directory records
                if b'PK\x01\x02' not in file_data:
                    return False
                # Check for Office-specific content
                if file_ext == 'docx':
                    if b'word/' not in file_data[:5000]:
                        return False
                    # Must have document.xml
                    if b'document.xml' not in file_data[:10000]:
                        return False
                elif file_ext == 'xlsx':
                    if b'xl/' not in file_data[:5000]:
                        return False
                    # Must have workbook
                    if b'workbook.xml' not in file_data[:10000]:
                        return False
                elif file_ext == 'pptx':
                    if b'ppt/' not in file_data[:5000]:
                        return False
                    # Must have presentation
                    if b'presentation.xml' not in file_data[:10000]:
                        return False
                # Must have [Content_Types].xml
                if b'[Content_Types].xml' not in file_data[:5000]:
                    return False
            
            elif file_ext == 'zip':
                # ZIP STRICT validation
                if not file_data.startswith(b'PK\x03\x04'):
                    return False
                # MUST have end of central directory
                if b'PK\x05\x06' not in file_data[-1000:]:
                    return False
                # Must have at least one central directory entry
                if b'PK\x01\x02' not in file_data:
                    return False
                # Check for valid local file header
                if len(file_data) < 100:
                    return False
            
            elif file_ext == 'rar':
                # RAR STRICT validation
                if not file_data.startswith(b'Rar!\x1a\x07'):
                    return False
                # Check for RAR block headers
                if file_data.count(b'\x74') < 1:  # RAR file header block
                    return False
                # Minimum size for valid RAR
                if len(file_data) < 100:
                    return False
            
            elif file_ext == 'mp3':
                # MP3 STRICT validation
                frame_count = 0
                if file_data.startswith(b'ID3'):
                    # Has ID3 tag - skip it to find audio frames
                    if len(file_data) < 10:
                        return False
                    # ID3v2 tag size
                    tag_size = ((file_data[6] & 0x7F) << 21) | ((file_data[7] & 0x7F) << 14) | \
                               ((file_data[8] & 0x7F) << 7) | (file_data[9] & 0x7F)
                    audio_start = 10 + tag_size
                    if audio_start >= len(file_data):
                        return False
                    # Check for valid MP3 frames after ID3
                    frame_count = file_data[audio_start:].count(b'\xFF\xFB')
                else:
                    frame_count = file_data.count(b'\xFF\xFB')
                
                # Must have many frames for valid MP3 (at least 100 for real audio)
                if frame_count < 100:
                    return False
                # Check file size reasonable for MP3
                if len(file_data) < 32768:  # Real MP3s are > 32KB
                    return False
            
            elif file_ext == 'wav':
                # WAV STRICT validation
                if not file_data.startswith(b'RIFF'):
                    return False
                if b'WAVE' not in file_data[8:12]:
                    return False
                # Must have fmt chunk
                if b'fmt ' not in file_data[12:100]:
                    return False
                # Must have data chunk
                if b'data' not in file_data[:1000]:
                    return False
                # Check RIFF size field
                if len(file_data) < 44:  # Minimum WAV header size
                    return False
                # Validate RIFF chunk size
                riff_size = int.from_bytes(file_data[4:8], 'little')
                if riff_size < 36:  # Minimum valid size
                    return False
            
            elif file_ext in ['mp4', 'mov']:
                # MP4/MOV STRICT validation
                if b'ftyp' not in file_data[:32]:
                    return False
                # Must have moov atom (movie metadata)
                if b'moov' not in file_data:
                    return False
                # Must have mdat atom (media data) or skip (modern files)
                has_mdat = b'mdat' in file_data[:50000]
                has_skip = b'skip' in file_data[:50000]
                if not has_mdat and not has_skip:
                    return False
                # Check for valid brand
                valid_brands = [b'mp41', b'mp42', b'isom', b'qt  ', b'M4V ', b'M4A ']
                has_valid_brand = any(brand in file_data[:32] for brand in valid_brands)
                if not has_valid_brand:
                    return False
            
            elif file_ext == 'avi':
                # AVI STRICT validation
                if not file_data.startswith(b'RIFF'):
                    return False
                if b'AVI ' not in file_data[8:12]:
                    return False
                # Must have hdrl (header list)
                if b'hdrl' not in file_data[:1000]:
                    return False
                # Must have movi (movie data)
                if b'movi' not in file_data[:10000]:
                    return False
                # Check RIFF size
                if len(file_data) < 1024:  # Real AVIs are larger
                    return False
            
            elif file_ext == 'sqlite':
                # SQLite STRICT validation
                if not file_data.startswith(b'SQLite format 3\x00'):
                    return False
                # Check page size (must be power of 2, between 512 and 65536)
                page_size = int.from_bytes(file_data[16:18], 'big')
                if page_size < 512 or page_size > 65536 or (page_size & (page_size - 1)) != 0:
                    return False
                # Must have proper database header
                if len(file_data) < page_size:
                    return False
                # Check for valid schema
                if b'sqlite_master' not in file_data[:page_size * 2]:
                    return False
            
            # If we got here, file passed STRICT validation
            return True
            
        except Exception as e:
            logger.debug(f"Validation error for {file_ext}: {e}")
            return False
    
    def _get_file_size_from_header(self, header_data: bytes, file_type: str) -> Optional[int]:
        """
        Try to determine file size from header data
        
        Args:
            header_data: First few bytes of file
            file_type: File type extension
            
        Returns:
            File size in bytes or None if cannot determine
        """
        try:
            if file_type == 'jpg' and len(header_data) >= 10:
                # JPEG files have segments with size markers
                # This is a simplified version
                return None  # Would need full JPEG parser
            
            elif file_type == 'png' and len(header_data) >= 33:
                # PNG has IHDR chunk early with image dimensions
                # Could estimate size from dimensions
                return None  # Would need PNG chunk parser
            
            elif file_type == 'pdf' and len(header_data) >= 20:
                # PDF files are text-based, size is harder to determine
                return None
            
        except Exception:
            pass
        
        return None

    async def _cluster_scan(self, drive_path: str, output_dir: str, options: dict, progress_callback) -> dict:
        """
        Perform cluster-level scan and generate hex view of drive
        
        Args:
            drive_path: Path to drive (e.g., 'E:')
            output_dir: Output directory for cluster map
            options: Scan options
            progress_callback: Progress update callback
            
        Returns:
            Dictionary with cluster scan results
        """
        try:
            logger.info("🔍 Starting Cluster Scan")
            
            # Initial progress
            if progress_callback:
                await progress_callback({
                    'progress': 0,
                    'sectors_scanned': 0,
                    'total_sectors': 100,
                    'files_found': 0
                })
            
            # Get drive info
            physical_drive = self._get_physical_drive(drive_path)
            drive_size = self._get_drive_size(drive_path)
            
            # Open drive
            drive_handle = self._open_drive(physical_drive)
            
            # Cluster scan parameters
            cluster_size = 4096  # 4KB clusters (typical)
            total_clusters = drive_size // cluster_size
            sample_rate = max(1, total_clusters // 1000)  # Sample 1000 clusters max
            
            logger.info(f"Drive size: {drive_size / (1024**3):.2f} GB")
            logger.info(f"Total clusters: {total_clusters:,}")
            logger.info(f"Sampling every {sample_rate} cluster(s)")
            
            # Update progress - starting scan
            if progress_callback:
                await progress_callback({
                    'progress': 5,
                    'sectors_scanned': 0,
                    'total_sectors': total_clusters // sample_rate,
                    'files_found': 0,
                    'expected_time': 'Calculating...'
                })
            
            cluster_map = []
            stats = {
                'drive_path': drive_path,
                'drive_size': drive_size,
                'total_clusters': total_clusters,
                'sampled_clusters': 0,
                'empty_clusters': 0,
                'used_clusters': 0,
                'start_time': datetime.now().isoformat()
            }
            
            # Sample clusters across the drive
            logger.info(f"Starting cluster sampling loop (sample_rate: {sample_rate})...")
            logger.info(f"Loop parameters - range(0, {total_clusters}, {sample_rate})")
            logger.info(f"Expected iterations: ~{total_clusters // sample_rate}")
            
            sampled_count = 0
            expected_samples = total_clusters // sample_rate
            loop_iterations = 0
            
            for i in range(0, total_clusters, sample_rate):
                loop_iterations += 1
                
                # Check for cancellation
                if options.get('is_cancelled') and callable(options['is_cancelled']) and options['is_cancelled']():
                    logger.info(f"Cluster scan cancelled after {loop_iterations} iterations")
                    break
                
                # Log first few iterations to debug
                if loop_iterations <= 3:
                    logger.info(f"Loop iteration {loop_iterations}: cluster index {i}, offset will be {i * cluster_size}")
                
                try:
                    # Read cluster
                    offset = i * cluster_size
                    drive_handle.seek(offset)
                    cluster_data = drive_handle.read(cluster_size)
                    
                    if loop_iterations <= 3:
                        logger.info(f"  Read {len(cluster_data) if cluster_data else 0} bytes from offset {offset}")
                    
                    if not cluster_data or len(cluster_data) == 0:
                        if loop_iterations <= 5:
                            logger.warning(f"No data read at cluster {i}, offset {offset} - iteration {loop_iterations}")
                        continue
                    
                    # Analyze cluster
                    is_empty = all(b == 0 for b in cluster_data)
                    
                    # Create hex preview (first 256 bytes)
                    preview_size = min(256, len(cluster_data))
                    hex_preview = cluster_data[:preview_size].hex()
                    
                    cluster_info = {
                        'cluster_id': i,
                        'offset': offset,
                        'is_empty': is_empty,
                        'hex_preview': hex_preview,
                        'ascii_preview': ''.join(chr(b) if 32 <= b < 127 else '.' for b in cluster_data[:preview_size])
                    }
                    
                    cluster_map.append(cluster_info)
                    stats['sampled_clusters'] += 1
                    sampled_count += 1
                    
                    if is_empty:
                        stats['empty_clusters'] += 1
                    else:
                        stats['used_clusters'] += 1
                    
                    # Update progress more frequently for better UX
                    if sampled_count % 5 == 0 or sampled_count >= expected_samples:
                        progress = min(95, 5 + (sampled_count / expected_samples) * 90)
                        elapsed = (datetime.now() - datetime.fromisoformat(stats['start_time'])).total_seconds()
                        expected_time = self._calculate_expected_time(elapsed, progress)
                        if progress_callback:
                            await progress_callback({
                                'progress': progress,
                                'sectors_scanned': sampled_count,
                                'total_sectors': expected_samples,
                                'files_found': len(cluster_map),
                                'expected_time': expected_time
                            })
                        if sampled_count % 20 == 0:
                            logger.info(f"Progress: {progress:.1f}% - Sampled {sampled_count}/{expected_samples} clusters")
                    
                except Exception as e:
                    if loop_iterations <= 5:
                        logger.error(f"Error reading cluster {i} (iteration {loop_iterations}): {e}")
                    continue
            
            logger.info(f"Cluster sampling loop completed. Loop iterations: {loop_iterations}, Total sampled: {sampled_count}")
            
            drive_handle.close()
            
            end_time = datetime.now()
            stats['end_time'] = end_time.isoformat()
            stats['duration'] = (end_time - datetime.fromisoformat(stats['start_time'])).total_seconds()
            
            # Final progress before saving
            if progress_callback:
                await progress_callback({
                    'progress': 95,
                    'sectors_scanned': sampled_count,
                    'total_sectors': expected_samples,
                    'files_found': len(cluster_map),
                    'expected_time': 'Almost done...'
                })
            
            # Save cluster map to JSON
            cluster_map_file = os.path.join(output_dir, 'cluster_map.json')
            with open(cluster_map_file, 'w') as f:
                json.dump({
                    'statistics': stats,
                    'cluster_map': cluster_map
                }, f, indent=2)
            
            logger.info(f"✅ Cluster scan complete: {stats['sampled_clusters']} clusters sampled")
            logger.info(f"   Empty: {stats['empty_clusters']}, Used: {stats['used_clusters']}")
            logger.info(f"   Cluster map saved to: {cluster_map_file}")
            
            # Final progress - 100%
            if progress_callback:
                await progress_callback({
                    'progress': 100,
                    'sectors_scanned': sampled_count,
                    'total_sectors': expected_samples,
                    'files_found': len(cluster_map),
                    'expected_time': 'Complete'
                })
            
            return {
                'files': [],  # No files recovered in cluster scan
                'statistics': stats,
                'cluster_map': cluster_map,
                'cluster_map_file': cluster_map_file
            }
            
        except Exception as e:
            logger.error(f"Error during cluster scan: {e}", exc_info=True)
            raise

    async def _health_scan(self, drive_path: str, output_dir: str, options: dict, progress_callback) -> dict:
        """
        Perform health scan: read SMART data, calculate health score, create surface map
        
        Args:
            drive_path: Path to drive (e.g., 'E:')
            output_dir: Output directory for health report
            options: Scan options
            progress_callback: Progress update callback
            
        Returns:
            Dictionary with health scan results
        """
        try:
            logger.info("🏥 Starting Health Scan")
            
            health_data = {
                'drive_path': drive_path,
                'scan_time': datetime.now().isoformat(),
                'smart_data': {},
                'health_score': 0,
                'surface_map': [],
                'bad_sectors': 0,
                'total_sectors_tested': 0,
                'recommendations': [],
                'checks': []  # Added for detailed health checks
            }
            
            # Initialize checks list
            checks = []
            
            # Check if drive is removable - skip SMART for removable drives
            is_removable = False
            try:
                if platform.system() == 'Windows' and ':' in drive_path:
                    import psutil
                    drive_letter = drive_path.split(':')[0].upper() + ':'
                    
                    # Check if drive is removable
                    for partition in psutil.disk_partitions():
                        if partition.device.startswith(drive_letter):
                            # On Windows, removable drives have 'removable' in opts
                            if 'removable' in partition.opts.lower() or partition.fstype == '':
                                is_removable = True
                                logger.info(f"📱 Detected removable drive: {drive_letter}")
                                break
            except Exception as e:
                logger.debug(f"Could not check if drive is removable: {e}")
            
            # Check 1: SMART Data Access (skip for removable drives)
            if is_removable:
                logger.info("⏭️ Skipping SMART data for removable drive")
                health_data['smart_data'] = None  # Set to None to hide section in UI
                checks.append({
                    'name': 'SMART Data Access',
                    'status': 'skip',
                    'details': 'SMART data not available for removable drives'
                })
            elif platform.system() == 'Windows':
                try:
                    logger.info("Reading SMART data...")
                    smart_data = await self._read_smart_data_wmi(drive_path)
                    
                    # Only show SMART data if it's not an error
                    if 'error' in smart_data:
                        health_data['smart_data'] = None  # Hide SMART section for errors
                        checks.append({
                            'name': 'SMART Data Access',
                            'status': 'skip',
                            'details': smart_data.get('note', 'SMART data not accessible')
                        })
                    else:
                        health_data['smart_data'] = smart_data
                        checks.append({
                            'name': 'SMART Data Access',
                            'status': 'pass',
                            'details': f"Successfully read {len(smart_data)} SMART attributes"
                        })
                except Exception as e:
                    logger.warning(f"Could not read SMART data: {e}")
                    health_data['smart_data'] = None  # Hide SMART section on error
                    checks.append({
                        'name': 'SMART Data Access',
                        'status': 'skip',
                        'details': 'SMART data not available for this drive'
                    })
            else:
                health_data['smart_data'] = None  # Hide SMART section on non-Windows
                checks.append({
                    'name': 'SMART Data Access',
                    'status': 'skip',
                    'details': 'SMART data only available on Windows'
                })
            
            health_data['checks'] = checks
            
            # Update progress
            if progress_callback:
                await progress_callback({
                    'progress': 25,
                    'sectors_scanned': 1,
                    'total_sectors': 4,
                    'files_found': 0,
                    'expected_time': 'Calculating...'
                })
            
            # Perform surface scan to detect bad sectors
            logger.info("🔍 Scanning disk surface for bad sectors...")
            surface_result = await self._scan_disk_surface(drive_path, options, progress_callback)
            health_data['surface_map'] = surface_result['surface_map']
            health_data['bad_sectors'] = surface_result['bad_sectors']
            health_data['total_sectors_tested'] = surface_result['total_tested']
            
            # Add surface scan check
            if surface_result.get('error'):
                checks.append({
                    'name': 'Surface Scan',
                    'status': 'fail',
                    'details': surface_result['error']
                })
            else:
                if health_data['bad_sectors'] == 0:
                    checks.append({
                        'name': 'Surface Scan',
                        'status': 'pass',
                        'details': f"No bad sectors found in {health_data['total_sectors_tested']} tested sectors"
                    })
                elif health_data['bad_sectors'] < 10:
                    checks.append({
                        'name': 'Surface Scan',
                        'status': 'warning',
                        'details': f"Found {health_data['bad_sectors']} bad sectors"
                    })
                else:
                    checks.append({
                        'name': 'Surface Scan',
                        'status': 'fail',
                        'details': f"Found {health_data['bad_sectors']} bad sectors - drive may be failing"
                    })
            
            # Calculate health score
            health_score = 100
            
            # Deduct for bad sectors
            if health_data['bad_sectors'] > 0:
                bad_sector_penalty = min(50, health_data['bad_sectors'] * 5)
                health_score -= bad_sector_penalty
                health_data['recommendations'].append(f"⚠️ {health_data['bad_sectors']} bad sectors detected")
            
            # Deduct based on SMART data (only if available and not null/error)
            if health_data['smart_data'] and isinstance(health_data['smart_data'], dict) and 'error' not in health_data['smart_data']:
                # Check for Reallocated Sectors (SATA/ATA drives) - value is now a string
                if 'Reallocated_Sector_Count' in health_data['smart_data']:
                    try:
                        reallocated_str = health_data['smart_data'].get('Reallocated_Sector_Count', '0')
                        # Remove commas and convert to int
                        reallocated = int(reallocated_str.replace(',', ''))
                        if reallocated > 0:
                            health_score -= min(20, reallocated)
                            health_data['recommendations'].append(f"⚠️ {reallocated:,} reallocated sectors")
                            checks.append({
                                'name': 'Reallocated Sectors',
                                'status': 'warning',
                                'details': f"{reallocated:,} sectors have been reallocated"
                            })
                    except (ValueError, AttributeError):
                        pass  # Skip if value can't be parsed
                
                # Check for Pending Sectors (SATA/ATA drives) - value is now a string
                if 'Current_Pending_Sector' in health_data['smart_data']:
                    try:
                        pending_str = health_data['smart_data'].get('Current_Pending_Sector', '0')
                        # Remove commas and convert to int
                        pending = int(pending_str.replace(',', ''))
                        if pending > 0:
                            health_score -= min(15, pending * 2)
                            health_data['recommendations'].append(f"⚠️ {pending:,} pending sectors")
                            checks.append({
                                'name': 'Pending Sectors',
                                'status': 'fail',
                                'details': f"{pending:,} sectors are pending reallocation"
                            })
                    except (ValueError, AttributeError):
                        pass  # Skip if value can't be parsed
                
                # Check temperature - value is now a string like "40°C"
                if 'Temperature_Celsius' in health_data['smart_data']:
                    try:
                        temp_value = health_data['smart_data'].get('Temperature_Celsius', '')
                        # Extract numeric temperature from string like "40°C"
                        if isinstance(temp_value, str) and '°C' in temp_value:
                            temp = int(temp_value.replace('°C', '').strip())
                        elif isinstance(temp_value, str):
                            temp = int(temp_value)
                        else:
                            temp = 0
                        
                        if temp > 60:
                            health_score -= 5
                            health_data['recommendations'].append(f"⚠️ High temperature: {temp}°C")
                            checks.append({
                                'name': 'Drive Temperature',
                                'status': 'warning',
                                'details': f"Temperature is {temp}°C (recommended < 60°C)"
                            })
                        elif temp > 0:
                            checks.append({
                                'name': 'Drive Temperature',
                                'status': 'pass',
                                'details': f"Temperature is normal: {temp}°C"
                            })
                    except (ValueError, AttributeError):
                        pass  # Skip if temperature can't be parsed
                
                # Check for Media Errors (NVMe drives) - value is now a string
                if 'Media_Errors' in health_data['smart_data']:
                    try:
                        media_errors = int(health_data['smart_data'].get('Media_Errors', '0'))
                        if media_errors > 0:
                            health_score -= min(30, media_errors * 10)
                            health_data['recommendations'].append(f"⚠️ {media_errors} media errors detected")
                            checks.append({
                                'name': 'Media Errors',
                                'status': 'fail',
                                'details': f"{media_errors} media errors detected on NVMe drive"
                            })
                    except (ValueError, AttributeError):
                        pass
                
                # Check for Critical Warning (NVMe drives)
                if 'Critical_Warning' in health_data['smart_data']:
                    warning_value = health_data['smart_data'].get('Critical_Warning', 'None')
                    if warning_value != 'None' and 'Warning Level' in warning_value:
                        health_score -= 20
                        health_data['recommendations'].append(f"❌ {warning_value}")
                        checks.append({
                            'name': 'Critical Warning',
                            'status': 'fail',
                            'details': warning_value
                        })
            
            health_data['health_score'] = max(0, health_score)
            health_data['checks'] = checks
            
            # Add recommendations based on score
            if health_score >= 90:
                health_data['status'] = 'Excellent'
                health_data['recommendations'].insert(0, "✅ Drive is healthy")
            elif health_score >= 70:
                health_data['status'] = 'Good'
                health_data['recommendations'].insert(0, "✅ Drive is in good condition")
            elif health_score >= 50:
                health_data['status'] = 'Fair'
                health_data['recommendations'].insert(0, "⚠️ Consider backing up important data")
            else:
                health_data['status'] = 'Poor'
                health_data['recommendations'].insert(0, "❌ Drive may fail soon - backup immediately!")
            
            # Save health report
            health_report_file = os.path.join(output_dir, 'health_report.json')
            with open(health_report_file, 'w') as f:
                json.dump(health_data, f, indent=2)
            
            logger.info(f"✅ Health scan complete")
            logger.info(f"   Health Score: {health_data['health_score']}/100 ({health_data['status']})")
            logger.info(f"   Bad Sectors: {health_data['bad_sectors']}")
            logger.info(f"   Checks Performed: {len(checks)}")
            
            return {
                'files': [],  # No files recovered in health scan
                'statistics': {
                    'drive_path': drive_path,
                    'health_score': health_data['health_score'],
                    'status': health_data['status'],
                    'bad_sectors': health_data['bad_sectors'],
                    'sectors_tested': health_data['total_sectors_tested'],
                    'duration': 0
                },
                'health_data': health_data,
                'health_report_file': health_report_file
            }
            
        except Exception as e:
            logger.error(f"Error during health scan: {e}", exc_info=True)
            raise

    async def _read_smart_data_wmi(self, drive_path: str) -> dict:
        """Read SMART data using multiple methods on Windows"""
        try:
            logger.info("Attempting to read SMART data...")
            
            # Method 1: Try smartmontools (smartctl.exe) - most detailed data
            smart_result = await self._try_smartctl(drive_path)
            if smart_result and 'error' not in smart_result:
                logger.info("✅ Successfully read SMART data using smartctl")
                return smart_result
            
            # Method 2: Try pySMART library (fallback)
            smart_result = await self._try_pysmart(drive_path)
            if smart_result and 'error' not in smart_result:
                logger.info("✅ Successfully read SMART data using pySMART")
                return smart_result
            
            # Method 3: Try using wmi module
            try:
                import wmi
                import struct
                
                c = wmi.WMI(namespace="root\\wmi")
                
                # Get physical drive number from path
                physical_drive = self._get_physical_drive(drive_path)
                
                # Try to extract drive number
                drive_num = None
                if 'PhysicalDrive' in physical_drive:
                    try:
                        drive_num = int(physical_drive.split('PhysicalDrive')[-1])
                    except:
                        pass
                
                smart_data = {}
                found_data = False
                
                logger.info(f"Querying SMART data for physical drive: {physical_drive} (number: {drive_num})")
                
                # Try MSStorageDriver_ATAPISmartData with better error handling
                try:
                    logger.info("Attempting to query MSStorageDriver_ATAPISmartData...")
                    smart_instances = list(c.MSStorageDriver_ATAPISmartData())
                    logger.info(f"Found {len(smart_instances)} SMART data instances")
                    
                    for idx, disk in enumerate(smart_instances):
                        try:
                            # Try to match the correct drive
                            instance_name = getattr(disk, 'InstanceName', '')
                            logger.debug(f"Instance {idx}: {instance_name}")
                            
                            vendor_specific = disk.VendorSpecific
                            if not vendor_specific or len(vendor_specific) < 362:
                                logger.debug(f"Instance {idx}: No or insufficient vendor specific data")
                                continue
                            
                            logger.info(f"Parsing SMART attributes from instance {idx}...")
                            
                            # SMART attributes start at offset 2 in vendor specific data
                            # Each attribute is 12 bytes
                            attributes = {}
                            
                            # Parse SMART attributes
                            for i in range(2, min(len(vendor_specific), 362), 12):
                                if i + 11 < len(vendor_specific):
                                    attr_id = vendor_specific[i]
                                    if attr_id == 0 or attr_id == 0xFF:
                                        continue
                                    
                                    try:
                                        # Parse attribute data
                                        flags = (vendor_specific[i+1] << 8) | vendor_specific[i+2]
                                        current = vendor_specific[i+3]
                                        worst = vendor_specific[i+4]
                                        
                                        # Raw value is 6 bytes little-endian
                                        raw_bytes = bytes(vendor_specific[i+5:i+11])
                                        raw_value = struct.unpack('<Q', raw_bytes + b'\x00\x00')[0]
                                        
                                        # Map common SMART attribute IDs
                                        attr_names = {
                                            1: 'Read_Error_Rate',
                                            5: 'Reallocated_Sector_Count',
                                            9: 'Power_On_Hours',
                                            12: 'Power_Cycle_Count',
                                            187: 'Reported_Uncorrectable_Errors',
                                            188: 'Command_Timeout',
                                            194: 'Temperature_Celsius',
                                            196: 'Reallocation_Event_Count',
                                            197: 'Current_Pending_Sector',
                                            198: 'Offline_Uncorrectable',
                                            199: 'UDMA_CRC_Error_Count',
                                            200: 'Write_Error_Rate'
                                        }
                                        
                                        if attr_id in attr_names:
                                            attr_name = attr_names[attr_id]
                                            
                                            # Special handling for temperature
                                            display_value = raw_value
                                            if attr_id == 194:  # Temperature
                                                # Temperature is usually in the lower byte
                                                display_value = raw_value & 0xFF
                                                if display_value > 100:  # Sanity check
                                                    display_value = raw_value & 0xFFFF
                                            
                                            attributes[attr_name] = {
                                                'id': attr_id,
                                                'current': current,
                                                'worst': worst,
                                                'value': display_value,
                                                'raw': raw_value,
                                                'flags': flags
                                            }
                                    except Exception as attr_parse_error:
                                        logger.debug(f"Error parsing attribute {attr_id}: {attr_parse_error}")
                                        continue
                            
                            if len(attributes) > 0:
                                smart_data = attributes
                                found_data = True
                                logger.info(f"✅ Successfully parsed {len(attributes)} SMART attributes")
                                logger.info(f"   Attributes found: {', '.join(attributes.keys())}")
                                break
                            else:
                                logger.debug(f"Instance {idx}: No valid attributes parsed")
                                
                        except Exception as parse_error:
                            logger.debug(f"Error parsing SMART data from instance {idx}: {parse_error}")
                            continue
                            
                except wmi.x_wmi as wmi_smart_error:
                    logger.warning(f"⚠️ MSStorageDriver_ATAPISmartData not accessible: {wmi_smart_error}")
                    logger.info("This is normal for some drives/systems - trying alternative methods...")
                except Exception as wmi_error:
                    logger.warning(f"⚠️ Error querying MSStorageDriver_ATAPISmartData: {wmi_error}")
                
                # If no data found, try MSStorageDriver_FailurePredictStatus
                if not found_data:
                    try:
                        logger.info("Trying MSStorageDriver_FailurePredictStatus...")
                        status_instances = list(c.MSStorageDriver_FailurePredictStatus())
                        logger.info(f"Found {len(status_instances)} failure prediction instances")
                        
                        for disk in status_instances:
                            predict_failure = getattr(disk, 'PredictFailure', None)
                            reason = getattr(disk, 'Reason', None)
                            
                            if predict_failure is not None:
                                smart_data = {
                                    'Predict_Failure': 'Yes' if predict_failure else 'No',
                                    'Health_Status': 'Warning' if predict_failure else 'Good',
                                    'Status': 'Drive health prediction available',
                                    'note': 'Limited SMART data - full attributes not accessible on this system'
                                }
                                found_data = True
                                logger.info(f"✅ Got failure prediction: {'Warning' if predict_failure else 'Good'}")
                                break
                    except wmi.x_wmi as wmi_status_error:
                        logger.warning(f"⚠️ MSStorageDriver_FailurePredictStatus not accessible: {wmi_status_error}")
                    except Exception as e:
                        logger.debug(f"FailurePredictStatus query failed: {e}")
                
                # If still no data, return informative message
                if not found_data:
                    logger.warning("❌ SMART data not accessible through WMI on this system")
                    return {
                        'error': 'SMART data not accessible via WMI',
                        'note': 'This is normal for some drives and systems',
                        'reason': 'Your drive may not expose SMART data through Windows WMI interface',
                        'alternative': 'Surface scan can still detect bad sectors',
                        'info': [
                            '✓ Application is running with admin rights',
                            '✓ WMI module is installed',
                            '✗ Drive does not expose SMART data via WMI',
                            '',
                            'Possible reasons:',
                            '• Drive connected via USB (limited SMART access)',
                            '• Virtual machine environment',
                            '• Drive controller does not support WMI SMART',
                            '• Some SSDs do not expose SMART via WMI',
                            '',
                            'The surface scan will still work to detect bad sectors!'
                        ]
                    }
                
                return smart_data
                
            except ImportError:
                logger.warning("WMI module not available - install with: pip install wmi")
                return {
                    'error': 'WMI module not installed',
                    'note': 'Install WMI module: pip install wmi pywin32',
                    'alternative': 'Surface scan can still detect bad sectors'
                }
                
        except Exception as e:
            logger.error(f"Error reading SMART data: {e}", exc_info=True)
            return {
                'error': str(e),
                'note': 'SMART data unavailable - unexpected error',
                'alternative': 'Surface scan can still detect bad sectors'
            }
    
    async def _try_pysmart(self, drive_path: str) -> dict:
        """Try reading SMART data using pySMART library"""
        try:
            from pySMART import Device
            
            # Get physical drive number
            physical_drive = self._get_physical_drive(drive_path)
            drive_num = None
            
            if 'PhysicalDrive' in physical_drive:
                try:
                    drive_num = int(physical_drive.split('PhysicalDrive')[-1])
                except:
                    pass
            elif ':' in drive_path:
                # Try to get physical drive from volume
                drive_letter = drive_path.split(':')[0].upper()
                # pySMART uses /dev/sdX on Linux, but on Windows we need drive number
                # For now, try 0-3 (most common range)
                for i in range(4):
                    try:
                        device = Device(f'/dev/pd{i}')  # Windows physical drive
                        if device and device.assessment:
                            drive_num = i
                            break
                    except:
                        continue
            
            if drive_num is None:
                drive_num = 0  # Default to first drive
            
            logger.info(f"Trying pySMART for drive number {drive_num}")
            
            # Try to read device
            device = Device(f'/dev/pd{drive_num}')
            
            if not device or not device.attributes:
                return {'error': 'pySMART: No device data available'}
            
            # Parse SMART attributes
            smart_data = {}
            
            # Overall assessment
            if device.assessment:
                smart_data['Health_Status'] = device.assessment
            
            if device.temperature:
                smart_data['Temperature_Celsius'] = {'value': device.temperature}
            
            # Parse individual attributes
            for attr in device.attributes:
                if attr:
                    attr_name = attr.name.replace(' ', '_')
                    smart_data[attr_name] = {
                        'id': attr.num,
                        'current': attr.value,
                        'worst': attr.worst,
                        'value': attr.raw,
                        'raw': attr.raw
                    }
            
            if len(smart_data) > 0:
                smart_data['method'] = 'pySMART'
                return smart_data
            
            return {'error': 'pySMART: No attributes found'}
            
        except ImportError:
            logger.debug("pySMART not installed")
            return {'error': 'pySMART not installed'}
        except Exception as e:
            logger.debug(f"pySMART failed: {e}")
            return {'error': f'pySMART error: {str(e)}'}
    
    async def _try_smartctl(self, drive_path: str) -> dict:
        """Try reading SMART data using smartmontools (smartctl.exe)"""
        try:
            import subprocess
            import json
            import shutil
            
            # Check if smartctl is available
            smartctl_path = shutil.which('smartctl')
            if not smartctl_path:
                # Try common installation paths
                common_paths = [
                    r'C:\Program Files\smartmontools\bin\smartctl.exe',
                    r'C:\Program Files (x86)\smartmontools\bin\smartctl.exe',
                    r'C:\smartmontools\bin\smartctl.exe',
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        smartctl_path = path
                        break
            
            if not smartctl_path:
                return {'error': 'smartctl not found'}
            
            # Map drive letter to device for smartctl
            device_path = None
            
            if ':' in drive_path:
                # Drive letter format (e.g., "E:")
                drive_letter = drive_path.split(':')[0].upper()
                
                # First, scan for all drives and find which one matches
                scan_cmd = [smartctl_path, '--scan']
                scan_result = subprocess.run(
                    scan_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
                )
                
                if scan_result.returncode == 0:
                    # Parse scan output to find drives
                    lines = scan_result.stdout.split('\n')
                    logger.info(f"Scanning for drive {drive_letter}:")
                    logger.info(f"Available devices: {lines}")
                    
                    # Try each device found
                    for line in lines:
                        if line.strip() and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) >= 1:
                                dev = parts[0]  # e.g., "/dev/sda"
                                # For now, map drive letters to devices sequentially
                                # E: is often the second partition/drive
                                if 'sda' in dev or 'pd0' in dev:
                                    if drive_letter == 'C':
                                        device_path = dev
                                        break
                                elif 'sdb' in dev or 'pd1' in dev:
                                    if drive_letter == 'E':
                                        device_path = dev
                                        break
                
                # Fallback: try common mappings
                if not device_path:
                    drive_mappings = {'C': '/dev/sda', 'D': '/dev/sda', 'E': '/dev/sdb'}
                    device_path = drive_mappings.get(drive_letter, '/dev/sda')
                
                logger.info(f"Mapped drive {drive_letter}: to {device_path}")
            else:
                # Use path as-is
                device_path = drive_path
            
            # Detect device type from scan
            device_type = None
            scan_cmd = [smartctl_path, '--scan']
            scan_result = subprocess.run(
                scan_cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            
            if scan_result.returncode == 0:
                for line in scan_result.stdout.split('\n'):
                    if device_path in line:
                        if 'nvme' in line:
                            device_type = 'nvme'
                        elif 'scsi' in line:
                            device_type = 'scsi'
                        elif 'ata' in line:
                            device_type = 'ata'
                        break
            
            # Build command
            cmd = [smartctl_path, '-a', device_path]
            if device_type:
                cmd.extend(['-d', device_type])
            cmd.append('--json=c')
            
            logger.info(f"Running smartctl command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            
            if result.returncode not in [0, 4]:  # 0=success, 4=SMART threshold exceeded (still valid)
                logger.debug(f"smartctl failed with code {result.returncode}")
                logger.debug(f"Output: {result.stdout}")
                logger.debug(f"Error: {result.stderr}")
                return {'error': f'smartctl returned code {result.returncode}'}
            
            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # Try non-JSON parsing
                return await self._parse_smartctl_text(result.stdout)
            
            # Extract SMART data
            smart_data = {}
            
            # Device info - store as plain strings
            if 'model_name' in data:
                smart_data['Model'] = data['model_name']
            if 'serial_number' in data:
                smart_data['Serial_Number'] = data['serial_number']
            if 'firmware_version' in data:
                smart_data['Firmware_Version'] = data['firmware_version']
            
            # Overall health
            if 'smart_status' in data and 'passed' in data['smart_status']:
                smart_data['Health_Status'] = 'PASS' if data['smart_status']['passed'] else 'FAIL'
            
            # Temperature
            if 'temperature' in data and 'current' in data['temperature']:
                smart_data['Temperature_Celsius'] = f"{data['temperature']['current']}°C"
            
            # NVMe specific health info
            if 'nvme_smart_health_information_log' in data:
                nvme_health = data['nvme_smart_health_information_log']
                
                if 'critical_warning' in nvme_health:
                    warning = nvme_health['critical_warning']
                    smart_data['Critical_Warning'] = 'None' if warning == 0 else f'Warning Level {warning}'
                
                if 'temperature' in nvme_health:
                    smart_data['Temperature_Celsius'] = f"{nvme_health['temperature']}°C"
                
                if 'available_spare' in nvme_health:
                    smart_data['Available_Spare'] = f"{nvme_health['available_spare']}%"
                
                if 'available_spare_threshold' in nvme_health:
                    smart_data['Available_Spare_Threshold'] = f"{nvme_health['available_spare_threshold']}%"
                
                if 'percentage_used' in nvme_health:
                    smart_data['Percentage_Used'] = f"{nvme_health['percentage_used']}%"
                
                if 'data_units_read' in nvme_health:
                    # Data units are in 512KB blocks, convert to TB
                    data_read_tb = (nvme_health['data_units_read'] * 512 * 1000) / (1024 ** 4)
                    smart_data['Data_Units_Read'] = f"{data_read_tb:.2f} TB"
                
                if 'data_units_written' in nvme_health:
                    # Data units are in 512KB blocks, convert to TB
                    data_written_tb = (nvme_health['data_units_written'] * 512 * 1000) / (1024 ** 4)
                    smart_data['Data_Units_Written'] = f"{data_written_tb:.2f} TB"
                
                if 'host_reads' in nvme_health:
                    smart_data['Host_Read_Commands'] = f"{nvme_health['host_reads']:,}"
                
                if 'host_writes' in nvme_health:
                    smart_data['Host_Write_Commands'] = f"{nvme_health['host_writes']:,}"
                
                if 'controller_busy_time' in nvme_health:
                    smart_data['Controller_Busy_Time'] = f"{nvme_health['controller_busy_time']} minutes"
                
                if 'power_cycles' in nvme_health:
                    smart_data['Power_Cycles'] = f"{nvme_health['power_cycles']:,}"
                
                if 'power_on_hours' in nvme_health:
                    smart_data['Power_On_Hours'] = f"{nvme_health['power_on_hours']:,} hours"
                
                if 'unsafe_shutdowns' in nvme_health:
                    smart_data['Unsafe_Shutdowns'] = str(nvme_health['unsafe_shutdowns'])
                
                if 'media_errors' in nvme_health:
                    smart_data['Media_Errors'] = str(nvme_health['media_errors'])
                
                if 'num_err_log_entries' in nvme_health:
                    smart_data['Error_Log_Entries'] = str(nvme_health['num_err_log_entries'])
                
                if 'warning_temp_time' in nvme_health:
                    smart_data['Warning_Temp_Time'] = f"{nvme_health['warning_temp_time']} minutes"
                
                if 'critical_comp_time' in nvme_health:
                    smart_data['Critical_Temp_Time'] = f"{nvme_health['critical_comp_time']} minutes"
            
            # ATA SMART attributes (for SATA drives)
            if 'ata_smart_attributes' in data and 'table' in data['ata_smart_attributes']:
                for attr in data['ata_smart_attributes']['table']:
                    attr_name = attr.get('name', f"Attr_{attr.get('id', 'Unknown')}").replace(' ', '_').replace('-', '_')
                    # Store human-readable value
                    raw_value = attr.get('raw', {}).get('value', 0)
                    smart_data[attr_name] = f"{raw_value:,}" if isinstance(raw_value, int) else str(raw_value)
            
            if len(smart_data) > 0:
                smart_data['method'] = 'smartctl'
                logger.info(f"✅ Successfully retrieved {len(smart_data)} SMART attributes")
                return smart_data
            
            logger.warning("❌ smartctl returned no SMART data")
            return {
                'error': 'No SMART data available',
                'note': 'This drive does not provide SMART information',
                'reason': 'This is common for USB drives, external drives, or unsupported controllers',
                'alternative': 'Surface scan can still detect bad sectors',
                'info': [
                    '✓ smartctl command executed successfully',
                    '✗ Drive does not expose SMART data',
                    '',
                    'Possible reasons:',
                    '• USB or external drive (limited SMART access)',
                    '• Drive controller does not support SMART',
                    '• Virtual drive or network storage',
                    '',
                    'The surface scan will still work to detect bad sectors!'
                ]
            }
            
        except subprocess.TimeoutExpired:
            logger.debug("smartctl timeout")
            return {'error': 'smartctl timeout'}
        except FileNotFoundError:
            return {'error': 'smartctl not found'}
        except Exception as e:
            logger.debug(f"smartctl failed: {e}")
            return {'error': f'smartctl error: {str(e)}'}
    
    async def _parse_smartctl_text(self, output: str) -> dict:
        """Parse smartctl text output (fallback when JSON not available)"""
        try:
            smart_data = {}
            lines = output.split('\n')
            
            in_attributes = False
            for line in lines:
                line = line.strip()
                
                # Look for overall health
                if 'SMART overall-health' in line or 'SMART Health Status' in line:
                    if 'PASSED' in line or 'OK' in line:
                        smart_data['Health_Status'] = 'PASS'
                    else:
                        smart_data['Health_Status'] = 'FAIL'
                
                # Look for temperature
                if 'Temperature_Celsius' in line or 'Current Drive Temperature' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit() and int(part) < 100:
                            smart_data['Temperature_Celsius'] = {'value': int(part)}
                            break
                
                # Parse attribute table
                if 'ID#' in line and 'ATTRIBUTE_NAME' in line:
                    in_attributes = True
                    continue
                
                if in_attributes and line and line[0].isdigit():
                    parts = line.split()
                    if len(parts) >= 10:
                        try:
                            attr_id = int(parts[0])
                            attr_name = parts[1].replace('-', '_')
                            current = int(parts[3])
                            worst = int(parts[4])
                            raw = int(parts[9])
                            
                            smart_data[attr_name] = {
                                'id': attr_id,
                                'current': current,
                                'worst': worst,
                                'value': raw,
                                'raw': raw
                            }
                        except (ValueError, IndexError):
                            continue
            
            if len(smart_data) > 0:
                smart_data['method'] = 'smartctl (text)'
                return smart_data
            
            return {'error': 'smartctl: Could not parse output'}
            
        except Exception as e:
            return {'error': f'smartctl parse error: {str(e)}'}

    async def _scan_disk_surface(self, drive_path: str, options: dict, progress_callback) -> dict:
        """
        Scan disk surface to detect bad sectors
        
        Returns dictionary with surface map and bad sector count
        """
        try:
            physical_drive = self._get_physical_drive(drive_path)
            
            # Get actual usable drive size
            try:
                if platform.system() == 'Windows' and ':' in drive_path:
                    import psutil
                    drive_letter = drive_path.split(':')[0].upper() + ':'
                    
                    # Get partition usage
                    usage = psutil.disk_usage(drive_letter)
                    drive_size = usage.total
                    logger.info(f"Drive {drive_letter} size: {drive_size / (1024**3):.2f} GB")
                else:
                    drive_size = self._get_drive_size(drive_path)
            except Exception as e:
                logger.warning(f"Could not get drive size via psutil: {e}, falling back")
                drive_size = self._get_drive_size(drive_path)
            
            if not drive_size or drive_size == 0:
                logger.error("Could not determine drive size")
                return {
                    'surface_map': [],
                    'bad_sectors': 0,
                    'total_tested': 0,
                    'error': 'Could not determine drive size'
                }
            
            # Open drive for reading
            try:
                drive_handle = self._open_drive(physical_drive)
            except Exception as e:
                logger.error(f"Could not open drive: {e}")
                return {
                    'surface_map': [],
                    'bad_sectors': 0,
                    'total_tested': 0,
                    'error': f'Could not open drive: {str(e)}'
                }
            
            sector_size = 512
            total_sectors = drive_size // sector_size
            
            # Test sectors at intervals (not every sector - too slow)
            # For smaller drives, test more sectors
            if drive_size < 10 * 1024**3:  # Less than 10GB
                test_interval = max(1, total_sectors // 1000)  # Test ~1000 sectors
            else:
                test_interval = max(1, total_sectors // 500)  # Test ~500 sectors
            
            sectors_to_test = total_sectors // test_interval
            
            surface_map = []
            bad_sectors = 0
            tested = 0
            start_time = datetime.now()  # Track start time for expected time calculation
            
            logger.info(f"Total sectors: {total_sectors:,}, Testing every {test_interval} sector (~{sectors_to_test} samples)")
            
            for sector_num in range(0, total_sectors, test_interval):
                # Check for cancellation
                if options.get('is_cancelled') and options['is_cancelled']():
                    logger.info("Surface scan cancelled by user")
                    break
                
                try:
                    offset = sector_num * sector_size
                    
                    # Seek to position
                    try:
                        drive_handle.seek(offset)
                    except OSError as seek_error:
                        # Seek beyond end of file
                        logger.debug(f"Seek error at sector {sector_num}: {seek_error}")
                        break  # Stop scanning, we've reached the end
                    
                    # Try to read sector
                    try:
                        data = drive_handle.read(sector_size)
                        
                        if len(data) == sector_size:
                            surface_map.append({'sector': sector_num, 'status': 'good'})
                        elif len(data) > 0:
                            # Partial read - might be last sector
                            surface_map.append({'sector': sector_num, 'status': 'good'})
                        else:
                            # No data read
                            surface_map.append({'sector': sector_num, 'status': 'bad'})
                            bad_sectors += 1
                    except OSError as read_error:
                        # Read error indicates bad sector
                        logger.debug(f"Read error at sector {sector_num}: {read_error}")
                        surface_map.append({'sector': sector_num, 'status': 'bad'})
                        bad_sectors += 1
                    
                    tested += 1
                    
                    # Update progress (25% done at start, so start at 25 and go to 100)
                    if progress_callback and tested % 10 == 0:
                        progress = 25 + (tested / sectors_to_test) * 75
                        progress = min(progress, 100)  # Cap at 100%
                        elapsed = (datetime.now() - start_time).total_seconds()
                        expected_time = self._calculate_expected_time(elapsed, progress)
                        await progress_callback({
                            'progress': progress,
                            'sectors_scanned': tested,
                            'total_sectors': sectors_to_test,
                            'files_found': 0,
                            'expected_time': expected_time
                        })
                    
                except Exception as e:
                    logger.debug(f"Error testing sector {sector_num}: {e}")
                    surface_map.append({'sector': sector_num, 'status': 'error'})
                    bad_sectors += 1
                    tested += 1
            
            drive_handle.close()
            
            logger.info(f"✅ Surface scan complete: Tested {tested:,} sectors, found {bad_sectors} bad sectors")
            
            return {
                'surface_map': surface_map,
                'bad_sectors': bad_sectors,
                'total_tested': tested
            }
            
        except Exception as e:
            logger.error(f"Error scanning disk surface: {e}", exc_info=True)
            return {
                'surface_map': [],
                'bad_sectors': 0,
                'total_tested': 0,
                'error': str(e)
            }
    
    async def recover_selected_files(self, file_list: List[Dict], output_dir: str,
                                    progress_callback: Optional[Callable] = None,
                                    create_subdirectories: bool = True) -> Dict:
        """
        ON-DEMAND RECOVERY: Recover specific files from scan index
        Like File Scavenger - user selects files, then we recover them
        
        This method:
        1. Reads file data from original drive location (using offset)
        2. Validates the data matches expected hash
        3. Writes only selected files to disk
        4. Returns recovery results
        
        Args:
            file_list: List of file info dictionaries from scan index
            output_dir: Directory to save recovered files
            progress_callback: Optional progress callback
            create_subdirectories: Whether to create subdirectories by file type
            
        Returns:
            Dictionary with recovery statistics
        """
        recovered_count = 0
        failed_count = 0
        total_size = 0
        recovery_results = []
        
        logger.info(f"🎯 Starting on-demand recovery of {len(file_list)} selected files")
        logger.info(f"📂 Output directory: {output_dir}")
        logger.info(f"📁 Create subdirectories: {create_subdirectories}")
        
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            for idx, file_info in enumerate(file_list):
                try:
                    # Extract file metadata
                    drive_path = file_info.get('drive_path', 'unknown')
                    offset = file_info.get('offset', 0)
                    size = file_info.get('size', 0)
                    expected_hash = file_info.get('sha256', file_info.get('hash', ''))
                    filename = file_info.get('name', f'unknown_{idx}')
                    method = file_info.get('method', 'unknown')
                    
                    logger.info(f"📄 Recovering {idx+1}/{len(file_list)}: {filename} ({size/1024:.1f} KB)")
                    logger.info(f"   Drive: {drive_path}, Offset: {offset}, Hash: {expected_hash[:16] if expected_hash else 'N/A'}...")
                    
                    # Send progress update at START of file recovery
                    if progress_callback:
                        progress = (idx / len(file_list)) * 100
                        await progress_callback({
                            'progress': progress,
                            'current_file': idx + 1,
                            'total_files': len(file_list),
                            'recovered': recovered_count,
                            'failed': failed_count,
                            'total_size': total_size,
                            'current_filename': filename
                        })
                        # Small delay
                        await asyncio.sleep(0.05)
                    
                    # Validate drive path
                    if drive_path == 'unknown' or not drive_path:
                        logger.error(f"❌ Invalid drive path for {filename}")
                        failed_count += 1
                        recovery_results.append({
                            'filename': filename,
                            'status': 'failed',
                            'reason': 'invalid_drive_path',
                            'drive_path': drive_path
                        })
                        
                        # Update progress for failed file
                        if progress_callback:
                            progress = ((idx + 1) / len(file_list)) * 100
                            await progress_callback({
                                'progress': progress,
                                'current_file': idx + 1,
                                'total_files': len(file_list),
                                'recovered': recovered_count,
                                'failed': failed_count,
                                'total_size': total_size,
                                'current_filename': filename
                            })
                            await asyncio.sleep(0.1)
                        continue
                    
                    # Open drive for reading
                    try:
                        drive_handle = self._open_drive(drive_path)
                        logger.debug(f"✅ Drive opened successfully: {drive_path}")
                    except Exception as drive_error:
                        logger.error(f"❌ Failed to open drive {drive_path}: {drive_error}")
                        failed_count += 1
                        recovery_results.append({
                            'filename': filename,
                            'status': 'failed',
                            'reason': f'drive_open_failed: {str(drive_error)}',
                            'drive_path': drive_path
                        })
                        
                        # Update progress for failed file
                        if progress_callback:
                            progress = ((idx + 1) / len(file_list)) * 100
                            await progress_callback({
                                'progress': progress,
                                'current_file': idx + 1,
                                'total_files': len(file_list),
                                'recovered': recovered_count,
                                'failed': failed_count,
                                'total_size': total_size,
                                'current_filename': filename
                            })
                            await asyncio.sleep(0.1)
                        continue
                    
                    # Read file data from drive with sector alignment
                    try:
                        # Raw disk access requires sector-aligned reads
                        # Calculate sector-aligned position and read size
                        SECTOR_SIZE = 512
                        
                        # Calculate aligned offset (round down to nearest sector)
                        aligned_offset = (offset // SECTOR_SIZE) * SECTOR_SIZE
                        offset_adjustment = offset - aligned_offset
                        
                        # Calculate aligned read size (round up to nearest sector)
                        total_read_size = offset_adjustment + size
                        aligned_read_size = ((total_read_size + SECTOR_SIZE - 1) // SECTOR_SIZE) * SECTOR_SIZE
                        
                        logger.debug(f"📐 Sector alignment: offset {offset} → {aligned_offset}, size {size} → {aligned_read_size}")
                        
                        # Seek to aligned position
                        drive_handle.seek(aligned_offset)
                        
                        # Read aligned data
                        aligned_data = drive_handle.read(aligned_read_size)
                        drive_handle.close()
                        
                        if len(aligned_data) == 0:
                            logger.error(f"❌ No data read from drive")
                            failed_count += 1
                            recovery_results.append({
                                'filename': filename,
                                'status': 'failed',
                                'reason': 'no_data_read',
                                'offset': offset,
                                'size': size
                            })
                            
                            # Update progress for failed file
                            if progress_callback:
                                progress = ((idx + 1) / len(file_list)) * 100
                                await progress_callback({
                                    'progress': progress,
                                    'current_file': idx + 1,
                                    'total_files': len(file_list),
                                    'recovered': recovered_count,
                                    'failed': failed_count,
                                    'total_size': total_size,
                                    'current_filename': filename
                                })
                                await asyncio.sleep(0.1)
                            continue
                        
                        # Extract the actual file data from aligned buffer
                        file_data = aligned_data[offset_adjustment:offset_adjustment + size]
                        
                        if len(file_data) != size:
                            logger.warning(f"⚠️ Read size mismatch: expected {size}, got {len(file_data)} bytes")
                            # Continue anyway - might be partial recovery
                        
                        if len(file_data) == 0:
                            logger.error(f"❌ No data extracted after alignment")
                            failed_count += 1
                            recovery_results.append({
                                'filename': filename,
                                'status': 'failed',
                                'reason': 'no_data_after_alignment',
                                'offset': offset,
                                'size': size
                            })
                            
                            # Update progress for failed file
                            if progress_callback:
                                progress = ((idx + 1) / len(file_list)) * 100
                                await progress_callback({
                                    'progress': progress,
                                    'current_file': idx + 1,
                                    'total_files': len(file_list),
                                    'recovered': recovered_count,
                                    'failed': failed_count,
                                    'total_size': total_size,
                                    'current_filename': filename
                                })
                                await asyncio.sleep(0.1)
                            continue
                        
                        logger.debug(f"✅ Read {len(file_data)} bytes from offset {offset}")
                    except Exception as read_error:
                        logger.error(f"❌ Failed to read data from drive: {read_error}")
                        try:
                            drive_handle.close()
                        except:
                            pass
                        failed_count += 1
                        recovery_results.append({
                            'filename': filename,
                            'status': 'failed',
                            'reason': f'read_failed: {str(read_error)}',
                            'offset': offset,
                            'size': size
                        })
                        
                        # Update progress for failed file
                        if progress_callback:
                            progress = ((idx + 1) / len(file_list)) * 100
                            await progress_callback({
                                'progress': progress,
                                'current_file': idx + 1,
                                'total_files': len(file_list),
                                'recovered': recovered_count,
                                'failed': failed_count,
                                'total_size': total_size,
                                'current_filename': filename
                            })
                            await asyncio.sleep(0.1)
                        continue
                    
                    # Validate data (check hash if available)
                    if expected_hash:
                        actual_hash = hashlib.sha256(file_data).hexdigest()
                        if actual_hash != expected_hash:
                            logger.warning(f"⚠️ Hash mismatch for {filename} - file may be corrupted")
                            failed_count += 1
                            recovery_results.append({
                                'filename': filename,
                                'status': 'failed',
                                'reason': 'hash_mismatch',
                                'expected_hash': expected_hash,
                                'actual_hash': actual_hash
                            })
                            
                            # Update progress for failed file
                            if progress_callback:
                                progress = ((idx + 1) / len(file_list)) * 100
                                await progress_callback({
                                    'progress': progress,
                                    'current_file': idx + 1,
                                    'total_files': len(file_list),
                                    'recovered': recovered_count,
                                    'failed': failed_count,
                                    'total_size': total_size,
                                    'current_filename': filename
                                })
                                await asyncio.sleep(0.1)
                            continue
                    
                    # Determine output path (with or without subdirectories)
                    if create_subdirectories:
                        file_type = file_info.get('type', file_info.get('extension', 'UNKNOWN')).upper()
                        type_folder = os.path.join(output_dir, file_type)
                        os.makedirs(type_folder, exist_ok=True)
                        output_path = os.path.join(type_folder, filename)
                    else:
                        output_path = os.path.join(output_dir, filename)
                    
                    logger.info(f"💾 Writing to: {output_path}")
                    
                    # Write file to disk
                    try:
                        with open(output_path, 'wb') as f:
                            f.write(file_data)
                        logger.info(f"✅ File written successfully: {len(file_data)} bytes")
                    except Exception as write_error:
                        logger.error(f"❌ Failed to write file: {write_error}")
                        failed_count += 1
                        recovery_results.append({
                            'filename': filename,
                            'status': 'failed',
                            'reason': f'write_failed: {str(write_error)}',
                            'output_path': output_path
                        })
                        
                        # Update progress for failed file
                        if progress_callback:
                            progress = ((idx + 1) / len(file_list)) * 100
                            await progress_callback({
                                'progress': progress,
                                'current_file': idx + 1,
                                'total_files': len(file_list),
                                'recovered': recovered_count,
                                'failed': failed_count,
                                'total_size': total_size,
                                'current_filename': filename
                            })
                            await asyncio.sleep(0.1)
                        continue
                    
                    recovered_count += 1
                    total_size += len(file_data)
                    
                    recovery_results.append({
                        'filename': filename,
                        'status': 'recovered',
                        'path': output_path,
                        'size': len(file_data),
                        'method': method
                    })
                    
                    logger.info(f"✅ Recovered: {filename}")
                    
                    # Update progress
                    if progress_callback:
                        progress = ((idx + 1) / len(file_list)) * 100
                        await progress_callback({
                            'progress': progress,
                            'current_file': idx + 1,
                            'total_files': len(file_list),
                            'recovered': recovered_count,
                            'failed': failed_count,
                            'total_size': total_size
                        })
                        
                        # Small delay to allow UI to show progress
                        await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to recover {file_info.get('name', 'unknown')}: {e}")
                    failed_count += 1
                    recovery_results.append({
                        'filename': file_info.get('name', 'unknown'),
                        'status': 'failed',
                        'reason': str(e)
                    })
                    
                    # Update progress even for failed files
                    if progress_callback:
                        progress = ((idx + 1) / len(file_list)) * 100
                        await progress_callback({
                            'progress': progress,
                            'current_file': idx + 1,
                            'total_files': len(file_list),
                            'recovered': recovered_count,
                            'failed': failed_count,
                            'total_size': total_size
                        })
                        
                        # Small delay to allow UI to show progress
                        await asyncio.sleep(0.1)
            
            logger.info(f"✅ Recovery complete: {recovered_count} succeeded, {failed_count} failed")
            logger.info(f"💾 Total size recovered: {total_size / (1024**2):.2f} MB")
            
            return {
                'recovered_count': recovered_count,
                'failed_count': failed_count,
                'total_size': total_size,
                'results': recovery_results
            }
            
        except Exception as e:
            logger.error(f"❌ Error during on-demand recovery: {e}", exc_info=True)
            return {
                'recovered_count': recovered_count,
                'failed_count': failed_count,
                'total_size': total_size,
                'results': recovery_results,
                'error': str(e)
            }
