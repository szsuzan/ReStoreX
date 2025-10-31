import asyncio
import uuid
import time
import logging
import os
import shutil
from typing import Dict, List, Optional
from datetime import datetime

from app.models import RecoveryProgress
from app.services.websocket_manager import websocket_manager
from app.config import settings

logger = logging.getLogger(__name__)


class RecoveryService:
    def __init__(self):
        self.active_recoveries: Dict[str, Dict] = {}
        self.recovery_logs: Dict[str, List[str]] = {}
        self.file_metadata_cache: Dict[str, Dict] = {}  # Cache for file metadata

    def cache_file_metadata(self, file_id: str, metadata: dict):
        """Cache file metadata for recovery"""
        self.file_metadata_cache[file_id] = metadata

    async def start_recovery(self, file_ids: List[str], output_path: str, options: dict) -> str:
        """Start a new recovery operation"""
        recovery_id = str(uuid.uuid4())
        
        # Validate output path
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create output directory: {e}")
                raise Exception(f"Invalid output path: {output_path}")
        
        recovery_info = {
            "recovery_id": recovery_id,
            "file_ids": file_ids,
            "output_path": output_path,
            "options": options,
            "status": "running",
            "progress": 0.0,
            "start_time": time.time(),
            "files_recovered": 0,
            "total_files": len(file_ids),
            "current_file": ""
        }
        
        self.active_recoveries[recovery_id] = recovery_info
        self.recovery_logs[recovery_id] = []
        
        # Start the recovery in the background
        asyncio.create_task(self._run_recovery(recovery_id, file_ids, output_path, options))
        
        return recovery_id

    async def _run_recovery(self, recovery_id: str, file_ids: List[str], output_path: str, options: dict):
        """Run the actual recovery operation"""
        try:
            logger.info(f"Starting recovery {recovery_id} for {len(file_ids)} files")
            
            recovery_info = self.active_recoveries[recovery_id]
            self._add_log(recovery_id, f"Recovery started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._add_log(recovery_id, f"Recovering {len(file_ids)} files to {output_path}")
            
            # Process each file
            for i, file_id in enumerate(file_ids):
                if recovery_info["status"] == "cancelled":
                    self._add_log(recovery_id, "Recovery cancelled by user")
                    break
                
                # Get file metadata from cache or use default
                file_metadata = self.file_metadata_cache.get(file_id, {})
                file_name = file_metadata.get('name', f"recovered_file_{i+1}.dat")
                file_type = file_metadata.get('type', 'dat').lower()
                
                recovery_info["current_file"] = file_name
                
                self._add_log(recovery_id, f"Recovering {file_name}...")
                
                # Create actual file (mock data for now)
                try:
                    # Create subdirectories if needed
                    if options.get('createSubdirectories', True):
                        type_folder = os.path.join(output_path, file_type.upper())
                        os.makedirs(type_folder, exist_ok=True)
                        file_path = os.path.join(type_folder, file_name)
                    else:
                        file_path = os.path.join(output_path, file_name)
                    
                    # Create mock file content (in real implementation, recover actual data)
                    mock_data = f"Recovered file: {file_name}\nFile ID: {file_id}\nRecovered at: {datetime.now()}\n".encode('utf-8')
                    mock_data += b'\x00' * (1024 * 100)  # Add 100KB of data
                    
                    with open(file_path, 'wb') as f:
                        f.write(mock_data)
                    
                    self._add_log(recovery_id, f"Successfully recovered {file_name} to {file_path}")
                except Exception as e:
                    self._add_log(recovery_id, f"Failed to recover {file_name}: {str(e)}")
                    logger.error(f"Failed to create file {file_path}: {e}")
                    
                    # Create mock file content (in real implementation, recover actual data)
                    mock_data = f"Recovered file {i+1}\nFile ID: {file_id}\nRecovered at: {datetime.now()}\n".encode('utf-8')
                    mock_data += b'\x00' * (1024 * 100)  # Add 100KB of data
                    
                    with open(file_path, 'wb') as f:
                        f.write(mock_data)
                    
                    self._add_log(recovery_id, f"Successfully recovered {file_name} to {file_path}")
                except Exception as e:
                    self._add_log(recovery_id, f"Failed to recover {file_name}: {str(e)}")
                    logger.error(f"Failed to create file {file_path}: {e}")
                
                # Simulate recovery time
                await asyncio.sleep(0.5)
                
                # Update progress
                recovery_info["files_recovered"] = i + 1
                recovery_info["progress"] = ((i + 1) / len(file_ids)) * 100
                
                # Broadcast progress
                await self._broadcast_progress(recovery_id)
            
            if recovery_info["status"] == "cancelled":
                recovery_info["status"] = "cancelled"
            else:
                recovery_info["status"] = "completed"
                recovery_info["progress"] = 100.0
                self._add_log(recovery_id, f"Recovery completed successfully. {len(file_ids)} files recovered.")
            
            # Notify completion
            await self._broadcast_progress(recovery_id)
            
        except Exception as e:
            logger.error(f"Error during recovery {recovery_id}: {e}")
            self.active_recoveries[recovery_id]["status"] = "error"
            self.active_recoveries[recovery_id]["error"] = str(e)
            self._add_log(recovery_id, f"Error: {str(e)}")
            await self._broadcast_progress(recovery_id)

    async def _broadcast_progress(self, recovery_id: str):
        """Broadcast recovery progress via WebSocket"""
        recovery_info = self.active_recoveries[recovery_id]
        
        # Format progress to 2 decimal places for consistency
        progress_value = round(recovery_info["progress"], 2)
        
        progress_data = RecoveryProgress(
            recoveryId=recovery_id,
            isRecovering=recovery_info["status"] == "running",
            progress=progress_value,
            currentFile=recovery_info["current_file"],
            filesRecovered=recovery_info["files_recovered"],
            totalFiles=recovery_info["total_files"],
            estimatedTimeRemaining=self._calculate_eta(recovery_info),
            status=recovery_info["status"]
        )
        
        await websocket_manager.broadcast({
            "type": "recovery_progress",
            "data": progress_data.dict()
        })

    def _calculate_eta(self, recovery_info: Dict) -> str:
        """Calculate estimated time remaining"""
        elapsed = time.time() - recovery_info["start_time"]
        progress = recovery_info["progress"]
        
        if progress <= 0:
            return "Calculating..."
        
        total_time = (elapsed / progress) * 100
        remaining = total_time - elapsed
        
        if remaining < 0:
            return "0s"
        
        minutes = int(remaining / 60)
        seconds = int(remaining % 60)
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def _add_log(self, recovery_id: str, message: str):
        """Add a log message for a recovery operation"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if recovery_id not in self.recovery_logs:
            self.recovery_logs[recovery_id] = []
        
        self.recovery_logs[recovery_id].append(log_entry)
        logger.info(f"Recovery {recovery_id}: {message}")

    async def get_recovery_status(self, recovery_id: str) -> Optional[Dict]:
        """Get the status of a recovery operation"""
        if recovery_id not in self.active_recoveries:
            return None
        
        recovery_info = self.active_recoveries[recovery_id]
        
        return {
            "recoveryId": recovery_id,
            "isRecovering": recovery_info["status"] == "running",
            "progress": recovery_info["progress"],
            "currentFile": recovery_info["current_file"],
            "filesRecovered": recovery_info["files_recovered"],
            "totalFiles": recovery_info["total_files"],
            "estimatedTimeRemaining": self._calculate_eta(recovery_info),
            "status": recovery_info["status"]
        }

    async def cancel_recovery(self, recovery_id: str) -> bool:
        """Cancel a running recovery operation"""
        if recovery_id not in self.active_recoveries:
            return False
        
        self.active_recoveries[recovery_id]["status"] = "cancelled"
        self._add_log(recovery_id, "Cancellation requested")
        await self._broadcast_progress(recovery_id)
        return True

    async def get_recovery_logs(self, recovery_id: str) -> List[str]:
        """Get the logs for a recovery operation"""
        if recovery_id not in self.recovery_logs:
            return []
        
        return self.recovery_logs[recovery_id]


recovery_service = RecoveryService()
