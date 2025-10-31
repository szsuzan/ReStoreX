from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.models import DirectoryContents, DirectoryItem
import logging
import os
import platform
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/explorer/directory", response_model=DirectoryContents)
async def get_directory_contents(path: str = Query(...)):
    """Get the contents of a directory"""
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Directory not found")
        
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="Path is not a directory")
        
        items = []
        
        try:
            entries = os.listdir(path)
            
            for entry in entries:
                entry_path = os.path.join(path, entry)
                
                try:
                    is_dir = os.path.isdir(entry_path)
                    stats = os.stat(entry_path)
                    
                    item = DirectoryItem(
                        id=entry_path,
                        name=entry,
                        type="folder" if is_dir else "file",
                        size=None if is_dir else _format_bytes(stats.st_size),
                        dateModified=datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        path=entry_path,
                        itemCount=len(os.listdir(entry_path)) if is_dir else None
                    )
                    items.append(item)
                except Exception as e:
                    logger.warning(f"Error reading entry {entry_path}: {e}")
                    continue
            
            # Sort: folders first, then files, alphabetically
            items.sort(key=lambda x: (x.type == "file", x.name.lower()))
            
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        return DirectoryContents(path=path, items=items)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting directory contents for {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explorer/open")
async def open_in_system_explorer(request: dict):
    """Open a path in the system's file explorer"""
    try:
        path = request.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="Path is required")
        
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Path not found")
        
        system = platform.system()
        
        try:
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])
            
            return {"message": f"Opened {path} in system explorer"}
        except Exception as e:
            logger.error(f"Error opening path in explorer: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to open path: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in open_in_system_explorer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explorer/directory")
async def create_directory(request: dict):
    """Create a new directory"""
    try:
        path = request.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="Path is required")
        
        if os.path.exists(path):
            raise HTTPException(status_code=400, detail="Directory already exists")
        
        os.makedirs(path, exist_ok=True)
        
        return {
            "message": f"Directory created successfully",
            "path": path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/explorer/items")
async def delete_items(request: dict):
    """Delete files or directories"""
    try:
        paths = request.get("paths", [])
        if not paths:
            raise HTTPException(status_code=400, detail="No paths provided")
        
        deleted = []
        errors = []
        
        for path in paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    deleted.append(path)
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                    deleted.append(path)
                else:
                    errors.append({"path": path, "error": "Path not found"})
            except Exception as e:
                errors.append({"path": path, "error": str(e)})
        
        return {
            "message": f"Deleted {len(deleted)} items",
            "deleted": deleted,
            "errors": errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _format_bytes(bytes: int) -> str:
    """Format bytes into human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"
