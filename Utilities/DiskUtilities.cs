using System;
using System.Collections.Generic;
using System.Management;

namespace ReStoreX.Utilities
{
    public class DiskInfo
    {
        public string DeviceId { get; set; } = string.Empty;
        public string Model { get; set; } = string.Empty;
        public string Interface { get; set; } = string.Empty;
        public ulong Size { get; set; }
    }

    public static class DiskUtilities
    {
        public static List<DiskInfo> GetAvailableDisks()
        {
            var disks = new List<DiskInfo>();
            
            using (var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_DiskDrive"))
            {
                foreach (ManagementObject disk in searcher.Get())
                {
                    var diskInfo = new DiskInfo
                    {
                        DeviceId = disk["DeviceID"]?.ToString() ?? string.Empty,
                        Model = disk["Model"]?.ToString() ?? string.Empty,
                        Interface = disk["InterfaceType"]?.ToString() ?? string.Empty,
                        Size = disk["Size"] != null ? Convert.ToUInt64(disk["Size"]) : 0
                    };
                    
                    disks.Add(diskInfo);
                }
            }
            
            return disks;
        }
    }
}
