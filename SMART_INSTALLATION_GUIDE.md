# SMART Data Reading - Installation Guide

## Quick Summary

Your ReStoreX application now supports **3 methods** to read SMART data:

1. ✅ **pySMART** - Installed, but requires smartctl
2. ⚠️ **smartctl** - Not installed (this is the key tool needed!)
3. ❌ **WMI** - Not working (drive doesn't support it)

## What You Need to Do

### To Get SMART Data Working: Install smartmontools

**This is the ONE tool you need to install:**

#### Option A: Download Installer (Easiest)

1. **Download smartmontools:**
   - Visit: https://builds.smartmontools.org/
   - Click: `smartmontools-7.4-1.win.x86_64-signed.zip`
   - Or latest version from: https://www.smartmontools.org/wiki/Download

2. **Install:**
   - Extract the ZIP file
   - Run `smartmontools-7.4-1.win.x86_64-signed.exe`
   - Follow the installer (keep default settings)

3. **Verify:**
   ```powershell
   smartctl --version
   ```
   Should show: "smartctl 7.x ..."

4. **If "command not found" error:**
   
   The PATH hasn't refreshed yet. Choose one:
   
   **Option A: Refresh PATH in current terminal (Quick)**
   ```powershell
   cd C:\Users\SZ\Desktop\ReStoreX\backend
   .\refresh_path.ps1
   ```
   
   **Option B: Refresh PATH manually**
   ```powershell
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
   smartctl --version
   ```
   
   **Option C: Restart terminal or VS Code (Permanent)**
   - Close and reopen your terminal/VS Code
   - PATH will be automatically updated

5. **Test with ReStoreX:**
   - Restart your backend server
   - Run a Health Scan
   - SMART data should now appear! 🎉

#### Option B: Using Chocolatey Package Manager

```powershell
choco install smartmontools
```

#### Option C: Manual Installation

1. Download from: https://builds.smartmontools.org/
2. Extract to: `C:\Program Files\smartmontools\`
3. Add to PATH: `C:\Program Files\smartmontools\bin\`
4. Restart terminal

---

## Testing After Installation

### Quick Test:
```powershell
# If smartctl command not found, refresh PATH first:
.\refresh_path.ps1
# Or manually:
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# List all drives
smartctl --scan

# Read SMART from first drive
smartctl -a /dev/sda
```

### Test in ReStoreX:
```powershell
cd C:\Users\SZ\Desktop\ReStoreX\backend
python test_pysmart.py
```

Should now show:
```
✅ Device found!
   Model: [Your Drive Model]
   Assessment: PASS
   Temperature: 35°C
   SMART Attributes found: 12
```

---

## What If It Still Doesn't Work?

### Common Issue: "smartctl command not found"

**This happens when PATH hasn't refreshed in your terminal.**

**Quick Fixes:**

1. **Run the refresh script:**
   ```powershell
   cd C:\Users\SZ\Desktop\ReStoreX\backend
   .\refresh_path.ps1
   ```

2. **Manual PATH refresh:**
   ```powershell
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
   smartctl --version
   ```

3. **Permanent fix - Restart:**
   - Close VS Code completely
   - Reopen VS Code
   - Open new terminal
   - Command should work now

4. **Verify installation:**
   ```powershell
   # Check if file exists
   Test-Path "C:\Program Files\smartmontools\bin\smartctl.exe"
   
   # Run with full path (always works)
   & "C:\Program Files\smartmontools\bin\smartctl.exe" --version
   ```

---

### Other Possible Reasons:

1. **USB Drive**
   - SMART often doesn't work through USB bridges
   - **Solution:** Use surface scan only (already works!)

2. **Virtual Machine**
   - VMs don't always pass through SMART data
   - **Solution:** Use surface scan only

3. **RAID Controller**
   - Some RAID controllers block SMART access
   - **Solution:** Use surface scan only

4. **NVMe Drive (Newer SSDs)**
   - Requires NVMe-specific commands
   - **Solution:** smartctl usually works, but may need `-d nvme` flag

### Don't Worry!

Even without SMART data, your **Health Scan still works perfectly**:

- ✅ Detects bad sectors via surface scan
- ✅ Shows surface map visualization
- ✅ Provides health assessment
- ✅ Gives recommendations

You just won't see:
- ❌ Power-on hours
- ❌ Temperature readings
- ❌ Reallocated sector count
- ❌ Predictive failure warnings

---

## Current Status

### ✅ What's Working:
- pySMART library installed
- Fallback system implemented
- Error handling with helpful messages
- Surface scan (detects bad sectors)
- All other scan types (Normal, Deep, Carving, Cluster)

### ⚠️ What Needs Action:
- Install smartmontools (smartctl.exe)
- Then restart backend server

### ❌ What Won't Work (Due to Hardware):
- WMI SMART access (your drive doesn't support it)
- This is hardware limitation, not a bug!

---

## Downloads

### smartmontools:
- **Homepage:** https://www.smartmontools.org/
- **Downloads:** https://builds.smartmontools.org/
- **Latest Windows:** `smartmontools-7.4-1.win.x86_64-signed.zip`

### After Installation:
1. Restart backend: `python main.py`
2. Run Health Scan
3. Check SMART Data section
4. Should see actual SMART attributes! 🎉

---

## Technical Details

### How the Fallback Works:

```
1. Try pySMART
   ↓ (requires smartctl)
   ↓
2. Try smartctl directly
   ↓ (Windows only)
   ↓
3. Try WMI
   ↓ (often fails)
   ↓
4. Show helpful error message
   + Surface scan still works!
```

### Files Modified:
- ✅ `python_recovery_service.py` - Added 3 fallback methods
- ✅ `requirements.txt` - Added pySMART note
- ✅ `ScanReportDialog.jsx` - Better SMART error display

---

## FAQs

**Q: Do I need all 3 methods?**
A: No! Just install smartmontools. That enables both pySMART and direct smartctl access.

**Q: Will this work on USB drives?**
A: Maybe. USB bridges often block SMART. Try it and see!

**Q: What if I can't install smartmontools?**
A: No problem! Surface scan still works and detects bad sectors.

**Q: Is SMART data necessary?**
A: No! It's helpful for predictive warnings, but surface scan is the real test.

**Q: Why doesn't WMI work?**
A: Your specific drive/controller doesn't expose SMART via WMI. This is common and normal.

---

*Last Updated: November 1, 2025*
*ReStoreX v2.0*
