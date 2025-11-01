import sys
sys.path.insert(0, '.')
from app.services.python_recovery_service import PythonRecoveryService
import asyncio
import tempfile
import platform

async def test_health_scan():
    temp_dir = tempfile.mkdtemp()
    service = PythonRecoveryService(temp_dir)
    
    # Test progress callback
    async def progress_cb(data):
        print(f"Progress: {data['progress']:.1f}% - Sectors: {data['sectors_scanned']}/{data['total_sectors']}")
    
    print('\n' + '='*60)
    print('Testing Health Scan')
    print('='*60)
    
    # Test removable drive (E:)
    print('\n--- Testing Drive E: (Removable) ---')
    options = {}
    result = await service._health_scan('E:\\', temp_dir, options, progress_cb)
    
    if 'error' in result:
        print(f"\nError: {result['error']}")
    else:
        print(f"\nDrive: {result.get('drive_path', 'N/A')}")
        print(f"Health Score: {result.get('health_score', 0)}/100")
        print(f"Status: {result.get('status', 'N/A')}")
        print(f"Bad Sectors: {result.get('bad_sectors', 0)}")
        print(f"Sectors Tested: {result.get('total_sectors_tested', 0)}")
        print(f"SMART Data: {'Available' if result.get('smart_data') else 'Skipped (Removable Drive)'}")
        
        if result.get('recommendations'):
            print(f"\nRecommendations:")
            for rec in result['recommendations']:
                print(f"  {rec}")
    
    print('\n' + '='*60)

if __name__ == '__main__':
    asyncio.run(test_health_scan())
