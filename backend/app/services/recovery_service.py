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
            
            # Check if we have any indexed files (from deep scan)
            indexed_files = []
            regular_files = []
            
            for file_id in file_ids:
                file_metadata = self.file_metadata_cache.get(file_id, {})
                file_status = file_metadata.get('status', 'unknown')
                
                logger.info(f"File {file_id}: status={file_status}, name={file_metadata.get('name', 'unknown')}")
                logger.debug(f"   Metadata: offset={file_metadata.get('offset', 0)}, drive_path={file_metadata.get('drive_path', 'unknown')}")
                
                if file_status == 'indexed':
                    indexed_files.append(file_metadata)
                    logger.info(f"   → Added to INDEXED files list (will read from drive)")
                else:
                    regular_files.append((file_id, file_metadata))
                    logger.info(f"   → Added to REGULAR files list (will copy from temp)")
            
            # Process indexed files using direct drive recovery
            if indexed_files:
                logger.info(f"Found {len(indexed_files)} indexed files - using direct drive recovery")
                self._add_log(recovery_id, f"Recovering {len(indexed_files)} indexed files from drive...")
                
                # Broadcast initial progress to show recovery dialog
                recovery_info["current_file"] = "Starting recovery..."
                recovery_info["progress"] = 0.0
                await self._broadcast_progress(recovery_id)
                
                # Import recovery service
                from app.services.python_recovery_service import PythonRecoveryService
                python_recovery = PythonRecoveryService()
                
                # Define progress callback
                async def indexed_progress_callback(progress_data: dict):
                    if recovery_info["status"] == "cancelled":
                        return
                    
                    current_filename = progress_data.get('current_filename', f"File {progress_data.get('current_file', 0)}")
                    recovery_info["current_file"] = current_filename
                    recovery_info["files_recovered"] = progress_data.get('recovered', 0)
                    recovery_info["progress"] = progress_data.get('progress', 0)
                    
                    logger.info(f"📊 Progress update: {recovery_info['progress']:.1f}% - {current_filename}")
                    
                    await self._broadcast_progress(recovery_id)
                    
                    # Small delay to allow UI to update
                    await asyncio.sleep(0.05)
                
                # Recover indexed files
                result = await python_recovery.recover_selected_files(
                    file_list=indexed_files,
                    output_dir=output_path,
                    progress_callback=indexed_progress_callback,
                    create_subdirectories=options.get('createSubdirectories', True)
                )
                
                self._add_log(recovery_id, f"Indexed files recovery: {result['recovered_count']} succeeded, {result['failed_count']} failed")
                
                if result['failed_count'] > 0:
                    for res in result.get('results', []):
                        if res['status'] == 'failed':
                            self._add_log(recovery_id, f"Failed: {res['filename']} - {res.get('reason', 'Unknown error')}")
            
            # Process regular files (already recovered by scan)
            successfully_copied_temp_files = []  # Track temp files to delete after successful copy
            
            for i, (file_id, file_metadata) in enumerate(regular_files):
                if recovery_info["status"] == "cancelled":
                    self._add_log(recovery_id, "Recovery cancelled by user")
                    break
                
                file_name = file_metadata.get('name', f"recovered_file_{i+1}.dat")
                file_type = file_metadata.get('type', 'dat').lower()
                file_path_from_scan = file_metadata.get('path', '')
                
                recovery_info["current_file"] = file_name
                
                self._add_log(recovery_id, f"Recovering {file_name}...")
                
                try:
                    # Determine output location
                    if options.get('createSubdirectories', True):
                        type_folder = os.path.join(output_path, file_type.upper())
                        os.makedirs(type_folder, exist_ok=True)
                        dest_file_path = os.path.join(type_folder, file_name)
                    else:
                        dest_file_path = os.path.join(output_path, file_name)
                    
                    # If the file was already recovered by scan (in temp location),
                    # copy it to the final destination
                    if file_path_from_scan and os.path.exists(file_path_from_scan):
                        # Copy the already recovered file
                        shutil.copy2(file_path_from_scan, dest_file_path)
                        self._add_log(recovery_id, f"Successfully recovered {file_name} to {dest_file_path}")
                        recovery_info["files_recovered"] += 1
                        
                        # Mark temp file for deletion
                        successfully_copied_temp_files.append(file_path_from_scan)
                    else:
                        # File not found in scan results
                        self._add_log(recovery_id, f"Warning: Source file not found for {file_name}. File may need to be re-scanned.")
                        logger.warning(f"Recovery source file not found: {file_path_from_scan}")
                        continue
                    
                except Exception as e:
                    self._add_log(recovery_id, f"Failed to recover {file_name}: {str(e)}")
                    logger.error(f"Failed to recover file {file_name}: {e}")
                
                # Update progress
                base_progress = (len(indexed_files) / len(file_ids)) * 100 if indexed_files else 0
                current_progress = ((i + 1) / len(regular_files)) * (100 - base_progress) if regular_files else 0
                recovery_info["progress"] = base_progress + current_progress
                
                # Broadcast progress
                await self._broadcast_progress(recovery_id)
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
            
            # Clean up successfully copied temp files
            if successfully_copied_temp_files:
                logger.info(f"🗑️ Cleaning up {len(successfully_copied_temp_files)} temporary files after successful recovery...")
                for temp_file in successfully_copied_temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                            logger.debug(f"Deleted temp file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {temp_file}: {e}")
                logger.info("✅ Temporary files cleaned up")
            
            if recovery_info["status"] == "cancelled":
                recovery_info["status"] = "cancelled"
            else:
                recovery_info["status"] = "completed"
                recovery_info["progress"] = 100.0
                self._add_log(recovery_id, f"Recovery completed successfully. {recovery_info['files_recovered']} files recovered.")
            
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
