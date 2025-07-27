using Microsoft.Win32.SafeHandles;
using System;
using System.IO;
using System.Runtime.InteropServices;

namespace ReStoreX.Utilities
{
    [StructLayout(LayoutKind.Sequential)]
    public struct DISK_GEOMETRY
    {
        public long Cylinders;
        public int MediaType;
        public int TracksPerCylinder;
        public int SectorsPerTrack;
        public int BytesPerSector;
    }
    public static class WinApi
    {
        [DllImport("kernel32.dll", SetLastError = true)]
        public static extern SafeFileHandle CreateFile(
            string lpFileName,
            FileAccess dwDesiredAccess,
            FileShare dwShareMode,
            IntPtr lpSecurityAttributes,
            FileMode dwCreationDisposition,
            int dwFlagsAndAttributes,
            IntPtr hTemplateFile);

        [DllImport("kernel32.dll", SetLastError = true)]
        public static extern bool DeviceIoControl(
            SafeFileHandle hDevice,
            uint dwIoControlCode,
            IntPtr lpInBuffer,
            int nInBufferSize,
            IntPtr lpOutBuffer,
            int nOutBufferSize,
            out int lpBytesReturned,
            IntPtr lpOverlapped);

        /// <summary>
        /// Get list of available physical drives.
        /// </summary>
        public static List<string> GetAvailablePhysicalDrives()
        {
            var drives = new List<string>();
            for (int i = 0; i < 32; i++) // Reasonable max number of drives
            {
                string path = $"\\\\.\\PhysicalDrive{i}";
                using var handle = CreateFile(path, FileAccess.Read, FileShare.ReadWrite, IntPtr.Zero, FileMode.Open, 0, IntPtr.Zero);
                if (!handle.IsInvalid)
                {
                    drives.Add(path);
                }
            }
            return drives;
        }

        /// <summary>
        /// Get the capacity of a disk device.
        /// </summary>
        public static long GetDiskCapacity(SafeFileHandle handle)
        {
            uint IOCTL_DISK_GET_DRIVE_GEOMETRY = 0x70000;
            var geometry = new DISK_GEOMETRY();
            int bytesReturned;

            var geometryPtr = Marshal.AllocHGlobal(Marshal.SizeOf(geometry));
            try
            {
                if (DeviceIoControl(handle, IOCTL_DISK_GET_DRIVE_GEOMETRY, IntPtr.Zero, 0, geometryPtr, Marshal.SizeOf(geometry), out bytesReturned, IntPtr.Zero))
                {
                    geometry = (DISK_GEOMETRY)Marshal.PtrToStructure(geometryPtr, typeof(DISK_GEOMETRY))!;
                    return (long)geometry.Cylinders * geometry.TracksPerCylinder * geometry.SectorsPerTrack * geometry.BytesPerSector;
                }
            }
            finally
            {
                Marshal.FreeHGlobal(geometryPtr);
            }
            return 0;
        }

        /// <summary>
        /// Get the sector size of a disk device.
        /// </summary>
        public static int GetSectorSize(SafeFileHandle handle)
        {
            uint IOCTL_DISK_GET_DRIVE_GEOMETRY = 0x70000;
            var geometry = new DISK_GEOMETRY();
            int bytesReturned;

            var geometryPtr = Marshal.AllocHGlobal(Marshal.SizeOf(geometry));
            try
            {
                if (DeviceIoControl(handle, IOCTL_DISK_GET_DRIVE_GEOMETRY, IntPtr.Zero, 0, geometryPtr, Marshal.SizeOf(geometry), out bytesReturned, IntPtr.Zero))
                {
                    geometry = (DISK_GEOMETRY)Marshal.PtrToStructure(geometryPtr, typeof(DISK_GEOMETRY))!;
                    return geometry.BytesPerSector;
                }
            }
            finally
            {
                Marshal.FreeHGlobal(geometryPtr);
            }
            return 512; // Default sector size
        }

        /// <summary>
        /// Creates a handle to a physical drive.
        /// </summary>
        public static SafeFileHandle OpenPhysicalDrive(string drivePath)
        {
            return CreateFile(
                drivePath,
                FileAccess.Read,
                FileShare.ReadWrite,
                IntPtr.Zero,
                FileMode.Open,
                0,
                IntPtr.Zero);
        }


    }
}
