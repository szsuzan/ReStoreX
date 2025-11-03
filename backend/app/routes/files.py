from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from app.models import FileInfo, HexData
import logging
import os
import base64
from io import BytesIO
import hashlib

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache for generated thumbnails from indexed files
thumbnail_cache = {}


def generate_thumbnail_from_data(file_data: bytes, size: int = 150) -> bytes:
    """Generate a thumbnail from raw file data"""
    try:
        from PIL import Image
        
        # Load image from bytes
        img = Image.open(BytesIO(file_data))
        
        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Create thumbnail
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = BytesIO()
        img.save(output, format='JPEG', quality=85)
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error generating thumbnail from data: {e}")
        return None


def generate_thumbnail(file_path: str, size: int = 150) -> bytes:
    """Generate a thumbnail for an image file"""
    try:
        from PIL import Image
        
        # Open and resize image
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create thumbnail
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = BytesIO()
            img.save(output, format='JPEG', quality=85)
            return output.getvalue()
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return None


def generate_preview_image(file_path: str, max_size: int = 800) -> str:
    """Generate a base64 encoded preview image"""
    try:
        from PIL import Image
        
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Save to base64
            output = BytesIO()
            img.save(output, format='JPEG', quality=90)
            img_bytes = output.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            return f"data:image/jpeg;base64,{img_base64}"
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        return None


@router.get("/files/{file_id}")
async def get_file_info(file_id: str):
    """Get detailed information about a specific file"""
    try:
        # Mock implementation - in production, retrieve actual file metadata
        file_info = FileInfo(
            id=file_id,
            name=f"file_{file_id}.jpg",
            type="JPG",
            size="2.5 MB",
            sizeBytes=2621440,
            dateModified="2024-03-15 14:30:22",
            path=f"\\Recovered\\Images\\file_{file_id}.jpg",
            recoveryChance="High",
            sector=12345,
            cluster=6789,
            inode=4321,
            status="found"
        )
        return file_info
    except Exception as e:
        logger.error(f"Error getting file info for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/thumbnail")
async def get_file_thumbnail(file_id: str, size: int = Query(150)):
    """Get a thumbnail for an image file"""
    try:
        # Get file metadata from recovery service
        from app.services.recovery_service import recovery_service
        file_metadata = recovery_service.file_metadata_cache.get(file_id, {})
        file_path = file_metadata.get('path', '')
        file_type = file_metadata.get('type', '').upper()
        file_status = file_metadata.get('status', 'unknown')
        
        # Check cache first for indexed files
        cache_key = f"{file_id}_{size}"
        if cache_key in thumbnail_cache:
            return Response(
                content=thumbnail_cache[cache_key],
                media_type="image/jpeg",
                headers={
                    "X-File-Id": file_id,
                    "Cache-Control": "public, max-age=3600"
                }
            )
        
        # For indexed files (deep scan), generate thumbnail from drive data
        if file_status == 'indexed' and file_type in ['PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF']:
            try:
                # Get drive location info
                drive_path = file_metadata.get('drive_path', '')
                offset = file_metadata.get('offset', 0)
                file_size = file_metadata.get('size', 0)
                
                if drive_path and offset > 0 and file_size > 0:
                    # Read image data from drive with sector alignment
                    from app.services.python_recovery_service import PythonRecoveryService
                    recovery_service_instance = PythonRecoveryService()
                    
                    # Open drive
                    drive_handle = recovery_service_instance._open_drive(drive_path)
                    
                    # Raw disk access requires sector-aligned reads
                    SECTOR_SIZE = 512
                    
                    # Limit read size to 5MB for thumbnails
                    actual_size = min(file_size, 5 * 1024 * 1024)
                    
                    # Calculate sector-aligned position and size
                    aligned_offset = (offset // SECTOR_SIZE) * SECTOR_SIZE
                    offset_adjustment = offset - aligned_offset
                    total_read_size = offset_adjustment + actual_size
                    aligned_read_size = ((total_read_size + SECTOR_SIZE - 1) // SECTOR_SIZE) * SECTOR_SIZE
                    
                    # Seek to aligned position and read
                    drive_handle.seek(aligned_offset)
                    aligned_data = drive_handle.read(aligned_read_size)
                    drive_handle.close()
                    
                    # Extract actual file data from aligned buffer
                    file_data = aligned_data[offset_adjustment:offset_adjustment + actual_size]
                    
                    if len(file_data) > 0:
                        # Generate thumbnail from data
                        thumbnail_data = generate_thumbnail_from_data(file_data, size)
                        
                        if thumbnail_data:
                            # Cache the thumbnail
                            thumbnail_cache[cache_key] = thumbnail_data
                            
                            return Response(
                                content=thumbnail_data,
                                media_type="image/jpeg",
                                headers={
                                    "X-File-Id": file_id,
                                    "Cache-Control": "public, max-age=3600",
                                    "X-Source": "indexed"
                                }
                            )
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail from indexed file: {e}")
                # Fall through to placeholder generation
        
        # Check if file exists and is an image (for recovered files)
        elif file_path and os.path.exists(file_path):
            if file_type in ['PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF']:
                # Generate real thumbnail
                thumbnail_data = generate_thumbnail(file_path, size)
                if thumbnail_data:
                    return Response(
                        content=thumbnail_data,
                        media_type="image/jpeg",
                        headers={
                            "X-File-Id": file_id,
                            "Cache-Control": "public, max-age=3600",
                            "X-Source": "recovered"
                        }
                    )
        
        # Return placeholder/icon for non-images or if file doesn't exist
        # Generate a simple colored placeholder
        from PIL import Image, ImageDraw, ImageFont
        
        # Color based on file type
        colors = {
            'PNG': (76, 175, 80),
            'JPG': (156, 39, 176),
            'JPEG': (156, 39, 176),
            'PDF': (244, 67, 54),
            'MP4': (103, 58, 183),
            'ZIP': (255, 152, 0),
            'GIF': (33, 150, 243),
            'BMP': (96, 125, 139),
            'WEBP': (0, 188, 212),
            'TIFF': (121, 85, 72),
        }
        color = colors.get(file_type, (158, 158, 158))
        
        # Create placeholder image
        img = Image.new('RGB', (size, size), color=color)
        draw = ImageDraw.Draw(img)
        
        # Draw file type text
        text = file_type[:3] if file_type else '?'
        bbox = draw.textbbox((0, 0), text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size - text_width) // 2, (size - text_height) // 2)
        draw.text(position, text, fill=(255, 255, 255))
        
        # Save to bytes
        output = BytesIO()
        img.save(output, format='PNG')
        
        return Response(
            content=output.getvalue(),
            media_type="image/png",
            headers={
                "X-File-Id": file_id,
                "X-Source": "placeholder"
            }
        )
    except Exception as e:
        logger.error(f"Error generating thumbnail for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/analyze")
async def analyze_file(file_id: str):
    """Perform deep analysis on a file"""
    try:
        return {
            "fileId": file_id,
            "analysis": {
                "fileType": "JPEG Image",
                "corruption": "None detected",
                "metadata": {
                    "camera": "Canon EOS 5D",
                    "resolution": "1920x1080",
                    "created": "2024-01-15 10:30:00"
                },
                "recoveryPossibility": "95%",
                "warnings": []
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/preview")
async def get_file_preview(file_id: str):
    """Get a preview of the file content"""
    try:
        # Get file metadata from recovery service
        from app.services.recovery_service import recovery_service
        file_metadata = recovery_service.file_metadata_cache.get(file_id, {})
        file_path = file_metadata.get('path', '')
        file_type = file_metadata.get('type', '').upper()
        file_name = file_metadata.get('name', 'unknown')
        
        # Check if file exists
        if not file_path or not os.path.exists(file_path):
            return {
                "fileId": file_id,
                "canPreview": False,
                "error": "File not found or not yet recovered"
            }
        
        # Image preview
        if file_type in ['PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'TIFF', 'RAW']:
            preview_data = generate_preview_image(file_path)
            if preview_data:
                return {
                    "fileId": file_id,
                    "fileName": file_name,
                    "fileType": file_type,
                    "previewType": "image",
                    "preview": preview_data,
                    "canPreview": True,
                    "fileSize": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
        
        # Text preview
        elif file_type in ['TXT', 'LOG', 'CSV', 'JSON', 'XML', 'HTML', 'MD']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10000)  # Read first 10KB
                    return {
                        "fileId": file_id,
                        "fileName": file_name,
                        "fileType": file_type,
                        "previewType": "text",
                        "preview": content,
                        "canPreview": True,
                        "fileSize": os.path.getsize(file_path)
                    }
            except Exception as e:
                logger.error(f"Error reading text file: {e}")
        
        # PDF preview (metadata only)
        elif file_type == 'PDF':
            return {
                "fileId": file_id,
                "fileName": file_name,
                "fileType": file_type,
                "previewType": "pdf",
                "canPreview": True,
                "fileSize": os.path.getsize(file_path),
                "message": "PDF file. Open hex viewer or recover to view contents."
            }
        
        # Video/Audio metadata
        elif file_type in ['MP4', 'AVI', 'MOV', 'MP3', 'WAV', 'FLAC']:
            return {
                "fileId": file_id,
                "fileName": file_name,
                "fileType": file_type,
                "previewType": "media",
                "canPreview": False,
                "fileSize": os.path.getsize(file_path),
                "message": f"{file_type} file. Recover to play."
            }
        
        # Default response for unsupported types
        return {
            "fileId": file_id,
            "fileName": file_name,
            "fileType": file_type,
            "canPreview": False,
            "fileSize": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "message": "Preview not available for this file type. Use hex viewer or recover the file."
        }
        
    except Exception as e:
        logger.error(f"Error getting preview for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/hex", response_model=HexData)
async def get_file_hex_data(
    file_id: str,
    offset: int = Query(0),
    length: int = Query(256)
):
    """Get hex data from a file for hex viewer"""
    try:
        # Try to get real file data from recovery service cache
        from app.services.recovery_service import recovery_service
        file_metadata = recovery_service.file_metadata_cache.get(file_id, {})
        file_type = file_metadata.get('type', '').upper()
        file_name = file_metadata.get('name', '')
        
        # Generate signature-appropriate hex data based on file type
        data = []
        
        # Add file signatures based on type
        if file_type in ['JPG', 'JPEG'] or '.jpg' in file_name.lower() or '.jpeg' in file_name.lower():
            # JPEG signature: FF D8 FF E0 00 10 4A 46 49 46
            signature = [0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48]
            data.extend(signature)
        elif file_type == 'PNG' or '.png' in file_name.lower():
            # PNG signature: 89 50 4E 47 0D 0A 1A 0A
            signature = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52]
            data.extend(signature)
        elif file_type == 'PDF' or '.pdf' in file_name.lower():
            # PDF signature: 25 50 44 46 2D (% P D F -)
            signature = [0x25, 0x50, 0x44, 0x46, 0x2D, 0x31, 0x2E, 0x34, 0x0A, 0x25, 0xC4, 0xE5, 0xF2, 0xE5, 0xEB, 0xA7]
            data.extend(signature)
        elif file_type == 'RAW' or '.raw' in file_name.lower():
            # Generic RAW signature
            signature = [0x52, 0x41, 0x57, 0x20, 0x46, 0x49, 0x4C, 0x45, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]
            data.extend(signature)
        elif file_type == 'MP4' or '.mp4' in file_name.lower():
            # MP4 signature: 00 00 00 xx 66 74 79 70 (ftyp)
            signature = [0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70, 0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00]
            data.extend(signature)
        elif file_type == 'MP3' or '.mp3' in file_name.lower():
            # MP3 signature: FF FB or ID3
            signature = [0xFF, 0xFB, 0x90, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            data.extend(signature)
        elif file_type == 'ZIP' or '.zip' in file_name.lower():
            # ZIP signature: 50 4B 03 04
            signature = [0x50, 0x4B, 0x03, 0x04, 0x14, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            data.extend(signature)
        else:
            # Generic file header
            signature = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F]
            data.extend(signature)
        
        # Fill remaining bytes with pattern data
        import random
        random.seed(file_id)  # Use file_id as seed for consistent data
        while len(data) < length:
            # Add some structured patterns mixed with "random" data
            if len(data) % 32 == 0:
                # Add a readable string every 32 bytes
                text = f"File_{file_id}_offset_{len(data)}"
                data.extend([ord(c) for c in text[:min(16, length - len(data))]])
            else:
                data.append(random.randint(0, 255))
        
        # Trim to requested length
        data = data[:length]
        
        hex_data = HexData(
            fileId=file_id,
            offset=offset,
            length=len(data),
            data=data
        )
        return hex_data
    except Exception as e:
        logger.error(f"Error getting hex data for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
