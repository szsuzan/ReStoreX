from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.routes import drives, scan, recovery, files, explorer
from app.services.websocket_manager import websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    logger.info("Starting ReStoreX Backend...")
    logger.info(f"Version: {settings.VERSION}")
    logger.info(f"Server: {settings.HOST}:{settings.PORT}")
    yield
    logger.info("Shutting down ReStoreX Backend...")


# Create FastAPI app
app = FastAPI(
    title="ReStoreX API",
    description="Data Recovery Backend using TestDisk and PhotoRec",
    version=settings.VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(drives.router, prefix="/api", tags=["drives"])
app.include_router(scan.router, prefix="/api", tags=["scan"])
app.include_router(recovery.router, prefix="/api", tags=["recovery"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(explorer.router, prefix="/api", tags=["explorer"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    from app.services.testdisk_service import testdisk_service
    
    testdisk_available = await testdisk_service.check_testdisk()
    photorec_available = await testdisk_service.check_photorec()
    
    return {
        "status": "healthy",
        "testdisk_available": testdisk_available,
        "photorec_available": photorec_available,
        "version": settings.VERSION
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")

