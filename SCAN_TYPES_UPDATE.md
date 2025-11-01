# Scan Types Update - Normal & Deep Scan Implementation

## Overview
Updated the scan functionality to properly differentiate between **Normal Scan** (fast, metadata-first) and **Deep Scan** (comprehensive, sector-by-sector like File Carving).

## Changes Made

### 1. Normal Scan (Fast/Quick Scan)
**Purpose**: Standard, surface-level scan that checks for existing and recently deleted files by analyzing the file system structure, partition table, and metadata.

**Implementation**:
- Uses **metadata-first recovery** logic (`_metadata_first_recovery` method)
- Parses NTFS Master File Table (MFT) for deleted file records
- Analyzes filesystem structure without scanning every sector
- **Much faster** than signature-based carving (seconds vs minutes)
- Recovers files with intact metadata and data runs

**Key Features**:
- ✅ Analyzes partition table and filesystem metadata
- ✅ Looks for existing and recently deleted files
- ✅ NO sector-by-sector scanning (faster)
- ✅ Automatically selects all important file types
- ✅ Only validates recoverable files (score >= 70)

**Best For**:
- Quick recovery of recently deleted files
- Files that still have filesystem metadata intact
- When you need results fast (< 1 minute typically)

### 2. Deep Scan (Comprehensive Recovery)
**Purpose**: Thorough, comprehensive scan that performs sector-by-sector signature-based file carving with ALL file types enabled.

**Implementation**:
- Uses the **same code as Signature File Carving** scan
- Scans every sector of the disk for file signatures
- Automatically enables **ALL file type categories**:
  - Images (JPG, PNG)
  - Documents (PDF, DOCX, XLSX, PPTX)
  - Videos (MP4, AVI, MOV)
  - Audio (MP3, WAV)
  - Archives (ZIP, RAR)
  - Email/Databases (SQLite, CSV)

**Key Features**:
- ✅ Sector-by-sector scanning (thorough)
- ✅ ALL file types automatically selected
- ✅ Detects files by signature (header/footer)
- ✅ Recovers fragmented and overwritten files
- ✅ Validation and deduplication (SHA256)
- ✅ Maximum file size: 20MB (safe mode)

**Best For**:
- Files deleted long ago (metadata lost)
- Files on formatted drives
- Maximum recovery coverage
- When Normal scan finds nothing

### 3. Signature File Carving Scan (Unchanged)
**Purpose**: User-selectable file type recovery with signature-based carving.

**Implementation**:
- Works exactly as before
- User selects which file types to search for
- Sector-by-sector scanning for selected types only
- More focused than Deep Scan

**Best For**:
- When you know what file types you need
- Targeted recovery (e.g., only photos)
- Faster than Deep Scan (fewer signatures to check)

## Code Changes

### File: `python_recovery_service.py`

#### 1. Updated `scan_drive()` method (lines 228-380)
```python
# NORMAL SCAN: Fast metadata-first recovery (MFT parsing for NTFS)
if scan_type == 'normal':
    logger.info("🚀 Normal Scan: Quick metadata-first recovery (analyzing filesystem structure)")
    logger.info("   - Scanning partition table and metadata")
    logger.info("   - Looking for existing and recently deleted files")
    logger.info("   - NO sector-by-sector scanning (faster)")
    recovered_files = await self._metadata_first_recovery(...)
    
# DEEP SCAN: Same as Signature File Carving - sector-by-sector with all file types
elif scan_type == 'deep':
    logger.info("🔍 Deep Scan: Comprehensive signature-based file carving (all file types)")
    logger.info("   - Scanning every sector of the disk")
    logger.info("   - Detecting all file types by signature")
    logger.info("   - Similar to Signature File Carving scan")
    
    # Deep scan uses all file types by default
    if not options.get('fileTypes'):
        options['fileTypes'] = {
            'images': True, 'documents': True, 'videos': True,
            'audio': True, 'archives': True, 'email': True
        }
    
    recovered_files = await self._carve_files(...)
```

#### 2. Updated `_carve_files()` method (lines 997-1145)
Added comprehensive handling for Deep Scan mode:
```python
elif scan_type == 'deep':
    # Deep scan: ALL file types (like Signature File Carving with all types selected)
    available_memory = self._get_available_memory()
    chunk_size = self._optimize_buffer_size(stats['total_size'], available_memory)
    
    # Deep scan: Use ALL file signatures (including system files)
    signatures_to_scan = self.signatures.copy()
    
    # Filter to only signatures with headers (can be detected)
    signatures_to_scan = {k: v for k, v in signatures_to_scan.items() 
                          if v.get('header') is not None}
    
    max_file_size = 20 * 1024 * 1024  # 20MB max per file for deep scan
    
    logger.info(f"🔍 Deep scan mode: Scanning for ALL file types (comprehensive recovery)")
    logger.info(f"   Total signatures to scan: {len(signatures_to_scan)}")
```

#### 3. Updated `_metadata_first_recovery()` method (lines 620-640)
Improved Normal Scan to automatically select all important file types:
```python
# For normal scan, get all important file types if no specific types selected
if scan_type == 'normal' and not file_type_options:
    # Default to all important file types for normal scan
    interested_extensions = set()
    for sig_name, sig_info in self.signatures.items():
        if sig_info.get('important', False):
            interested_extensions.add(sig_info['extension'])
    logger.info(f"🎯 Normal scan: Looking for all important file types")
```

## User Experience

### Normal Scan Workflow:
1. User selects drive and clicks "Normal Scan"
2. System analyzes filesystem metadata (NTFS MFT)
3. **Fast results** (typically 30-60 seconds)
4. Shows recently deleted files with intact metadata
5. If no results, user is prompted to try Deep Scan

### Deep Scan Workflow:
1. User selects drive and clicks "Deep Scan"
2. System performs sector-by-sector signature carving
3. **ALL file types automatically enabled** (no manual selection needed)
4. Slower but comprehensive (minutes to hours depending on drive size)
5. Shows all recoverable files found by signature

### Signature File Carving Workflow:
1. User selects drive and clicks "Signature File Carving"
2. User **manually selects** which file types to search for
3. System performs sector-by-sector carving for selected types
4. Faster than Deep Scan (fewer signatures to check)
5. Shows only selected file types

## Technical Details

### Normal Scan (Metadata-First):
- **Speed**: Fast (< 1 minute for most drives)
- **Method**: MFT/inode parsing
- **Coverage**: Recently deleted files with intact metadata
- **Accuracy**: High (uses filesystem records)
- **Limitations**: Won't find files if metadata is overwritten

### Deep Scan (Signature-Based):
- **Speed**: Slow (minutes to hours)
- **Method**: Sector-by-sector signature carving
- **Coverage**: All file types, even with lost metadata
- **Accuracy**: High (signature validation + integrity checks)
- **Limitations**: Slower, may find many partial files

### Memory Optimization:
Both Deep Scan and File Carving use dynamic buffer sizing:
- Analyzes available system memory
- Uses 1% of available memory (capped 1-10MB)
- Adjusts chunk size for optimal performance

### Safety Features:
- ✅ Read-only operations (no writes to source drive)
- ✅ File validation (only saves recoverable files)
- ✅ Deduplication (MD5 + SHA256 hashing)
- ✅ Maximum file size limits (prevent memory issues)
- ✅ Total recovery size limits (prevent filling C: drive)

## Logging

### Normal Scan Logs:
```
🚀 Normal Scan: Quick metadata-first recovery (analyzing filesystem structure)
   - Scanning partition table and metadata
   - Looking for existing and recently deleted files
   - NO sector-by-sector scanning (faster)
📂 Detected NTFS filesystem - parsing MFT...
🎯 Normal scan: Looking for all important file types
✅ Normal scan complete: X files recovered from filesystem metadata
```

### Deep Scan Logs:
```
🔍 Deep Scan: Comprehensive signature-based file carving (all file types)
   - Scanning every sector of the disk
   - Detecting all file types by signature
   - Similar to Signature File Carving scan
💾 Memory optimization: X.XX GB available, using X.XX MB chunks
🔍 Deep scan mode: Scanning for ALL file types (comprehensive recovery)
   Total signatures to scan: XX (SAFE MODE - Read Only)
   Unique extensions: jpg, png, pdf, docx, mp4, mp3, zip, ...
✅ File carving completed: X valid files recovered
```

## Testing Checklist

- [x] Normal Scan uses metadata-first recovery
- [x] Deep Scan uses signature-based carving with all file types
- [x] Signature File Carving still works with user-selected types
- [x] No syntax errors in Python code
- [x] Proper logging for each scan type
- [x] Memory optimization for Deep Scan
- [x] File validation and deduplication
- [x] Safety limits in place

## Benefits

1. **Clear Distinction**: Users now understand the difference between scan types
2. **Better UX**: Normal scan is fast, Deep scan is thorough
3. **No Confusion**: Deep scan automatically selects all types (like the working File Carving)
4. **Performance**: Normal scan provides quick results for recent deletions
5. **Comprehensive**: Deep scan ensures maximum coverage for difficult cases

## Recommendations

### For Users:
1. **Try Normal Scan first** - Fast and often sufficient for recently deleted files
2. **Use Deep Scan if Normal finds nothing** - More thorough but slower
3. **Use Signature File Carving for targeted recovery** - When you know what you need

### For Frontend:
Consider updating UI descriptions:
- **Normal Scan**: "Fast scan using filesystem metadata (recommended first)"
- **Deep Scan**: "Thorough sector-by-sector scan with all file types (slower but comprehensive)"
- **Signature File Carving**: "Targeted recovery - select specific file types to search for"

## Notes

- Cluster Scan and Disk Health Scan remain **unchanged** as requested
- All changes maintain backward compatibility
- Safety features and read-only mode remain intact
- Logging has been enhanced for better debugging
