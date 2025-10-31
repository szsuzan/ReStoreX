"""
Quick test script to verify backend functionality
Run this after setting up the backend to ensure everything works
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.drive_service import drive_service
from app.services.testdisk_service import testdisk_service


async def test_testdisk():
    """Test TestDisk availability"""
    print("=" * 50)
    print("Testing TestDisk Installation")
    print("=" * 50)
    
    testdisk_ok = await testdisk_service.check_testdisk()
    photorec_ok = await testdisk_service.check_photorec()
    
    print(f"TestDisk: {'✓ Found' if testdisk_ok else '✗ Not Found'}")
    print(f"PhotoRec: {'✓ Found' if photorec_ok else '✗ Not Found'}")
    
    if not testdisk_ok or not photorec_ok:
        print("\n⚠ Warning: TestDisk/PhotoRec not found")
        print("Please install from: https://www.cgsecurity.org/")
    
    return testdisk_ok and photorec_ok


async def test_drive_detection():
    """Test drive detection"""
    print("\n" + "=" * 50)
    print("Testing Drive Detection")
    print("=" * 50)
    
    drives = await drive_service.get_all_drives()
    
    if drives:
        print(f"✓ Found {len(drives)} drive(s):\n")
        for drive in drives:
            print(f"  - {drive.name}")
            print(f"    ID: {drive.id}")
            print(f"    Size: {drive.size}")
            print(f"    File System: {drive.fileSystem}")
            print(f"    Status: {drive.status}")
            print()
    else:
        print("✗ No drives detected")
    
    return len(drives) > 0


async def test_api_imports():
    """Test if all imports work"""
    print("\n" + "=" * 50)
    print("Testing Module Imports")
    print("=" * 50)
    
    try:
        from app.routes import drives, scan, recovery, files, explorer
        from app.services import scan_service, recovery_service
        from app.models import DriveInfo, ScanRequest, RecoveryRequest
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║" + " " * 12 + "ReStoreX Backend Tests" + " " * 14 + "║")
    print("╚" + "=" * 48 + "╝")
    print()
    
    results = []
    
    # Test imports
    results.append(await test_api_imports())
    
    # Test TestDisk
    results.append(await test_testdisk())
    
    # Test drive detection
    results.append(await test_drive_detection())
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! Backend is ready to use.")
        print("\nNext steps:")
        print("1. Run: python main.py")
        print("2. Access API docs at: http://localhost:3001/docs")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("- Install TestDisk from https://www.cgsecurity.org/")
        print("- Ensure Python dependencies are installed: pip install -r requirements.txt")
        print("- Run with administrator privileges if drive detection fails")
    
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\nError running tests: {e}")
        import traceback
        traceback.print_exc()
