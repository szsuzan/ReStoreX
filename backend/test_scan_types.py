"""
Test script for enhanced scan types:
- Cluster Scan
- Health Scan
- Signature Scan
- Forensic Scan
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.scan_service import scan_service
from app.services.drive_service import drive_service


async def test_scan_type(scan_type: str, drive_id: str):
    """Test a specific scan type"""
    print(f"\n{'=' * 70}")
    print(f"Testing {scan_type.upper()} SCAN")
    print(f"{'=' * 70}")
    
    try:
        # Start scan
        scan_id = await scan_service.start_scan(drive_id, scan_type, {})
        print(f"✅ Scan started with ID: {scan_id}")
        
        # Monitor progress
        print("\n📊 Progress:")
        last_progress = 0
        while True:
            status = await scan_service.get_scan_status(scan_id)
            if not status:
                break
            
            if status["progress"] != last_progress:
                print(f"  {status['progress']:.1f}% - Found {status['filesFound']} files - ETA: {status['estimatedTimeRemaining']}")
                last_progress = status["progress"]
            
            if status["status"] != "running":
                print(f"\n✅ Scan completed with status: {status['status']}")
                break
            
            await asyncio.sleep(0.5)
        
        # Get results
        results = await scan_service.get_scan_results(scan_id)
        print(f"📁 Total files found: {len(results)}")
        
        if len(results) > 0:
            print(f"\n📋 Sample results (first 5):")
            for i, file in enumerate(results[:5], 1):
                print(f"  {i}. {file.name} ({file.size}) - Recovery: {file.recoveryChance}")
        
        # Check for scan-specific data
        scan_info = scan_service.active_scans.get(scan_id)
        if scan_info:
            if "cluster_analysis" in scan_info:
                ca = scan_info["cluster_analysis"]
                print(f"\n🔍 Cluster Analysis:")
                print(f"  - Total Clusters: {ca['total_clusters']:,}")
                print(f"  - Used Clusters: {ca['used_clusters']:,}")
                print(f"  - Free Clusters: {ca['free_clusters']:,}")
                print(f"  - Fragmented Files: {ca['fragmented_files']:,}")
                print(f"  - Orphaned Clusters: {ca['orphaned_clusters']:,}")
            
            if "health_report" in scan_info:
                hr = scan_info["health_report"]
                print(f"\n🏥 Health Report:")
                print(f"  - Drive: {hr['drive_name']}")
                print(f"  - Scan Time: {hr['scan_time']}")
                print(f"  - Checks Performed: {len(hr['checks'])}")
                for check in hr['checks']:
                    status_icon = "✅" if check['status'] == 'pass' else "⚠️" if check['status'] == 'warning' else "❌" if check['status'] == 'fail' else "⏭️"
                    print(f"    {status_icon} {check['name']}: {check['details']}")
            
            if "forensic_data" in scan_info:
                fd = scan_info["forensic_data"]
                print(f"\n🔬 Forensic Data:")
                print(f"  - Files Analyzed: {fd['files_analyzed']}")
                print(f"  - Hashes Calculated: {fd['hashes_calculated']}")
                print(f"  - Evidence Log Entries: {len(fd['evidence_log'])}")
                print(f"  - Chain of Custody Events: {len(fd['chain_of_custody'])}")
                print(f"\n  📜 Evidence Log:")
                for entry in fd['evidence_log'][:3]:  # Show first 3
                    print(f"    - [{entry['timestamp']}] {entry['action']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing {scan_type} scan: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all scan type tests"""
    print("🧪 RESTOREX ENHANCED SCAN TYPES TEST")
    print("=" * 70)
    
    # Get first available drive
    drives = await drive_service.get_all_drives()
    if not drives:
        print("❌ No drives found!")
        return
    
    test_drive = drives[0]
    print(f"\n📀 Using drive: {test_drive.name} (ID: {test_drive.id})")
    print(f"   Size: {test_drive.size}")
    print(f"   File System: {test_drive.fileSystem}")
    print(f"   Status: {test_drive.status}")
    
    # Test each scan type
    scan_types = ["cluster", "health", "signature", "forensic"]
    results = {}
    
    for scan_type in scan_types:
        success = await test_scan_type(scan_type, test_drive.id)
        results[scan_type] = success
        await asyncio.sleep(1)  # Small delay between scans
    
    # Summary
    print(f"\n{'=' * 70}")
    print("📊 TEST SUMMARY")
    print(f"{'=' * 70}")
    
    for scan_type, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {scan_type.capitalize()} Scan")
    
    all_passed = all(results.values())
    print(f"\n{'=' * 70}")
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
