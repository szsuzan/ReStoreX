using System;
using System.IO;

namespace DiscUtils.Ntfs
{
    public static class NtfsFileSystemExtensions
    {
        public static Stream OpenCluster(this NtfsFileSystem ntfs, long clusterNumber)
        {
            long offset = clusterNumber * ntfs.ClusterSize;
            var stream = new MemoryStream();
            
            // Get the underlying disk stream
            var diskStream = typeof(NtfsFileSystem)
                .GetProperty("DiskStream", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
                ?.GetValue(ntfs) as Stream;

            if (diskStream == null)
                throw new InvalidOperationException("Could not access disk stream");

            var buffer = new byte[ntfs.ClusterSize];
            diskStream.Position = offset;
            diskStream.Read(buffer, 0, (int)Math.Min(ntfs.ClusterSize, int.MaxValue));
            stream.Write(buffer, 0, buffer.Length);
            stream.Position = 0;
            
            return stream;
        }
    }
}
