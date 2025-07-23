using System;
using System.IO;
using System.Text;

namespace ReStoreX.Utilities
{
    public static class Utility
    {
        /// <summary>
        /// Convert a file size to a human-readable string.
        /// </summary>
        public static string FormatFileSize(long bytes)
        {
            string[] sizes = { "B", "KB", "MB", "GB", "TB" };
            double len = bytes;
            int order = 0;
            while (len >= 1024 && order < sizes.Length - 1)
            {
                order++;
                len /= 1024;
            }
            return $"{len:0.##} {sizes[order]}";
        }

        /// <summary>
        /// Reads a block of bytes from a stream.
        /// </summary>
        public static byte[] ReadBytes(Stream stream, long offset, int count)
        {
            stream.Seek(offset, SeekOrigin.Begin);
            byte[] buffer = new byte[count];
            stream.Read(buffer, 0, count);
            return buffer;
        }

        /// <summary>
        /// Convert a byte array to a hex string.
        /// </summary>
        public static string ToHexString(byte[] bytes)
        {
            StringBuilder sb = new StringBuilder(bytes.Length * 2);
            foreach (byte b in bytes)
                sb.AppendFormat("{0:X2}", b);
            return sb.ToString();
        }
    }
}
