"""
Test script for drive health and details endpoints
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.drive_service import drive_service


async def test_drive_endpoints():
    """Test the drive health and details endpoints"""
    print("Testing Drive Health and Details Endpoints...")
    print("=" * 60)
    
    # Get all drives
    print("\n📀 Fetching all drives...")
    drives = await drive_service.get_all_drives()
    
    if not drives:
        print("❌ No drives found!")
        return
    
    print(f"✅ Found {len(drives)} drive(s)")
    
    # Test each drive
    for i, drive in enumerate(drives, 1):
        print(f"\n{'=' * 60}")
        print(f"Drive {i}: {drive.name}")
        print(f"{'=' * 60}")
        print(f"ID: {drive.id}")
        print(f"Size: {drive.size}")
        print(f"File System: {drive.fileSystem}")
        print(f"Status: {drive.status}")
        
        # Test health endpoint
        print(f"\n🏥 Testing Health Check...")
        health = await drive_service.get_drive_health(drive.id)
        
        if health:
            print(f"  ✅ Health Score: {health['health_score']}/100")
            print(f"  ✅ Health Status: {health['health_status']}")
            print(f"  ✅ Disk Usage: {health['disk_usage']['percent']}%")
            print(f"  ✅ Issues: {len(health['issues'])}")
            for issue in health['issues']:
                print(f"     - {issue}")
            print(f"  ✅ Recommendations: {len(health['recommendations'])}")
            for rec in health['recommendations'][:2]:  # Show first 2
                print(f"     - {rec}")
        else:
            print("  ❌ Health check failed")
        
        # Test details endpoint
        print(f"\n📋 Testing Details...")
        details = await drive_service.get_drive_details(drive.id)
        
        if details:
            print(f"  ✅ Device: {details['basic_info']['device']}")
            print(f"  ✅ Mount Point: {details['basic_info']['mountpoint']}")
            print(f"  ✅ Total Capacity: {details['capacity']['total']}")
            print(f"  ✅ Free Space: {details['capacity']['free']}")
            print(f"  ✅ Max File Size: {details['partition_info']['max_file_size']}")
            print(f"  ✅ Scannable: {details['recovery_info']['scannable']}")
            print(f"  ✅ Recommended Scan: {details['recovery_info']['recommended_scan_type']}")
            print(f"  ✅ Estimated Time: {details['recovery_info']['estimated_scan_time']}")
        else:
            print("  ❌ Details fetch failed")
        
        # Only test first drive to keep output manageable
        if i == 1:
            break
    
    print(f"\n{'=' * 60}")
    print("✅ All tests completed successfully!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(test_drive_endpoints())
