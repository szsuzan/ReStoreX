from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class DriveInfo(BaseModel):
    id: str
    name: str
    size: str
    fileSystem: str
    status: Literal['healthy', 'damaged', 'scanning', 'error']


class RecoveredFile(BaseModel):
    id: str
    name: str
    type: str
    size: str
    sizeBytes: int
    dateModified: str
    path: str
    recoveryChance: Literal['High', 'Average', 'Low', 'Unknown']
    thumbnail: Optional[str] = None
    isSelected: bool = False
    sector: Optional[int] = None
    cluster: Optional[int] = None
    inode: Optional[int] = None
    status: Literal['found', 'recovering', 'recovered', 'failed'] = 'found'


class ScanOptions(BaseModel):
    fileTypes: Optional[List[str]] = None
    deepScan: bool = False
    skipBadSectors: bool = True


class ScanRequest(BaseModel):
    driveId: str
    scanType: Literal['normal', 'deep', 'cluster', 'health', 'signature']
    options: Optional[ScanOptions] = ScanOptions()


class ScanProgress(BaseModel):
    scanId: str
    isScanning: bool
    progress: float
    currentSector: int
    totalSectors: int
    filesFound: int
    estimatedTimeRemaining: str
    status: str


class RecoveryRequest(BaseModel):
    fileIds: List[str]
    outputPath: str
    options: Optional[dict] = {}


class RecoveryProgress(BaseModel):
    recoveryId: str
    isRecovering: bool
    progress: float
    currentFile: str
    filesRecovered: int
    totalFiles: int
    estimatedTimeRemaining: str
    status: str


class FileInfo(BaseModel):
    id: str
    name: str
    type: str
    size: str
    sizeBytes: int
    dateModified: str
    path: str
    recoveryChance: Literal['High', 'Average', 'Low', 'Unknown']
    sector: Optional[int] = None
    cluster: Optional[int] = None
    inode: Optional[int] = None
    status: Literal['found', 'recovering', 'recovered', 'failed']


class HexData(BaseModel):
    fileId: str
    offset: int
    length: int
    data: List[int]


class DirectoryItem(BaseModel):
    id: str
    name: str
    type: Literal['file', 'folder']
    size: Optional[str] = None
    dateModified: str
    path: str
    itemCount: Optional[int] = None


class DirectoryContents(BaseModel):
    path: str
    items: List[DirectoryItem]


class HealthCheckResponse(BaseModel):
    status: str
    testdisk_available: bool
    photorec_available: bool
    version: str
