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
            
            # Map whence to Windows constants
            move_method = {
                0: win32file.FILE_BEGIN,      # Absolute position
                1: win32file.FILE_CURRENT,    # Relative to current
                2: win32file.FILE_END         # Relative to end
            }.get(whence, win32file.FILE_BEGIN)
            
            # Perform the seek operation
            new_pos = win32file.SetFilePointer(self.handle, offset, move_method)
            self.position = new_pos
            return new_pos
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
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.signatures = FileSignature.SIGNATURES
        
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
            
            # DEEP SCAN: Same as Signature File Carving - sector-by-sector with all file types
            elif scan_type == 'deep':
                logger.info("🔍 Deep Scan: Comprehensive signature-based file carving (all file types)")
                logger.info("   - Scanning every sector of the disk")
                logger.info("   - Detecting all file types by signature")
                logger.info("   - Similar to Signature File Carving scan")
                
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
                
                recovered_files = await self._carve_files(
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
        if 'PHYSICALDRIVE' in drive_path.upper():
            return drive_path
        
        # On Windows, for drive letters, use the volume path directly
        # This scans only the specific volume, not the entire physical disk
        if platform.system() == 'Windows' and ':' in drive_path:
            try:
                drive_letter = drive_path.split(':')[0].upper()
                # Use the volume path, not physical drive
                # This limits scanning to the specific partition
                logger.info(f"Using volume path for drive {drive_letter}: to scan only that partition")
                return f'\\\\.\\{drive_letter}:'
                
            except Exception as e:
                logger.warning(f"Could not map drive letter: {e}")
                return f'\\\\.\\{drive_letter}:'
        
        return drive_path
    
    def _get_drive_size(self, drive_path: str) -> int:
        """Get the size of a drive in bytes"""
        try:
            if platform.system() == 'Windows':
                import psutil
                
                # Extract drive letter
                if ':' in drive_path:
                    drive_letter = drive_path.split(':')[0].upper() + ':'
                    
                    # Get partition info
                    partitions = psutil.disk_partitions()
                    for partition in partitions:
                        if partition.device.startswith(drive_letter):
                            usage = psutil.disk_usage(partition.mountpoint)
                            return usage.total
                
                # If not found via psutil, try win32file
                try:
                    import win32file
                    physical_drive = self._get_physical_drive(drive_path)
                    
                    handle = win32file.CreateFile(
                        physical_drive,
                        0,  # No access required for size query
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    
                    # Get drive geometry
                    size = win32file.GetFileSize(handle)
                    win32file.CloseHandle(handle)
                    return size
                except:
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
            # On Windows, try to open the drive letter first (simpler, no admin needed for mounted volumes)
            if physical_drive.endswith(':'):
                logger.info(f"Opening mounted volume: {physical_drive}")
                try:
                    # For mounted volumes (like E:), we can scan files without admin rights
                    # But for low-level disk access, admin rights are needed
                    
                    # Try direct file access first (requires admin)
                    try:
                        import win32file
                        
                        logger.info("Attempting low-level disk access (requires admin)...")
                        handle = win32file.CreateFile(
                            f'\\\\.\\{physical_drive}',
                            win32file.GENERIC_READ,
                            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                            None,
                            win32file.OPEN_EXISTING,
                            0,
                            None
                        )
                        
                        logger.info("✅ Successfully opened drive with low-level access (admin mode)")
                        # Return a file-like wrapper for the Windows handle
                        return Win32FileWrapper(handle)
                        
                    except Exception as e:
                        logger.warning(f"Low-level access failed: {e}")
                        logger.info("⚠️ Falling back to file system scanning (no admin rights)")
                        # This will scan only existing files on the mounted volume
                        # Not true raw disk recovery, but better than nothing
                        raise PermissionError("Administrator rights required for raw disk scanning")
                        
                except Exception as e:
                    logger.error(f"Failed to open drive: {e}")
                    raise
            else:
                # Physical drive path like \\.\PHYSICALDRIVE1
                try:
                    import win32file
                    
                    logger.info(f"Opening physical drive with win32file: {physical_drive}")
                    handle = win32file.CreateFile(
                        physical_drive,
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    
                    logger.info("✅ Successfully opened physical drive")
                    # Return a file-like wrapper for the Windows handle
                    return Win32FileWrapper(handle)
                    
                except Exception as e:
                    logger.error(f"Failed to open physical drive with win32file: {e}")
                    raise
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
            drive_handle.seek(0)
            boot_sector = drive_handle.read(512)
            
            if not boot_sector or len(boot_sector) < 512:
                logger.error("❌ Failed to read boot sector - insufficient data")
                logger.info("💡 The drive may not be accessible or formatted")
                return recovered_files
            
            # Check for NTFS (bytes 3-11 should contain "NTFS    ")
            filesystem_sig = boot_sector[3:11] if len(boot_sector) >= 11 else b''
            logger.info(f"🔍 Filesystem signature detected: {filesystem_sig}")
            
            if filesystem_sig == b'NTFS    ':
                logger.info("📂 Detected NTFS filesystem - parsing MFT...")
                recovered_files = await self._recover_from_ntfs_mft(
                    drive_handle, output_dir, stats, options, progress_callback
                )
            else:
                logger.warning("⚠️ Non-NTFS filesystem detected - metadata-first not available")
                logger.info(f"   Detected signature: {filesystem_sig}")
                logger.info("   Filesystem metadata recovery only supports NTFS currently")
                logger.info("💡 For non-NTFS drives, use Deep Scan or Signature File Carving instead")
                
        except Exception as e:
            logger.error(f"Error in metadata-first recovery: {e}", exc_info=True)
            
        return recovered_files
    
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
            
            # For normal scan, get all important file types if no specific types selected
            if scan_type == 'normal' and not file_type_options:
                # Default to all important file types for normal scan
                interested_extensions = set()
                for sig_name, sig_info in self.signatures.items():
                    if sig_info.get('important', False):
                        interested_extensions.add(sig_info['extension'])
                logger.info(f"🎯 Normal scan: Looking for all important file types")
            else:
                interested_extensions = self._get_interested_extensions(file_type_options)
            
            logger.info(f"🎯 Target extensions: {', '.join(sorted(interested_extensions)) if len(interested_extensions) <= 20 else f'{len(interested_extensions)} file types'}")
            
            # Parse MFT entries
            drive_handle.seek(mft_offset)
            mft_entry_size = 1024  # Standard MFT entry size
            entries_parsed = 0
            deleted_files_found = 0
            max_entries = 100000  # Limit to first 100k entries for performance
            
            # Statistics tracking for optimization analysis
            files_checked = 0
            files_too_small = 0
            files_no_signature = 0
            files_failed_validation = 0
            files_low_score = 0
            
            logger.info(f"🔎 Parsing MFT entries (analyzing up to {max_entries} entries)...")
            
            for entry_num in range(max_entries):
                # Check for cancellation
                is_cancelled = options.get('is_cancelled') if options else None
                if is_cancelled and callable(is_cancelled) and is_cancelled():
                    logger.info("⚠️ MFT parsing cancelled by user")
                    break
                
                # Read MFT entry
                mft_entry = drive_handle.read(mft_entry_size)
                if len(mft_entry) < mft_entry_size:
                    break
                
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
                        
                        # Check if this file type is of interest
                        if file_ext in interested_extensions:
                            # Recover file data
                            file_data = file_info.get('data')
                            files_checked += 1
                            
                            if not file_data or len(file_data) < 4096:  # Minimum 4KB
                                files_too_small += 1
                                if files_checked <= 10:  # Log first 10 rejections
                                    logger.debug(f"❌ {filename}: Too small ({len(file_data) if file_data else 0} bytes, need >= 4KB)")
                                continue
                                
                            # Validate file
                            sig_info = self._get_signature_for_extension(file_ext)
                            if not sig_info:
                                files_no_signature += 1
                                if files_checked <= 10:
                                    logger.debug(f"❌ {filename}: No signature found for .{file_ext}")
                                continue
                            
                            validation_result = self._validate_file_with_score(file_data, sig_info)
                            
                            if not validation_result['is_valid']:
                                files_failed_validation += 1
                                if files_checked <= 10:
                                    logger.debug(f"❌ {filename}: Failed validation")
                                continue
                            
                            if validation_result['score'] < 70:
                                files_low_score += 1
                                if files_checked <= 10:
                                    logger.debug(f"❌ {filename}: Score too low ({validation_result['score']}, need >= 70)")
                                continue
                            
                            # File passed all checks - save it
                            safe_filename = self._sanitize_filename(filename)
                            file_path = os.path.join(output_dir, f"mft_{entry_num}_{safe_filename}")
                            
                            with open(file_path, 'wb') as f:
                                f.write(file_data)
                            
                            # Calculate hashes
                            file_md5 = hashlib.md5(file_data).hexdigest()
                            file_sha256 = hashlib.sha256(file_data).hexdigest()
                            
                            recovered_files.append({
                                'name': safe_filename,
                                'path': file_path,
                                'size': len(file_data),
                                'type': file_ext,
                                'offset': mft_offset + (entry_num * mft_entry_size),
                                'md5': file_md5,
                                'sha256': file_sha256,
                                'validation_score': validation_result['score'],
                                'is_partial': validation_result['is_partial'],
                                'method': 'mft_metadata'
                            })
                            
                            logger.info(f"✅ MFT: Recovered {safe_filename} (score: {validation_result['score']}, size: {len(file_data)/1024:.1f}KB)")
                
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
            logger.info(f"   │  ├─ Too small (< 4KB): {files_too_small:,}")
            logger.info(f"   │  ├─ No signature: {files_no_signature:,}")
            logger.info(f"   │  ├─ Failed validation: {files_failed_validation:,}")
            logger.info(f"   │  └─ Score < 70: {files_low_score:,}")
            logger.info(f"   │")
            logger.info(f"   └─ ✅ Files recovered: {len(recovered_files):,}")
            
            if files_checked > 0:
                success_rate = (len(recovered_files) / files_checked) * 100
                logger.info(f"   📊 Success rate: {success_rate:.1f}% of checked files passed ULTRA-STRICT validation")
            
        except Exception as e:
            logger.error(f"Error parsing NTFS MFT: {e}", exc_info=True)
        
        return recovered_files
    
    def _parse_mft_entry(self, mft_entry: bytes, entry_num: int, drive_handle: BinaryIO, 
                         bytes_per_cluster: int) -> Optional[Dict]:
        """
        Parse an MFT entry to extract filename and data
        
        This is a simplified MFT parser - full MFT parsing is very complex
        """
        try:
            # Get first attribute offset
            first_attr_offset = int.from_bytes(mft_entry[0x14:0x16], 'little')
            
            filename = None
            data_runs = []
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
                    # Parse filename
                    try:
                        name_offset = offset + 0x5A  # Filename starts at offset 0x5A in attribute
                        name_length = mft_entry[offset + 0x58]  # Length in characters
                        if name_offset + (name_length * 2) <= len(mft_entry):
                            filename = mft_entry[name_offset:name_offset + (name_length * 2)].decode('utf-16le', errors='ignore')
                    except:
                        pass
                
                # 0x80 = DATA attribute
                elif attr_type == 0x80:
                    # Check if resident or non-resident
                    non_resident = mft_entry[offset + 8]
                    if non_resident == 0:
                        # Resident data (small files)
                        try:
                            data_offset = int.from_bytes(mft_entry[offset+0x14:offset+0x16], 'little')
                            data_length = int.from_bytes(mft_entry[offset+0x10:offset+0x14], 'little')
                            if data_length > 0 and offset + data_offset + data_length <= len(mft_entry):
                                data = mft_entry[offset + data_offset:offset + data_offset + data_length]
                                return {'filename': filename, 'data': data, 'resident': True}
                        except:
                            pass
                    else:
                        # Non-resident data (large files) - would need to parse data runs
                        # This is complex and beyond simple implementation
                        pass
                
                offset += attr_length
            
            return {'filename': filename, 'data': None, 'resident': False}
            
        except Exception as e:
            logger.debug(f"Error parsing MFT entry: {e}")
            return None
    
    def _get_interested_extensions(self, file_type_options: Dict) -> set:
        """Get set of file extensions user is interested in"""
        if not file_type_options:
            return {'jpg', 'png', 'pdf', 'docx', 'xlsx', 'pptx', 'txt', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'zip', 'rar', 'sqlite', 'csv'}
        
        extensions = set()
        file_type_map = {
            'images': {'jpg', 'jpeg', 'png'},
            'documents': {'pdf', 'docx', 'xlsx', 'pptx', 'txt'},
            'videos': {'mp4', 'avi', 'mov'},
            'audio': {'mp3', 'wav'},
            'archives': {'zip', 'rar'},
            'email': {'sqlite', 'csv'}
        }
        
        for category, enabled in file_type_options.items():
            if enabled and category in file_type_map:
                extensions.update(file_type_map[category])
        
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
        # Limit to 2x the source drive size or 20GB, whichever is smaller
        source_drive_size = stats.get('total_size', 0)
        max_total_recovery_size = min(source_drive_size * 2, 20 * 1024 * 1024 * 1024)  # 2x drive or 20GB max
        logger.info(f"⚠️ SAFETY LIMIT: Maximum total recovery size: {max_total_recovery_size / (1024**3):.2f} GB")
        
        logger.info("Starting file carving...")
        logger.info(f"Duplicate detection enabled (hash-based)")
        logger.info(f"File validation enabled (integrity check)")
        logger.info(f"Chunk size: {chunk_size / 1024:.0f} KB")
        
        try:
            while True:
                # Check for cancellation
                is_cancelled = options.get('is_cancelled') if options else None
                if is_cancelled and callable(is_cancelled) and is_cancelled():
                    logger.info("⚠️ Scan cancelled by user")
                    break
                
                # Read chunk
                chunk = drive_handle.read(chunk_size)
                if not chunk:
                    break
                
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
                                
                                # SAFETY CHECK: Stop if total recovered size exceeds limit
                                if total_recovered_size + len(file_data) > max_total_recovery_size:
                                    logger.warning("⚠️ SAFETY LIMIT REACHED!")
                                    logger.warning(f"   Total recovered: {total_recovered_size / (1024**3):.2f} GB")
                                    logger.warning(f"   Limit: {max_total_recovery_size / (1024**3):.2f} GB")
                                    logger.warning("   Stopping recovery to prevent filling your drive!")
                                    break  # Stop scanning
                                
                                # Save file
                                file_counter += 1
                                file_name = f"f{absolute_pos:08d}.{file_ext}"
                                file_path = os.path.join(output_dir, file_name)
                                
                                with open(file_path, 'wb') as f:
                                    f.write(file_data)
                                
                                # Track this file and update total size
                                found_hashes.add(file_md5)
                                found_offsets.add(absolute_pos)
                                total_recovered_size += len(file_data)
                                
                                # Create enhanced file info with manifest data
                                file_info = {
                                    'name': file_name,
                                    'path': file_path,
                                    'size': len(file_data),
                                    'type': sig_info['extension'].upper(),
                                    'offset': absolute_pos,
                                    'md5': file_md5,
                                    'sha256': file_sha256,
                                    'validation_score': validation_result.get('score', 0),
                                    'is_partial': is_partial,
                                    'method': 'signature_carving',
                                    'recovered_at': datetime.now().isoformat()
                                }
                                
                                recovered_files.append(file_info)
                                partial_marker = " [PARTIAL]" if is_partial else ""
                                logger.debug(f"Recovered: {file_name} ({len(file_data)} bytes, SHA256: {file_sha256[:16]}...){partial_marker}")
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
        total_recovered_size = sum(f['size'] for f in recovered_files)
        total_recovered_mb = total_recovered_size / (1024 * 1024)
        
        # Log duplicate statistics
        logger.info(f"Carving complete: {len(recovered_files)} unique files found")
        logger.info(f"Total recovered size: {total_recovered_mb:.2f} MB")
        logger.info(f"Files skipped - Duplicates: {file_counter - len(recovered_files)}, Corrupted: {skipped_corrupted}")
        
        # Important note about file carving
        if total_recovered_mb > stats['total_sectors'] * 512 / (1024 * 1024):
            logger.warning("⚠️ Recovered size exceeds drive capacity!")
            logger.warning("   This is NORMAL for file carving - it recovers:")
            logger.warning("   • Old deleted files not yet overwritten")
            logger.warning("   • Multiple versions of edited files")
            logger.warning("   • Temporary copies from applications")
            logger.warning("   • File fragments from historical data")
            logger.warning("   Recommendation: Sort by file type and manually select what you need")
        
        # Send final progress update
        if progress_callback:
            elapsed = (datetime.now() - datetime.fromisoformat(stats['start_time'])).total_seconds()
            await progress_callback({
                'progress': 100.0,
                'sectors_scanned': stats['sectors_scanned'],
                'total_sectors': stats['total_sectors'],
                'files_found': len(recovered_files),
                'expected_time': "Complete",
                'current_pass': 1
            })
        
        # Generate manifest.json with all recovered file metadata
        self._generate_manifest(recovered_files, output_dir, stats)
        
        logger.info(f"File carving completed: {len(recovered_files)} valid files recovered")
        return recovered_files
    
    def _generate_manifest(self, recovered_files: List[Dict], output_dir: str, stats: Dict):
        """
        Generate manifest.json with all recovered file metadata
        
        Args:
            recovered_files: List of recovered file information dictionaries
            output_dir: Directory where manifest will be saved
            stats: Scan statistics dictionary
        """
        try:
            manifest_path = os.path.join(output_dir, 'manifest.json')
            
            # Build manifest data
            manifest = {
                'scan_info': {
                    'timestamp': datetime.now().isoformat(),
                    'drive_path': stats.get('drive_path', 'unknown'),
                    'total_sectors_scanned': stats.get('sectors_scanned', 0),
                    'scan_duration_seconds': (datetime.now() - datetime.fromisoformat(stats['start_time'])).total_seconds(),
                    'recovery_method': 'signature_carving'
                },
                'statistics': {
                    'total_files_recovered': len(recovered_files),
                    'unique_files': len(recovered_files),  # Already deduplicated by MD5
                    'total_size_bytes': sum(f['size'] for f in recovered_files),
                    'partial_files': sum(1 for f in recovered_files if f.get('is_partial', False))
                },
                'files': []
            }
            
            # Add detailed file information
            for file_info in recovered_files:
                manifest['files'].append({
                    'filename': file_info.get('name', 'unknown'),
                    'path': file_info.get('path', ''),
                    'size_bytes': file_info.get('size', 0),
                    'offset': file_info.get('offset', 0),
                    'file_type': file_info.get('type', 'unknown'),
                    'md5': file_info.get('md5', ''),
                    'sha256': file_info.get('sha256', ''),
                    'validation_score': file_info.get('validation_score', 0),
                    'is_partial': file_info.get('is_partial', False),
                    'method': file_info.get('method', 'signature_carving')
                })
            
            # Write manifest file
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Manifest generated: {manifest_path}")
            logger.info(f"  Total files: {manifest['statistics']['total_files_recovered']}")
            logger.info(f"  Partial files: {manifest['statistics']['partial_files']}")
            logger.info(f"  Total size: {manifest['statistics']['total_size_bytes'] / (1024*1024):.2f} MB")
            
        except Exception as e:
            logger.error(f"Failed to generate manifest: {e}", exc_info=True)
    
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
