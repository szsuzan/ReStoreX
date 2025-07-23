using Microsoft.Win32.SafeHandles;
using System;
using System.IO;
using System.Runtime.InteropServices;

namespace ReStoreX.Utilities
{
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

        /// <summary>
        /// Get sector size from disk geometry.
        /// </summary>
        public static long GetSectorSize(SafeFileHandle handle)
        {
            // Default sector size if we can't get it
            return 512;
        }

        /// <summary>
        /// Get disk capacity (stub for now).
        /// </summary>
        public static long GetDiskCapactity(SafeFileHandle handle)
        {
            // Implement IOCTL if needed; returning 0 as placeholder
            return 0;
        }
    }
}
