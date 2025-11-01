# ReStoreX - Quick Start Guide

## 🚀 Start the Application

### Prerequisites
- Python 3.8+ with Administrator rights
- Node.js 16+ and npm
- pywin32 package installed (`pip install pywin32`)

---

## Backend Setup

### 1. Navigate to backend directory
```powershell
cd C:\Users\SZ\Desktop\ReStoreX\backend
```

### 2. Activate virtual environment (if using)
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Ensure dependencies are installed
```powershell
pip install -r requirements.txt
```

### 4. Start backend with Admin rights
**Option A: Using batch file**
```powershell
.\start_admin.bat
```

**Option B: Manual start (Run PowerShell as Administrator)**
```powershell
python main.py
```

### ✅ Backend should start on: `http://127.0.0.1:8000`

Expected output:
```
Starting ReStoreX Backend...
Version: 1.0.0
Server: 127.0.0.1:8000
============================================================
Starting ReStoreX Backend Server
Recovery Mode: Pure Python (Signature-based)
============================================================
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## Frontend Setup

### 1. Open a NEW terminal (don't close backend terminal)

### 2. Navigate to frontend directory
```powershell
cd C:\Users\SZ\Desktop\ReStoreX\frontend
```

### 3. Install dependencies (first time only)
```powershell
npm install
```

### 4. Start development server
```powershell
npm run dev
```

### ✅ Frontend should start on: `http://localhost:5173`

Expected output:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

## Access the Application

### Open your browser and navigate to:
```
http://localhost:5173
```

---

## Quick Test

### 1. Check Health
Visit: http://localhost:8000/api/health

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 2. Check Drives
Visit: http://localhost:8000/api/drives

Should return list of available drives

### 3. Test UI
- Dashboard should load
- Drives should be listed
- All components should render without errors

---

## Common Commands

### Backend
```powershell
# Start backend
cd C:\Users\SZ\Desktop\ReStoreX\backend
python main.py

# Check if running
curl http://localhost:8000/api/health

# View logs
# Logs appear in terminal
```

### Frontend
```powershell
# Start frontend
cd C:\Users\SZ\Desktop\ReStoreX\frontend
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Troubleshooting

### Backend won't start
**Error: "Access Denied" or "Cannot open physical drive"**
- Solution: Run PowerShell as Administrator
- Solution: Use `start_admin.bat` which requests admin rights

**Error: "Module not found"**
- Solution: `pip install -r requirements.txt`
- Check: Correct virtual environment activated

**Error: "Port 8000 already in use"**
- Solution: Kill existing process or change PORT in `.env`
- Find process: `Get-Process | Where-Object {$_.ProcessName -eq "python"}`

### Frontend won't start
**Error: "Cannot find module"**
- Solution: `npm install`

**Error: "Port 5173 already in use"**
- Solution: Kill existing process or press `y` to use different port

**Error: "API connection failed"**
- Check: Backend is running on port 8000
- Check: CORS_ORIGINS in backend/.env includes frontend URL
- Check: No firewall blocking localhost

### No drives detected
**Symptom: Dashboard shows "No drives found"**
- Check: Backend running with Administrator rights
- Check: Physical drives are connected
- Check: WMI service is running on Windows

### Scan fails to start
**Error: "Failed to start scan"**
- Check: Drive is not mounted/in use by another process
- Check: Sufficient permissions to access drive
- Check: pywin32 is installed correctly

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         Browser (localhost:5173)        │
│              React Frontend             │
└─────────────┬───────────────────────────┘
              │ HTTP/WebSocket
              │
┌─────────────▼───────────────────────────┐
│      Backend (localhost:8000)           │
│           FastAPI Server                │
├─────────────────────────────────────────┤
│  Routes: scan, recovery, drives, etc.   │
├─────────────────────────────────────────┤
│  Services:                              │
│  - scan_service.py                      │
│  - python_recovery_service.py (NEW)     │
│  - recovery_service.py                  │
│  - drive_service.py                     │
│  - system_service.py                    │
└─────────────┬───────────────────────────┘
              │
              │ win32file API
              │
┌─────────────▼───────────────────────────┐
│      Physical Drives (\\.\PHYSICALDRIVEx)│
│      Windows Drive Access               │
└─────────────────────────────────────────┘
```

---

## File Recovery Process

```
1. User selects drive in UI
   ↓
2. Frontend sends POST /api/scan/start
   ↓
3. scan_service creates scan task
   ↓
4. python_recovery_service opens drive with win32file
   ↓
5. Reads drive in 1MB chunks
   ↓
6. Searches for file signatures (60+ types)
   ↓
7. Extracts files when signatures found
   ↓
8. WebSocket broadcasts progress
   ↓
9. Frontend updates UI in real-time
   ↓
10. Files saved to temp/output directory
```

---

## Technology Stack

### Backend
- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **WebSockets** - Real-time updates
- **pywin32** - Windows drive access (NEW)
- **psutil** - System monitoring

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **WebSocket API** - Real-time updates

---

## Next Steps

1. ✅ Start both servers
2. ✅ Test drive detection
3. ✅ Run a quick scan on a test drive
4. ✅ Verify file recovery works
5. ✅ Check real-time progress updates
6. ✅ Test recovery to output directory

---

## Support

For issues or questions:
1. Check `INTEGRATION_STATUS.md` for detailed testing checklist
2. Check `CLEANUP_SUMMARY.md` for recent changes
3. Review backend logs in terminal
4. Review browser console for frontend errors

---

## Important Notes

- ⚠️ **Always run backend with Administrator rights** for physical drive access
- ⚠️ **Scan operations access drives directly** - ensure no critical data is at risk
- ⚠️ **Test on non-critical drives first** to validate recovery accuracy
- ✅ **Pure Python implementation** - no external tools required
- ✅ **60+ file types supported** - images, documents, videos, archives, etc.
- ✅ **Real-time progress** - WebSocket updates throughout scan/recovery

---

## Production Deployment

For production use:

1. **Build frontend**:
   ```powershell
   cd frontend
   npm run build
   ```

2. **Configure production settings**:
   - Update `.env` with production values
   - Set appropriate CORS_ORIGINS
   - Configure production paths

3. **Run with production ASGI server**:
   ```powershell
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. **Serve frontend build**:
   - Use nginx, Apache, or IIS to serve `frontend/dist`
   - Configure reverse proxy to backend

---

**Ready to recover data! 🎉**
