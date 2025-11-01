import os
from pathlib import Path


class Settings:
    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS settings
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    ).split(",")
    
    # Directories
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./temp")
    RECOVERY_DIR: str = os.getenv("RECOVERY_DIR", "./recovered_files")
    
    # Operational limits
    MAX_CONCURRENT_SCANS: int = int(os.getenv("MAX_CONCURRENT_SCANS", "2"))
    MAX_CONCURRENT_RECOVERIES: int = int(os.getenv("MAX_CONCURRENT_RECOVERIES", "1"))
    
    # API version
    VERSION: str = "1.0.0"
    
    def __init__(self):
        # Ensure directories exist
        os.makedirs(self.TEMP_DIR, exist_ok=True)
        os.makedirs(self.RECOVERY_DIR, exist_ok=True)


settings = Settings()

