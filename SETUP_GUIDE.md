# ReStoreX - Complete Setup Guide

## Project Overview

ReStoreX is a data recovery application with:
- **Frontend**: React + Vite + TailwindCSS
- **Backend**: FastAPI + TestDisk/PhotoRec integration

## Quick Start

### 1. Install TestDisk (Required)

**Option A: Place in Project (Recommended)**
1. Download TestDisk from: https://www.cgsecurity.org/wiki/TestDisk_Download
2. Extract the contents to `tools/testdisk/` folder:
   ```
   ReStoreX/
     └── tools/
         └── testdisk/
             ├── testdisk_win.exe
             ├── photorec_win.exe
             └── (other DLL files)
   ```
3. The application will automatically detect TestDisk from this location

**Option B: System PATH**
- Install TestDisk globally and add to system PATH

**Option C: Manual Configuration**
- Install TestDisk anywhere and set path in `backend/.env`

### Backend Setup

1. **Navigate to backend folder:**
   ```powershell
   cd backend
   ```

2. **Run setup script:**
   ```powershell
   .\setup.bat
   ```

3. **Start the backend:**
   ```powershell
   .\start.bat
   ```
   
   Backend will run at: http://localhost:3001

### Frontend Setup

1. **Navigate to frontend folder:**
   ```powershell
   cd ..\frontend
   ```

2. **Install dependencies:**
   ```powershell
   npm install
   ```

3. **Start development server:**
   ```powershell
   npm run dev
   ```
   
   Frontend will run at: http://localhost:5173

## Detailed Setup Instructions

### Backend Configuration

1. **Edit `.env` file** in backend folder:
   ```env
   HOST=0.0.0.0
   PORT=3001
   CORS_ORIGINS=http://localhost:5173
   TESTDISK_PATH=C:\path\to\testdisk.exe  # Optional
   PHOTOREC_PATH=C:\path\to\photorec.exe  # Optional
   ```

2. **Verify TestDisk installation:**
   ```powershell
   testdisk /version
   photorec /version
   ```

### Frontend Configuration

The frontend is already configured to connect to `http://localhost:3001/api`

If you need to change the backend URL, edit:
- `frontend/src/services/apiService.js` (line 1)

## Running Both Services

### Option 1: Two Terminals

**Terminal 1 (Backend):**
```powershell
cd backend
.\start.bat
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```

### Option 2: PowerShell Script

Create a `start-all.ps1` in the root folder:

```powershell
# Start backend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\start.bat"

# Wait for backend to start
Start-Sleep -Seconds 3

# Start frontend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "ReStoreX is starting..."
Write-Host "Backend: http://localhost:3001"
Write-Host "Frontend: http://localhost:5173"
```

## Testing the Application

1. **Open browser**: http://localhost:5173
2. **Select a drive** to scan
3. **Choose scan type** (Normal, Deep, etc.)
4. **Start scan** and watch real-time progress
5. **Browse recovered files**
6. **Select files** to recover
7. **Choose output location** and start recovery

## API Documentation

Once backend is running, access:
- **Swagger UI**: http://localhost:3001/docs
- **ReDoc**: http://localhost:3001/redoc

## Troubleshooting

### Backend Issues

**"TestDisk not found"**
- Install TestDisk from https://www.cgsecurity.org/
- Add to PATH or set in `.env`

**"Port 3001 already in use"**
- Change port in `backend/.env`
- Update frontend API URL accordingly

**"Permission denied" when scanning**
- Run PowerShell as Administrator
- Some drives require elevated permissions

### Frontend Issues

**"Failed to fetch" errors**
- Ensure backend is running at http://localhost:3001
- Check CORS settings in `backend/.env`

**Dependencies installation fails**
- Update npm: `npm install -g npm@latest`
- Clear cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`, then reinstall

### Connection Issues

**WebSocket connection fails**
- Ensure backend is running
- Check firewall settings
- Verify WebSocket URL in `apiService.js`

## Development Tips

### Backend Development

- **Auto-reload**: Backend auto-reloads on file changes
- **Logs**: Check console for detailed logs
- **Debug**: Add `logger.info()` or `logger.debug()` statements

### Frontend Development

- **Hot reload**: Vite provides instant updates
- **React DevTools**: Install browser extension for debugging
- **Console**: Check browser console for errors

## Project Structure

```
ReStoreX/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── requirements.txt     # Python dependencies
│   ├── setup.bat           # Setup script
│   ├── start.bat           # Start script
│   ├── .env                # Configuration
│   └── app/
│       ├── routes/         # API endpoints
│       ├── services/       # Business logic
│       └── models.py       # Data models
│
└── frontend/
    ├── package.json        # Node dependencies
    ├── vite.config.js     # Vite configuration
    └── src/
        ├── components/     # React components
        ├── services/       # API client
        └── hooks/          # Custom hooks
```

## Production Deployment

### Backend (Production)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3001 --workers 4
```

### Frontend (Production)

```bash
cd frontend
npm run build
# Serve the 'dist' folder with nginx or similar
```

## Common Commands

### Backend

```powershell
# Setup
.\setup.bat

# Start server
.\start.bat

# Install new package
pip install package-name
pip freeze > requirements.txt

# Run specific port
python main.py --port 3002
```

### Frontend

```powershell
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Support & Resources

- **TestDisk Documentation**: https://www.cgsecurity.org/wiki/TestDisk
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **Vite Docs**: https://vitejs.dev/

## License

MIT License - See LICENSE file for details
