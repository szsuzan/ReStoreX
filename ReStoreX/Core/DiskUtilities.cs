using System;
using System.Collections.Generic;
using System.Management;
using System.Runtime.InteropServices;

namespace ReStoreX.Core
{
    public static class DiskUtilities
    {
        public static List<DiskInfo> GetAvailableDisks()
        {
            var disks = new List<DiskInfo>();

            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_DiskDrive");
                foreach (ManagementObject disk in searcher.Get())
                {
                    disks.Add(new DiskInfo
                    {
                        DeviceId = disk["DeviceID"].ToString()!,
                        Model = disk["Model"].ToString()!,
                        Size = Convert.ToInt64(disk["Size"]),
                        SerialNumber = disk["SerialNumber"]?.ToString() ?? "Unknown",
                        InterfaceType = disk["InterfaceType"].ToString()!,
                        Partitions = GetPartitionsForDisk(disk["DeviceID"].ToString()!)
                    });
                }
            }
            else
            {
                // Unix-like systems
                // Implement using /dev/sd* or similar
            }

            return disks;
        }

        public static List<SmartAttribute> GetSmartAttributes(string deviceId)
        {
            var attributes = new List<SmartAttribute>();

            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                using var searcher = new ManagementObjectSearcher(
                    $"SELECT * FROM MSStorageDriver_ATAPISmartData WHERE InstanceName LIKE '%{deviceId}%'");

                foreach (ManagementObject data in searcher.Get())
                {
                    var vendorSpecific = (byte[])data["VendorSpecific"];
                    for (int i = 0; i < vendorSpecific.Length; i += 12)
                    {
                        if (vendorSpecific[i + 0] == 0) continue;

                        attributes.Add(new SmartAttribute
                        {
                            Id = vendorSpecific[i + 0],
                            Current = vendorSpecific[i + 3],
                            Worst = vendorSpecific[i + 4],
                            Threshold = vendorSpecific[i + 5],
                            Raw = BitConverter.ToInt64(vendorSpecific, i + 6)
                        });
                    }
                }
            }

            return attributes;
        }

        private static List<PartitionInfo> GetPartitionsForDisk(string deviceId)
        {
            var partitions = new List<PartitionInfo>();

            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                using var searcher = new ManagementObjectSearcher(
                    $"ASSOCIATORS OF {{Win32_DiskDrive.DeviceID='{deviceId}'}} WHERE AssocClass = Win32_DiskDriveToDiskPartition");

                foreach (ManagementObject partition in searcher.Get())
                {
                    using var logicalDiskSearcher = new ManagementObjectSearcher(
                        $"ASSOCIATORS OF {{Win32_DiskPartition.DeviceID='{partition["DeviceID"]}'}} WHERE AssocClass = Win32_LogicalDiskToPartition");

                    foreach (ManagementObject logicalDisk in logicalDiskSearcher.Get())
                    {
                        partitions.Add(new PartitionInfo
                        {
                            DeviceId = partition["DeviceID"].ToString()!,
                            DriveLetter = logicalDisk["Name"].ToString()!,
                            Size = Convert.ToInt64(partition["Size"]),
                            Type = partition["Type"].ToString()!,
                            BootPartition = Convert.ToBoolean(partition["BootPartition"])
                        });
                    }
                }
            }

            return partitions;
        }

        public static bool LockVolume(string driveLetter)
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                // Implementation for Windows using DeviceIOControl
                return true;
            }
            return false;
        }

        public static bool UnlockVolume(string driveLetter)
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                // Implementation for Windows using DeviceIOControl
                return true;
            }
            return false;
        }
    }

    public class DiskInfo
    {
        public required string DeviceId { get; set; }
        public required string Model { get; set; }
        public long Size { get; set; }
        public string SerialNumber { get; set; } = "Unknown";
        public required string InterfaceType { get; set; }
        public List<PartitionInfo> Partitions { get; set; } = new();
    }

    public class PartitionInfo
    {
        public required string DeviceId { get; set; }
        public required string DriveLetter { get; set; }
        public long Size { get; set; }
        public required string Type { get; set; }
        public bool BootPartition { get; set; }
    }

    public class SmartAttribute
    {
        public byte Id { get; set; }
        public byte Current { get; set; }
        public byte Worst { get; set; }
        public byte Threshold { get; set; }
        public long Raw { get; set; }

        public string GetAttributeName() => Id switch
        {
            1 => "Read Error Rate",
            5 => "Reallocated Sectors Count",
            9 => "Power-On Hours",
            10 => "Spin Retry Count",
            12 => "Power Cycle Count",
            194 => "Temperature",
            196 => "Reallocation Event Count",
            197 => "Current Pending Sector Count",
            198 => "Offline Uncorrectable Sector Count",
            _ => $"Unknown ({Id})"
        };

        public bool IsOk => Current > Threshold;
    }
}
