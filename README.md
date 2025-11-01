# ReStoreX - Data Recovery Application

<div align="center">

![ReStoreX](https://img.shields.io/badge/ReStoreX-Data%20Recovery-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-orange)
![React](https://img.shields.io/badge/React-18+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

A powerful, user-friendly data recovery application with a modern web interface powered by TestDisk and PhotoRec.

</div>

---

## 🌟 Features

### 🔍 Advanced Scanning
- **Multiple Scan Types**: Normal, Signature File Carving, Deep, Cluster, Health Check, and Forensic scanning
- **Real-time Progress**: Live updates via WebSocket during scan operations
- **Smart File Detection**: Automatic file type recognition and categorization
- **Recovery Probability**: Intelligent estimation of file recovery chances

### 💾 Powerful Recovery
- **Batch Recovery**: Recover multiple files simultaneously
- **Custom Output Locations**: Choose where recovered files are saved
- **Live Progress Tracking**: Monitor recovery progress in real-time
- **Detailed Logging**: Complete logs of all recovery operations

### 🎨 Modern Interface
- **Intuitive Dashboard**: Clean, easy-to-navigate interface
- **File Preview**: Preview recoverable files before recovery
- **Hex Viewer**: Examine file contents at byte level
- **Advanced Filtering**: Filter by file type, size, date, and recovery chance
- **Built-in Explorer**: Browse and manage recovered files

### ⚡ Performance
- **Concurrent Operations**: Multiple scans and recoveries
- **Efficient Processing**: Optimized for speed and accuracy
- **Cross-platform**: Works on Windows, Linux, and macOS

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** - [Download](https://nodejs.org/)
- **TestDisk/PhotoRec** - [Download](https://www.cgsecurity.org/wiki/TestDisk_Download)
- **Administrator Rights** (Windows) - Required for real disk scanning

### One-Command Start (Windows)

#### For Real Disk Scanning (Recommended) ⭐

**Step 1**: Right-click `backend\start_admin.bat` → Select **"Run as administrator"**

**Step 2**: In a regular terminal:
```powershell
cd frontend
npm run dev
```

> **See full guide**: [RUN_AS_ADMIN_GUIDE.md](RUN_AS_ADMIN_GUIDE.md)

#### For Testing/Development (Mock Mode)

```powershell
.\start-all.bat
```

This will:
1. Set up the backend (if needed)
2. Start the FastAPI server (mock mode)
3. Start the React development server
4. Open the application in your browser

### Manual Setup

#### Backend Setup

```powershell
cd backend
.\setup.bat
.\start.bat
```

Backend runs at: **http://localhost:3001**

#### Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 📁 Project Structure

```
ReStoreX/
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── requirements.txt    # Python dependencies
│   ├── app/
│   │   ├── routes/         # API endpoints
│   │   │   ├── drives.py   # Drive management
│   │   │   ├── scan.py     # Scan operations
│   │   │   ├── recovery.py # Recovery operations
│   │   │   ├── files.py    # File operations
│   │   │   └── explorer.py # File browsing
│   │   ├── services/       # Business logic
│   │   │   ├── drive_service.py
│   │   │   ├── scan_service.py
│   │   │   ├── recovery_service.py
│   │   │   ├── testdisk_service.py
│   │   │   └── websocket_manager.py
│   │   ├── models.py       # Data models
│   │   └── config.py       # Configuration
│   └── README.md           # Backend documentation
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API client
│   │   ├── hooks/          # Custom hooks
│   │   └── data/           # Mock data
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
│
├── SETUP_GUIDE.md          # Detailed setup instructions
└── start-all.bat           # Quick start script
```

---

## 🔧 Configuration

### Backend Configuration

Edit `backend/.env`:

```env
# Server Settings
HOST=0.0.0.0
PORT=3001

# CORS Settings
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# TestDisk Paths (optional if in PATH)
TESTDISK_PATH=
PHOTOREC_PATH=

# Directories
TEMP_DIR=./temp
RECOVERY_DIR=./recovered_files

# Performance
MAX_CONCURRENT_SCANS=2
MAX_CONCURRENT_RECOVERIES=1
```

### Frontend Configuration

The frontend automatically connects to `http://localhost:3001/api`

To change the backend URL, edit:
- `frontend/src/services/apiService.js`

---

## 📖 Usage Guide

### 1. Select a Drive
- Launch the application
- View all available drives on the dashboard
- Click on a drive to select it

### 2. Choose Scan Type
- **Normal Scan**: Quick scan for recently deleted files (5-15 minutes)
- **Signature File Carving Scan**: Smart recovery of photos, videos, documents & audio files (10-25 minutes) ⭐ Recommended
- **Deep Scan**: Comprehensive sector-by-sector analysis for maximum recovery (30-120 minutes)
- **Cluster Scan**: View disk clusters and hex data for advanced analysis (15-45 minutes)
- **Disk Health Scan**: Read SMART data, calculate health scores, and create surface map (10-30 minutes)
- **Forensic Scan**: Professional forensic analysis with detailed logging (60+ minutes)

### 3. Monitor Progress
- Watch real-time progress updates
- View files as they're discovered
- See estimated time remaining

### 4. Browse Results
- Filter by file type (Images, Videos, Documents, etc.)
- Sort by name, size, date, or recovery chance
- Search for specific files
- Preview file contents

### 5. Recover Files
- Select files to recover
- Choose output location
- Start recovery process
- Monitor progress with detailed logs

---

## 🔌 API Endpoints

### Drive Operations
- `GET /api/drives` - List all drives
- `GET /api/drives/{id}` - Get drive details
- `POST /api/drives/{id}/validate` - Validate drive

### Scan Operations
- `POST /api/scan/start` - Start scan
- `GET /api/scan/{id}/status` - Get scan status
- `GET /api/scan/{id}/results` - Get scan results
- `POST /api/scan/{id}/cancel` - Cancel scan

### Recovery Operations
- `POST /api/recovery/start` - Start recovery
- `GET /api/recovery/{id}/status` - Get recovery status
- `GET /api/recovery/{id}/logs` - Get recovery logs
- `POST /api/recovery/{id}/cancel` - Cancel recovery

### File Operations
- `GET /api/files/{id}` - Get file info
- `GET /api/files/{id}/thumbnail` - Get thumbnail
- `GET /api/files/{id}/preview` - Get preview
- `GET /api/files/{id}/hex` - Get hex data

### WebSocket
- `WS /ws` - Real-time updates

Full API documentation: **http://localhost:3001/docs**

---

## 🧪 Testing

### Test Backend Setup

```powershell
cd backend
python test_setup.py
```

This will verify:
- ✓ Module imports
- ✓ TestDisk installation
- ✓ Drive detection

---

## 🛠️ Development

### Backend Development

```bash
cd backend
# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
python main.py
```

### Frontend Development

```bash
cd frontend
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

---

## 📊 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **WebSockets** - Real-time communication
- **TestDisk/PhotoRec** - Data recovery engine
- **psutil** - System and process utilities
- **Pydantic** - Data validation

### Frontend
- **React** - UI library
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **WebSocket API** - Real-time updates

---

## ⚠️ Important Notes

- **Administrator Rights**: Some operations require elevated privileges
- **Data Safety**: Always backup important data before recovery operations
- **Performance**: Deep scans can take time depending on disk size
- **TestDisk**: Make sure TestDisk/PhotoRec is properly installed

---

## 🐛 Troubleshooting

### TestDisk Not Found
```powershell
# Install TestDisk
# Download from: https://www.cgsecurity.org/
# Add to PATH or configure in .env
```

### Port Already in Use
```powershell
# Change port in backend/.env
PORT=3002
```

### Permission Denied
```powershell
# Run PowerShell as Administrator
# Right-click PowerShell -> Run as Administrator
```

### CORS Errors
```env
# Add frontend URL to backend/.env
CORS_ORIGINS=http://localhost:5173
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [TestDisk & PhotoRec](https://www.cgsecurity.org/) by CGSecurity
- [FastAPI](https://fastapi.tiangolo.com/) framework
- [React](https://react.dev/) library
- [Vite](https://vitejs.dev/) build tool
- [TailwindCSS](https://tailwindcss.com/) framework

---

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review the setup guide in `SETUP_GUIDE.md`

---

## 🚧 Future Enhancements

- [ ] Cloud storage integration
- [ ] Email notifications for long operations
- [ ] Advanced file repair capabilities
- [ ] Scheduled automatic scans
- [ ] Multi-language support
- [ ] Mobile app version

---

<div align="center">

**Made with ❤️ for data recovery**

[Documentation](SETUP_GUIDE.md) • [API Docs](http://localhost:3001/docs) • [Report Bug](https://github.com/szsuzan/ReStoreX/issues)

</div>
