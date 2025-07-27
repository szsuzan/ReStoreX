using System;
using System.Collections.Generic;
using System.IO;

namespace ReStoreX.Core
{
    public interface IDisk
    {
        string DeviceId { get; }
        long Length { get; }
        byte[] ReadSector(long offset, int size);
        void WriteSector(long offset, byte[] data);
    }

    public interface IReStoreXFileSystem
    {
        string Name { get; }
        long TotalSpace { get; }
        long FreeSpace { get; }
        int ClusterSize { get; }
        bool IsReady { get; }

        IEnumerable<DirectoryEntry> GetDirectories(string path);
        IEnumerable<FileEntry> GetFiles(string path);
        IEnumerable<DeletedFileEntry> ScanForDeletedFiles();
        IEnumerable<ClusterInfo> GetClusterMap();
        
        bool RecoverFile(FileEntry file, string destinationPath);
        byte[] ReadFileData(FileEntry file);
    }

    public class DirectoryEntry
    {
        public string DirectoryName { get; set; } = "";
        public string FullPath { get; set; } = "";
        public List<FileEntry> Files { get; set; } = new();
        public List<DirectoryEntry> SubDirectories { get; set; } = new();
        public DateTime CreationTime { get; set; }
        public DateTime LastAccessTime { get; set; }
        public DateTime LastWriteTime { get; set; }
    }

    public class FileEntry
    {
        public string FileName { get; set; } = "";
        public string FullPath { get; set; } = "";
        public long Size { get; set; }
        public DateTime CreationTime { get; set; }
        public DateTime LastAccessTime { get; set; }
        public DateTime LastWriteTime { get; set; }
        public bool IsDeleted { get; set; }
    }

    public class DeletedFileEntry : FileEntry
    {
        public int RecoveryChance { get; set; }
        public string FileSignature { get; set; } = "";
    }

    public class ClusterInfo
    {
        public long ClusterId { get; set; }
        public ClusterStatus Status { get; set; }
        public string? FileName { get; set; }
        public long Size { get; set; }
    }

    public enum ClusterStatus
    {
        Free,
        Used,
        Bad,
        Reserved
    }
}
