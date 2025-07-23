using ReStoreX.Core;
using System;
using System.Collections.Generic;
using System.IO;

namespace ReStoreX.Database
{
    public class DriveDatabase
    {
        public List<IReStoreXFileSystem> FileSystems { get; private set; } = new List<IReStoreXFileSystem>();

        public void AddFileSystem(IReStoreXFileSystem fs)
        {
            if (fs != null)
                FileSystems.Add(fs);
        }

        public void Clear()
        {
            FileSystems.Clear();
        }
    }

    public class PartitionDatabase
    {
        public string PartitionName { get; set; }
        public string FileSystemType { get; set; }
        public long Offset { get; set; }
        public long Length { get; set; }

        public PartitionDatabase(string name, string fsType, long offset, long length)
        {
            PartitionName = name;
            FileSystemType = fsType;
            Offset = offset;
            Length = length;
        }
    }

    public class FileDatabase
    {
        public string FileName { get; set; }
        public long FileSize { get; set; }
        public DateTime Created { get; set; }
        public DateTime Modified { get; set; }
        public DateTime Accessed { get; set; }

        public FileDatabase(FileEntry file)
        {
            FileName = file.FileName;
            FileSize = file.FileSize;
            Created = file.CreationTime;
            Modified = file.LastWriteTime;
            Accessed = file.LastAccessTime;
        }
    }
}
