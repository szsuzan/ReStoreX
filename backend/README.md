# ReStoreX Backend

A powerful FastAPI-based backend for data recovery operations using TestDisk and PhotoRec.

## Features

- 🔍 **Multiple Scan Types**: Normal, Deep, Cluster, Health, and Signature scans
- 💾 **Drive Management**: Automatic detection and validation of available drives
- 🔄 **Real-time Progress**: WebSocket support for live scan and recovery updates
- 📁 **File Recovery**: Efficient file recovery with progress tracking
- 🔎 **File Analysis**: Hex viewer, metadata extraction, and file preview
- 📂 **Explorer Integration**: Browse directories and manage recovered files
- 🎯 **Smart Filtering**: Filter and sort recovered files by type, size, date, and recovery chance

## Prerequisites

### Required Software

1. **Python 3.8+**
   - Download from [python.org](https://www.python.org/downloads/)

2. **TestDisk & PhotoRec**
   - **Windows**: Download from [CGSecurity](https://www.cgsecurity.org/wiki/TestDisk_Download)
     - Extract to a folder (e.g., `C:\Program Files\TestDisk`)
     - Add the folder to your system PATH, or configure the path in `.env`
   
   - **Linux**:
     ```bash
     sudo apt-get install testdisk
     ```
   
   - **macOS**:
     ```bash
     brew install testdisk
     ```

## Installation

### 1. Clone the Repository

```bash
cd ReStoreX/backend
```

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and configure as needed:

```env
# Backend Configuration
HOST=0.0.0.0
PORT=3001

# CORS Settings (add your frontend URL)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# TestDisk/PhotoRec paths (leave empty if in system PATH)
TESTDISK_PATH=
PHOTOREC_PATH=

# Directories
TEMP_DIR=./temp
RECOVERY_DIR=./recovered_files

# Operational limits
MAX_CONCURRENT_SCANS=2
MAX_CONCURRENT_RECOVERIES=1
```

### 5. Verify TestDisk Installation

Check if TestDisk and PhotoRec are accessible:

**Windows:**
```powershell
testdisk /version
photorec /version
```

**Linux/macOS:**
```bash
testdisk --version
photorec --version
```

## Running the Server

### Development Mode

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 3001 --workers 4
```

The server will start at `http://localhost:3001`

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:3001/docs
- **ReDoc**: http://localhost:3001/redoc

## API Endpoints

### Health Check
- `GET /api/health` - Check API and TestDisk availability

### Drives
- `GET /api/drives` - List all available drives
- `GET /api/drives/{drive_id}` - Get specific drive info
- `POST /api/drives/{drive_id}/validate` - Validate drive for scanning

### Scan Operations
- `POST /api/scan/start` - Start a new scan
- `GET /api/scan/{scan_id}/status` - Get scan status
- `GET /api/scan/{scan_id}/results` - Get scan results with filters
- `POST /api/scan/{scan_id}/cancel` - Cancel running scan

### Recovery Operations
- `POST /api/recovery/start` - Start file recovery
- `GET /api/recovery/{recovery_id}/status` - Get recovery status
- `GET /api/recovery/{recovery_id}/logs` - Get recovery logs
- `POST /api/recovery/{recovery_id}/cancel` - Cancel recovery

### File Operations
- `GET /api/files/{file_id}` - Get file information
- `GET /api/files/{file_id}/thumbnail` - Get file thumbnail
- `GET /api/files/{file_id}/preview` - Get file preview
- `GET /api/files/{file_id}/hex` - Get hex data for hex viewer
- `POST /api/files/{file_id}/analyze` - Analyze file

### Explorer
- `GET /api/explorer/directory` - Browse directory contents
- `POST /api/explorer/open` - Open path in system explorer
- `POST /api/explorer/directory` - Create new directory
- `DELETE /api/explorer/items` - Delete files/folders

### WebSocket
- `WS /ws` - Real-time updates for scans and recoveries

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
├── .gitignore            # Git ignore rules
├── app/
│   ├── config.py         # Configuration settings
│   ├── models.py         # Pydantic models
│   ├── routes/           # API routes
│   │   ├── drives.py     # Drive management endpoints
│   │   ├── scan.py       # Scan operation endpoints
│   │   ├── recovery.py   # Recovery operation endpoints
│   │   ├── files.py      # File operation endpoints
│   │   └── explorer.py   # File explorer endpoints
│   └── services/         # Business logic
│       ├── drive_service.py        # Drive detection and management
│       ├── scan_service.py         # Scan operations
│       ├── recovery_service.py     # Recovery operations
│       ├── testdisk_service.py     # TestDisk/PhotoRec integration
│       └── websocket_manager.py    # WebSocket management
├── temp/                 # Temporary files (auto-created)
└── recovered_files/      # Default recovery output (auto-created)
```

## Usage Examples

### Start a Scan

```bash
curl -X POST http://localhost:3001/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "driveId": "c-",
    "scanType": "normal",
    "options": {
      "deepScan": false,
      "skipBadSectors": true
    }
  }'
```

### Check Scan Status

```bash
curl http://localhost:3001/api/scan/{scan_id}/status
```

### Start Recovery

```bash
curl -X POST http://localhost:3001/api/recovery/start \
  -H "Content-Type: application/json" \
  -d '{
    "fileIds": ["file1", "file2", "file3"],
    "outputPath": "C:\\Recovery\\Output",
    "options": {}
  }'
```

## WebSocket Usage

Connect to `ws://localhost:3001/ws` to receive real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:3001/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'scan_progress') {
    console.log('Scan progress:', data.data);
  } else if (data.type === 'recovery_progress') {
    console.log('Recovery progress:', data.data);
  }
};
```

## Troubleshooting

### TestDisk Not Found

**Error**: `TestDisk not found in system PATH`

**Solution**:
1. Ensure TestDisk is installed
2. Add TestDisk directory to system PATH, or
3. Set `TESTDISK_PATH` in `.env` file

### Port Already in Use

**Error**: `Address already in use`

**Solution**:
1. Change the port in `.env`:
   ```env
   PORT=3002
   ```
2. Or stop the process using port 3001

### Permission Denied (Linux/macOS)

**Error**: `Permission denied` when scanning drives

**Solution**:
Run with sudo or adjust permissions:
```bash
sudo python main.py
```

### CORS Errors

**Error**: CORS policy blocking requests from frontend

**Solution**:
Add your frontend URL to `CORS_ORIGINS` in `.env`:
```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
```

### Linting

```bash
pylint app/
```

## Important Notes

⚠️ **Administrator Rights**: Some operations (especially disk scanning) may require administrator/root privileges.

⚠️ **Data Safety**: Always ensure you have backups. Recovery operations can modify disk data.

⚠️ **Performance**: Deep scans can take significant time depending on disk size and health.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Open an issue on GitHub
- Check the API documentation at `/docs`
- Review TestDisk documentation at [cgsecurity.org](https://www.cgsecurity.org/)

## Acknowledgments

- TestDisk & PhotoRec by CGSecurity
- FastAPI framework
- Python community
