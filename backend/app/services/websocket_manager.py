from fastapi import WebSocket
from typing import List, Dict
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # Remove from all subscriptions
        for topic in self.subscriptions:
            if websocket in self.subscriptions[topic]:
                self.subscriptions[topic].remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    def subscribe(self, websocket: WebSocket, topic: str):
        """Subscribe a client to a specific topic"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        if websocket not in self.subscriptions[topic]:
            self.subscriptions[topic].append(websocket)

    async def publish(self, topic: str, message: dict):
        """Publish a message to all subscribers of a topic"""
        if topic not in self.subscriptions:
            return
        
        disconnected = []
        for connection in self.subscriptions[topic]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error publishing to topic {topic}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


websocket_manager = WebSocketManager()
