# SMART Data Reading - Alternative Methods

## Overview

ReStoreX now supports **multiple methods** to read SMART data from your drives. If one method doesn't work, it automatically tries the next one:

1. **pySMART Library** (Python-based, cross-platform)
2. **smartmontools (smartctl)** (Industry standard tool)
3. **WMI (Windows Management Instrumentation)** (Windows-only, built-in)

---

## Why Multiple Methods?

SMART data access can fail due to:
- **USB-connected drives** (limited SMART access via USB bridges)
- **Virtual machine environments** (VMs don't always pass through SMART data)
- **Some drive controllers** (not all support WMI SMART interface)
- **Some SSDs** (don't expose SMART via standard WMI)
- **RAID controllers** (may block direct SMART access)

---

## Method 1: pySMART (Recommended)

### What is pySMART?
A Python library that provides cross-platform SMART data access.

### Installation:

```powershell
# Activate your virtual environment first
cd C:\Users\SZ\Desktop\ReStoreX\backend
python -m pip install pySMART
```

### Pros:
- ✅ Cross-platform (Windows, Linux, macOS)
- ✅ Pure Python (no external dependencies)
- ✅ Better USB drive support
- ✅ Easier to parse data

### Cons:
- ⚠️ May require admin rights on Windows
- ⚠️ Still limited by hardware capabilities

---

## Method 2: smartmontools (Most Reliable)

### What is smartmontools?
Industry-standard tool for reading SMART data. Used by professionals worldwide.

### Installation:

1. **Download smartmontools:**
   - Visit: https://www.smartmontools.org/
   - Download: `smartmontools-7.4-1.win.x86_64-signed.zip` (or latest version)
   - Or direct download: https://builds.smartmontools.org/

2. **Install:**
   ```powershell
   # Extract the ZIP file
   # Run the installer: smartmontools-7.4-1.win.x86_64-signed.exe
   
   # Or use Chocolatey package manager:
   choco install smartmontools
   ```

3. **Verify installation:**
   ```powershell
   smartctl --version
   ```

### Usage with ReStoreX:
Once installed, ReStoreX will automatically detect and use smartctl if available.

### Pros:
- ✅ **Most reliable** SMART reading method
- ✅ Industry standard tool
- ✅ Works with most drives (even USB with proper bridges)
- ✅ Actively maintained
- ✅ Supports NVMe, SATA, SAS drives
- ✅ Can read extended SMART logs

### Cons:
- ⚠️ Requires separate installation
- ⚠️ Must be in system PATH or common installation location

---

## Method 3: WMI (Windows Built-in)

### What is WMI?
Windows Management Instrumentation - built into Windows.

### Installation:
Already installed! Just need the Python module:

```powershell
python -m pip install WMI pywin32
```

### Pros:
- ✅ Built into Windows
- ✅ No external tool needed
- ✅ Fast when it works

### Cons:
- ❌ Limited drive compatibility
- ❌ Doesn't work with USB drives
- ❌ Often blocked in VMs
- ❌ Some SSDs/controllers don't expose SMART via WMI

---

## Current Status on Your System

Based on your current setup, **WMI is not working** because your drive doesn't expose SMART data through the Windows WMI interface.

### What's Already Working:
- ✅ Application runs with admin rights
- ✅ WMI module is installed
- ✅ **Surface scan still works** to detect bad sectors
- ✅ All other scan types work perfectly

### What's Not Working:
- ❌ SMART data reading via WMI
- Reason: Your drive/controller doesn't support WMI SMART interface

---

## Recommended Solution

### Option 1: Install smartmontools (Best)

**This is the most reliable method:**

1. Download from: https://builds.smartmontools.org/
2. Run installer: `smartmontools-7.4-1.win.x86_64-signed.exe`
3. Restart ReStoreX
4. SMART data should now work!

### Option 2: Install pySMART

```powershell
cd C:\Users\SZ\Desktop\ReStoreX\backend
python -m pip install pySMART
```

Then restart the backend server.

### Option 3: Use Surface Scan Only

**No installation needed!**

The Health Scan's surface scan component already works perfectly and can detect bad sectors. You just won't get:
- Power-on hours
- Temperature readings
- Reallocated sector counts
- Predictive failure warnings

But you **WILL** get:
- ✅ Bad sector detection
- ✅ Surface map visualization
- ✅ Drive health assessment based on bad sectors
- ✅ Recommendations based on scan results

---

## Testing SMART Data After Installation

### Test smartctl (if installed):

```powershell
# List all drives
smartctl --scan

# Read SMART data from first drive
smartctl -a /dev/pd0

# Read SMART data with JSON output
smartctl -a /dev/pd0 --json=c
```

### Test pySMART (if installed):

```python
from pySMART import Device

# Read first physical drive
device = Device('/dev/pd0')
print(f"Health: {device.assessment}")
print(f"Temperature: {device.temperature}°C")

# List all attributes
for attr in device.attributes:
    print(f"{attr.name}: {attr.raw}")
```

### Test in ReStoreX:

1. Open ReStoreX
2. Select your drive
3. Click "Disk Health Scan"
4. Check the SMART Data section in the report

---

## Troubleshooting

### "smartctl not found"
- **Solution:** Make sure smartmontools is installed and in your PATH
- **Check:** Run `smartctl --version` in PowerShell
- **Fix:** Add installation directory to system PATH or reinstall

### "pySMART: No device data available"
- **Solution:** Try running as Administrator
- **Alternative:** Install smartmontools instead

### "Permission denied"
- **Solution:** Run VS Code as Administrator
- **Alternative:** Use elevated PowerShell terminal

### Still not working?
- **Check:** Is this a USB drive? (SMART often doesn't work via USB)
- **Check:** Is this a virtual machine? (VMs often don't pass SMART data)
- **Alternative:** Use surface scan only - it still detects bad sectors!

---

## Summary Table

| Method | Reliability | Installation | USB Support | VM Support |
|--------|------------|--------------|-------------|------------|
| **smartctl** | ⭐⭐⭐⭐⭐ | External tool | ✅ Good | ⚠️ Limited |
| **pySMART** | ⭐⭐⭐⭐ | `pip install` | ✅ Good | ⚠️ Limited |
| **WMI** | ⭐⭐⭐ | Built-in | ❌ Poor | ❌ Poor |

---

## For Developers

The fallback system is implemented in `python_recovery_service.py`:

```python
async def _read_smart_data_wmi(self, drive_path: str) -> dict:
    # Try Method 1: pySMART
    result = await self._try_pysmart(drive_path)
    if result and 'error' not in result:
        return result
    
    # Try Method 2: smartctl
    result = await self._try_smartctl(drive_path)
    if result and 'error' not in result:
        return result
    
    # Try Method 3: WMI
    result = await self._try_wmi(drive_path)
    if result and 'error' not in result:
        return result
    
    # All methods failed - return helpful error
    return {
        'error': 'SMART data not accessible',
        'note': 'All methods attempted',
        'alternative': 'Surface scan can still detect bad sectors'
    }
```

---

## Additional Resources

- **smartmontools Homepage:** https://www.smartmontools.org/
- **smartmontools Documentation:** https://www.smartmontools.org/wiki/TocDoc
- **pySMART GitHub:** https://github.com/truenas/py-SMART
- **WMI Documentation:** https://docs.microsoft.com/en-us/windows/win32/wmisdk/

---

*Last Updated: November 1, 2025*
