from pySMART import Device
import sys

print('Testing pySMART SMART data reading...')
print('=' * 50)

try:
    # Try first physical drive
    device = Device('/dev/pd0')
    
    if device:
        print(f'✅ Device found!')
        print(f'   Model: {device.model or "Unknown"}')
        print(f'   Serial: {device.serial or "Unknown"}')
        print(f'   Interface: {device.interface or "Unknown"}')
        print(f'   Assessment: {device.assessment or "Unknown"}')
        print(f'   Temperature: {device.temperature or "N/A"}°C')
        print(f'   Capacity: {device.capacity or "Unknown"}')
        
        if device.attributes:
            print(f'\n   SMART Attributes found: {len(device.attributes)}')
            print('   Sample attributes:')
            for attr in device.attributes[:5]:  # First 5 attributes
                if attr:
                    print(f'      - {attr.name}: {attr.raw}')
        else:
            print('   ⚠️ No SMART attributes available')
    else:
        print('❌ Device not found or SMART not accessible')
        print('   This is normal for:')
        print('   • USB drives')
        print('   • Virtual machines')
        print('   • Some controllers')
        
except Exception as e:
    print(f'❌ Error: {e}')
    print('\nThis is normal if:')
    print('• smartctl is not installed')
    print('• Drive does not support SMART')
    print('• Running without administrator rights')
    print('\nTry installing smartmontools from: https://www.smartmontools.org/')
