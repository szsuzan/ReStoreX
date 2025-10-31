import psutil
import platform
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Try to import Windows-specific libraries for temperature
try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False
    logger.debug("WMI not available - temperature monitoring limited on Windows")


class SystemService:
    """Service for getting system performance metrics"""
    
    def __init__(self):
        self.platform = platform.system()
        self.wmi_connection = None
        
        # Initialize WMI for Windows temperature monitoring
        if self.platform == "Windows" and HAS_WMI:
            try:
                self.wmi_connection = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                logger.info("WMI connection established for temperature monitoring")
            except Exception as e:
                logger.debug(f"OpenHardwareMonitor not available: {e}")
                try:
                    self.wmi_connection = wmi.WMI(namespace="root\\WMI")
                    logger.info("WMI connection established (WMI namespace)")
                except Exception as e2:
                    logger.debug(f"WMI connection failed: {e2}")
                    self.wmi_connection = None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current system performance metrics
        
        Returns:
            Dictionary containing CPU, memory, disk, and temperature data
        """
        try:
            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory Usage
            memory = psutil.virtual_memory()
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            memory_percent = memory.percent
            
            # Disk Usage (for system drive)
            disk = psutil.disk_usage('/')
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            disk_percent = disk.percent
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # Temperature (if available)
            temperature = self._get_temperature()
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                "cpu": {
                    "percent": round(cpu_percent, 1),
                    "count": cpu_count,
                    "frequency": round(cpu_freq.current, 0) if cpu_freq else None
                },
                "memory": {
                    "percent": round(memory_percent, 1),
                    "used_gb": round(memory_used_gb, 2),
                    "total_gb": round(memory_total_gb, 2),
                    "available_gb": round(memory.available / (1024**3), 2)
                },
                "disk": {
                    "percent": round(disk_percent, 1),
                    "used_gb": round(disk_used_gb, 2),
                    "total_gb": round(disk_total_gb, 2),
                    "read_mb": round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
                    "write_mb": round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0
                },
                "network": {
                    "sent_mb": round(net_io.bytes_sent / (1024**2), 2) if net_io else 0,
                    "recv_mb": round(net_io.bytes_recv / (1024**2), 2) if net_io else 0
                },
                "temperature": temperature,
                "processes": process_count,
                "platform": self.platform
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            # Return default values on error
            return {
                "cpu": {"percent": 0, "count": 0, "frequency": None},
                "memory": {"percent": 0, "used_gb": 0, "total_gb": 0, "available_gb": 0},
                "disk": {"percent": 0, "used_gb": 0, "total_gb": 0, "read_mb": 0, "write_mb": 0},
                "network": {"sent_mb": 0, "recv_mb": 0},
                "temperature": None,
                "processes": 0,
                "platform": self.platform
            }
    
    def _get_temperature(self) -> Dict[str, float] | None:
        """
        Get system temperature
        Tries multiple methods depending on the platform
        """
        # Try Linux sensors first (psutil)
        temp = self._get_temperature_psutil()
        if temp:
            return temp
        
        # Try Windows WMI methods
        if self.platform == "Windows":
            temp = self._get_temperature_wmi()
            if temp:
                return temp
        
        # Generate simulated temperature based on CPU usage (fallback)
        return self._get_simulated_temperature()
    
    def _get_temperature_psutil(self) -> Dict[str, float] | None:
        """Get temperature using psutil (works on Linux)"""
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Try to get CPU temperature
                    for name, entries in temps.items():
                        if entries:
                            temp = entries[0].current
                            return {
                                "value": round(temp, 1),
                                "unit": "C",
                                "sensor": name
                            }
            return None
        except Exception as e:
            logger.debug(f"psutil temperature not available: {e}")
            return None
    
    def _get_temperature_wmi(self) -> Dict[str, float] | None:
        """Get temperature using WMI (Windows only)"""
        if not HAS_WMI or not self.wmi_connection:
            return None
        
        try:
            # Try OpenHardwareMonitor namespace
            temperature_infos = self.wmi_connection.Sensor()
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature':
                    return {
                        "value": round(float(sensor.Value), 1),
                        "unit": "C",
                        "sensor": sensor.Name
                    }
        except Exception as e:
            logger.debug(f"WMI temperature reading failed: {e}")
        
        try:
            # Try MSAcpi_ThermalZoneTemperature (standard Windows)
            w = wmi.WMI(namespace="root\\WMI")
            temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
            # Convert from tenths of Kelvin to Celsius
            temp_celsius = (temperature_info.CurrentTemperature / 10.0) - 273.15
            return {
                "value": round(temp_celsius, 1),
                "unit": "C",
                "sensor": "Thermal Zone"
            }
        except Exception as e:
            logger.debug(f"MSAcpi temperature reading failed: {e}")
        
        return None
    
    def _get_simulated_temperature(self) -> Dict[str, float]:
        """
        Generate simulated temperature based on CPU usage
        This provides a visual representation when real sensors aren't available
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            # Simulate temperature: 30°C base + (CPU% * 0.5)
            # This gives a range of roughly 30-80°C
            simulated_temp = 30 + (cpu_percent * 0.5)
            return {
                "value": round(simulated_temp, 1),
                "unit": "C",
                "sensor": "Simulated (CPU-based)"
            }
        except Exception as e:
            logger.debug(f"Simulated temperature failed: {e}")
            return {
                "value": 45.0,
                "unit": "C",
                "sensor": "Default"
            }
