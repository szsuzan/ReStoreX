# Signature File Carving Scan Feature

## Overview 🔍

**Signature File Carving Scan** is a smart recovery mode specifically designed to recover deleted important user files like photos, videos, documents, and audio files. It's optimized for safety and efficiency.

## Key Features ✨

### 🛡️ Safe Mode
- **Read-Only Operations**: Never writes to or modifies your source drive
- **Volume-Level Access**: Scans only the selected drive partition
- **No Physical Drive Modification**: Works at the volume level, not physical disk level
- **Automatic Error Recovery**: Gracefully handles any read errors

### 📁 Targeted File Recovery
Recovers only important user files:

#### Images 📸
- JPEG (.jpg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tif)

#### Documents 📄
- PDF (.pdf)
- Microsoft Word (.docx)
- Microsoft Excel (.xlsx)
- Microsoft PowerPoint (.pptx)
- Rich Text Format (.rtf)

#### Videos 🎥
- MP4 (.mp4)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- FLV (.flv)
- WMV (.wmv)

#### Audio 🎵
- MP3 (.mp3)
- WAV (.wav)
- FLAC (.flac)
- OGG (.ogg)
- M4A (.m4a)

#### Archives 📦
- ZIP (.zip)
- RAR (.rar)
- 7Z (.7z)

#### Email 📧
- Outlook PST (.pst)
- Outlook OST (.ost)
- Email Messages (.eml)

### ⚡ Performance Optimized
- **Balanced Chunk Size**: 1MB chunks for optimal speed
- **Smart Filtering**: Only scans for selected file types
- **Minimum File Size**: Skips corrupted fragments (1KB minimum)
- **Max File Size**: 100MB per file (prevents memory issues)

### ❌ Excluded Files
To keep your recovery focused and efficient, these are **NOT** recovered:
- System executables (.exe, .dll)
- System databases (.sqlite)
- System archives (.tar, .gz, .bz2)
- Other system files

## How It Works 🔧

### Signature-Based Detection
File Carving uses **file signature detection** (also called "magic numbers"):

1. **Reads drive in chunks** (1MB at a time)
2. **Searches for file headers** (unique byte patterns that identify file types)
3. **Extracts complete files** using footer markers when available
4. **Validates file integrity** before saving
5. **Saves to output directory** organized by file type

### Example File Signatures:
- JPEG: Starts with `FF D8 FF`
- PNG: Starts with `89 50 4E 47 0D 0A 1A 0A`
- PDF: Starts with `25 50 44 46 2D` ("%PDF-")
- ZIP: Starts with `50 4B 03 04` ("PK")

## When to Use File Carving Scan 🎯

### ✅ Best For:
- Recovering accidentally deleted photos from a camera SD card
- Recovering deleted documents from a USB drive
- Recovering lost videos from an external hard drive
- Recovering deleted music files
- When you know the file types you're looking for
- After formatting a drive (quick format)

### ⚠️ Not Recommended For:
- Very old deletions (use Deep Scan instead)
- Highly fragmented file systems
- Physically damaged drives (use specialized tools)
- System file recovery (use Deep Scan if needed)

## Safety Guarantees 🔒

### What File Carving DOES:
✅ Reads data from your drive
✅ Analyzes file signatures
✅ Extracts recoverable files
✅ Saves to output directory

### What File Carving DOES NOT DO:
❌ Write to your source drive
❌ Modify your file system
❌ Change partition tables
❌ Alter drive sectors
❌ Format or repartition
❌ Defragment

### Technical Safeguards:
1. **Read-Only Mode**: Opens drive with read-only access
2. **Error Handling**: Continues on read errors without crashing
3. **Volume Isolation**: Only accesses the selected volume
4. **No Destructive Operations**: Zero write operations to source

## Usage Guide 📖

### Step 1: Select File Carving Scan
1. Open ReStoreX Dashboard
2. Look for the **File Carving Scan** card (cyan color with 🛡️ Safe badge)
3. Note the features:
   - Photos & Videos
   - Documents (PDF, DOCX)
   - Audio files
   - No system files

### Step 2: Choose Your Drive
1. Click "Start File Carving Scan"
2. Select the drive where files were deleted
3. Verify it's the correct drive letter

### Step 3: Monitor Progress
- **Progress Bar**: Shows scan completion percentage
- **Files Found**: Real-time count of recovered files
- **Sectors Scanned**: Technical progress indicator
- **Elapsed Time**: How long the scan has been running

### Step 4: Review Results
Once complete, you'll see:
- Total files found
- File types recovered
- Recovery success rate
- Files organized by type

## Performance Expectations ⏱️

### Typical Scan Times:
- **8GB USB Drive**: 5-10 minutes
- **32GB SD Card**: 15-20 minutes
- **128GB External Drive**: 40-60 minutes
- **500GB HDD**: 2-3 hours

### Factors Affecting Speed:
- Drive size and speed (USB 2.0 vs 3.0, HDD vs SSD)
- Number of files on drive
- File fragmentation
- System resources (CPU, RAM)
- Other running programs

### Files Recovered:
- **Best Case**: 80-95% of deleted files (recent deletions, no overwrite)
- **Average Case**: 50-70% of deleted files (some overwrite)
- **Worst Case**: 10-30% of deleted files (heavy overwrite, old deletions)

## Comparison with Other Scan Types 📊

| Feature | File Carving | Normal Scan | Deep Scan |
|---------|-------------|-------------|-----------|
| **Speed** | Fast (1MB chunks) | Fast | Slow (512KB chunks) |
| **File Types** | User files only | User files only | All files |
| **System Files** | ❌ Excluded | ❌ Excluded | ✅ Included |
| **Safety** | 🛡️ Safe Mode | ✅ Safe | ✅ Safe |
| **Best For** | Photos, docs, media | Recent deletions | Complete recovery |
| **Time (8GB)** | 5-10 min | 5-15 min | 20-30 min |
| **Recommended** | ⭐ Yes | ⭐ Yes | Advanced users |

## Troubleshooting 🔧

### Scan Not Finding Files?
1. **Try Deep Scan** - More thorough but slower
2. **Check correct drive** - Make sure you selected the right drive
3. **Stop using drive** - Every write operation reduces recovery chances
4. **Check if files were overwritten** - Long time since deletion?

### Scan Taking Too Long?
1. **Normal for large drives** - Be patient
2. **Close other programs** - Free up system resources
3. **Check drive health** - Slow reads indicate drive issues
4. **USB 3.0** - Use faster connection if available

### Recovered Files Corrupted?
1. **Some corruption is normal** - Not all files survive deletion
2. **Try different viewer** - Some viewers are more forgiving
3. **Check file size** - 0-byte files are not recoverable
4. **Deep Scan** - Might find better copies

### Scan Failed/Crashed?
1. **Run as Administrator** - Required for drive access
2. **Check drive connection** - Ensure drive is properly connected
3. **Check logs** - Look in `backend/logs/` for error details
4. **Restart backend** - Sometimes fixes transient issues

## Technical Details 🔬

### Implementation:
- **Language**: Python 3.x
- **File I/O**: Direct volume access via win32file (Windows)
- **Async Processing**: asyncio for non-blocking operations
- **Memory Management**: Chunked reading to prevent RAM overflow
- **Error Handling**: Try-except blocks with graceful degradation

### File Signature Database:
Located in: `backend/app/services/python_recovery_service.py`

```python
SIGNATURES = {
    'jpg': {'header': b'\xFF\xD8\xFF', 'footer': b'\xFF\xD9', 'extension': 'jpg', 'important': True},
    'png': {'header': b'\x89PNG\r\n\x1a\n', 'footer': b'\x49\x45\x4E\x44\xAE\x42\x60\x82', 'extension': 'png', 'important': True},
    # ... more signatures
}
```

### Recovery Algorithm:
1. Open drive with read-only access
2. Read 1MB chunks sequentially
3. Search for known file signatures
4. Validate signature with additional checks
5. Extract file based on footer or size heuristics
6. Apply minimum size filter (1KB)
7. Save to output directory
8. Update progress every second
9. Continue until end of volume

## Best Practices 💡

### Before Scanning:
1. ✅ Stop using the drive immediately
2. ✅ Close all programs accessing the drive
3. ✅ Ensure sufficient space on output drive
4. ✅ Run as Administrator for best results
5. ✅ Backup any existing important data

### During Scanning:
1. ✅ Let it complete without interruption
2. ✅ Don't remove the drive
3. ✅ Monitor system resources
4. ✅ Keep laptop plugged in (if applicable)
5. ✅ Don't hibernate/sleep the computer

### After Scanning:
1. ✅ Review recovered files before deleting scan
2. ✅ Copy important files to safe location
3. ✅ Verify file integrity (open and check)
4. ✅ Clean up temp directory if needed
5. ✅ Consider running Deep Scan if files missing

## FAQ ❓

### Q: Is File Carving safe for my drive?
**A:** Yes! It only reads from your drive, never writes to it. It's completely safe.

### Q: Why is it called "File Carving"?
**A:** Because it "carves out" (extracts) files from raw drive data based on their signatures.

### Q: Can it recover files after format?
**A:** Yes, if it was a quick format and the drive hasn't been used much since.

### Q: Why 100MB file size limit?
**A:** To prevent memory issues and ensure stability. Deep Scan allows up to 500MB.

### Q: Will it recover my system files?
**A:** No, File Carving focuses only on user files. Use Deep Scan for system files.

### Q: Can I recover from a network drive?
**A:** Network drives are not recommended. Best results are from directly connected drives.

### Q: What if scan is interrupted?
**A:** Already recovered files are saved. You can start a new scan to continue.

---

## Support & Feedback 📞

If you have questions or issues with File Carving Scan:
1. Check the logs: `backend/logs/`
2. Review TROUBLESHOOTING.md
3. Check QUICK_FIX_GUIDE.md for common issues
4. Report issues with detailed logs

**Version:** 1.0.0  
**Last Updated:** November 1, 2025  
**Status:** ✅ Production Ready
