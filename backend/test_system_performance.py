"""
Test script for system performance endpoint
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.system_service import SystemService


async def test_system_performance():
    """Test the system service"""
    service = SystemService()
    
    print("Testing System Performance Service...")
    print("-" * 50)
    
    # Get performance metrics
    metrics = service.get_performance_metrics()
    
    print("\n✓ CPU Information:")
    print(f"  - Usage: {metrics['cpu']['percent']}%")
    print(f"  - Cores: {metrics['cpu']['count']}")
    if metrics['cpu']['frequency']:
        print(f"  - Frequency: {metrics['cpu']['frequency']} MHz")
    
    print("\n✓ Memory Information:")
    print(f"  - Usage: {metrics['memory']['percent']}%")
    print(f"  - Used: {metrics['memory']['used_gb']} GB")
    print(f"  - Total: {metrics['memory']['total_gb']} GB")
    print(f"  - Available: {metrics['memory']['available_gb']} GB")
    
    print("\n✓ Disk Information:")
    print(f"  - Usage: {metrics['disk']['percent']}%")
    print(f"  - Used: {metrics['disk']['used_gb']} GB")
    print(f"  - Total: {metrics['disk']['total_gb']} GB")
    
    print("\n✓ Temperature:")
    if metrics['temperature']:
        print(f"  - Value: {metrics['temperature']['value']}°{metrics['temperature']['unit']}")
        print(f"  - Sensor: {metrics['temperature']['sensor']}")
    else:
        print("  - Not available on this system")
    
    print("\n✓ Other Information:")
    print(f"  - Platform: {metrics['platform']}")
    print(f"  - Processes: {metrics['processes']}")
    
    print("\n" + "-" * 50)
    print("✅ System performance test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_system_performance())
