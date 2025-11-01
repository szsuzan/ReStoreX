import sys
sys.path.insert(0, '.')
from app.services.python_recovery_service import PythonRecoveryService
import asyncio
import tempfile
import json

async def test_smart():
    temp_dir = tempfile.mkdtemp()
    service = PythonRecoveryService(temp_dir)
    result = await service._read_smart_data_wmi('C:\\')  # Test with C: drive (NVMe)
    
    print('\n' + '='*60)
    print('SMART Data Test Result - Drive C:')
    print('='*60)
    
    print(f'\nMethod: {result.get("method", "Unknown")}')
    print(f'Total attributes: {len(result)}')
    
    # Key health indicators
    print('\n--- Key Health Indicators ---')
    key_attrs = ['Health_Status', 'Temperature_Celsius', 'Power_On_Hours', 
                 'Data_Units_Read', 'Data_Units_Written', 'Media_Errors', 
                 'Available_Spare', 'Percentage_Used', 'Power_Cycles', 
                 'Unsafe_Shutdowns', 'Critical_Warning']
    
    for key in key_attrs:
        if key in result:
            value = result[key]
            if isinstance(value, dict):
                print(f'  {key}: {value.get("value", value)}')
            else:
                print(f'  {key}: {value}')
    
    print('\n--- All Attributes ---')
    for key, value in sorted(result.items()):
        if key not in ['method']:
            if isinstance(value, dict):
                print(f'  {key}: {value.get("value", value)}')
            else:
                print(f'  {key}: {value}')
    
    print('\n' + '='*60)

if __name__ == '__main__':
    asyncio.run(test_smart())
