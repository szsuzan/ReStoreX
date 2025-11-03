# Quick Start: Testing Fixed Normal Scan

## What Was Fixed
✅ Normal Scan now properly recovers deleted files from NTFS drives using MFT metadata
✅ Parses data runs to recover large files from disk clusters
✅ Preserves original filenames
✅ Much faster than Deep Scan

## How to Test (3 Steps)

### Step 1: Start Backend as Admin
```powershell
# Right-click PowerShell -> Run as Administrator
cd C:\Users\SZ\Desktop\ReStoreX\backend
.\venv\Scripts\Activate.ps1
python main.py
```

### Step 2: Run Normal Scan
- Open frontend in browser
- Select your 8GB pendrive
- Click "Normal Scan"
- Wait for completion

### Step 3: Check Results
Backend logs will show:
```
✅ Success:
   "Detected NTFS filesystem"
   "Parsing MFT entries..."
   "Files recovered: X"

❌ No files found:
   "No deleted files with recoverable data"
   → Files were overwritten
   → Try Deep Scan instead
```

## Quick Test Scenario
1. Copy a test file to pendrive (e.g., test.txt)
2. Delete it normally
3. Run Normal Scan immediately
4. Should recover the file with original name

## When to Use Each Scan Type

### Normal Scan (Metadata/MFT)
- ✅ Fast (seconds to minutes)
- ✅ Original filenames
- ✅ Recently deleted files
- ❌ NTFS only
- ❌ Fails if overwritten

### Deep Scan (Signature Carving)
- ✅ Works on all filesystems
- ✅ Finds old/overwritten files
- ✅ More thorough
- ❌ Slow (can take hours)
- ❌ No original filenames

## Troubleshooting

**"Failed to read boot sector"**
→ Run as Administrator

**"Non-NTFS filesystem detected"**
→ Use Deep Scan for FAT32/exFAT drives

**"No deleted files found"**
→ Files were overwritten, try Deep Scan

**Scan completes instantly with 0 files**
→ No deleted files in MFT or all data overwritten

## More Info
See `NORMAL_SCAN_FIX.md` for complete technical details.
