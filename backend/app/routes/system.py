from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.system_service import SystemService
from app.services.websocket_manager import websocket_manager
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
system_service = SystemService()


@router.get("/system/performance")
async def get_system_performance():
    """Get current system performance metrics"""
    try:
        performance = system_service.get_performance_metrics()
        return {"status": "success", "data": performance}
    except Exception as e:
        logger.error(f"Error getting system performance: {e}")
        return {"status": "error", "message": str(e)}


@router.websocket("/system/performance/stream")
async def system_performance_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time system performance updates"""
    await websocket_manager.connect(websocket)
    websocket_manager.subscribe(websocket, "system_performance")
    
    try:
        # Start the background task to send performance updates
        update_task = asyncio.create_task(send_performance_updates(websocket))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                # Handle any client messages if needed
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        update_task.cancel()
        websocket_manager.disconnect(websocket)


async def send_performance_updates(websocket: WebSocket):
    """Send performance updates every 2 seconds"""
    try:
        while True:
            try:
                performance = system_service.get_performance_metrics()
                await websocket_manager.send_personal_message(
                    {
                        "type": "system_performance",
                        "data": performance
                    },
                    websocket
                )
                await asyncio.sleep(2)  # Update every 2 seconds
            except Exception as e:
                logger.error(f"Error sending performance update: {e}")
                break
    except asyncio.CancelledError:
        logger.info("Performance update task cancelled")
