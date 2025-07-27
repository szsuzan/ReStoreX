using System;
using System.Collections.Generic;

namespace ReStoreX.NTFS
{
    public class StandardInformation : NtfsAttribute
    {
        public DateTime CreationTime { get; set; }
        public DateTime LastWriteTime { get; set; }
        public DateTime LastAccessTime { get; set; }
        public long FileSize { get; set; }

        public StandardInformation()
        {
            Type = AttributeType.StandardInformation;
            IsResident = true;
        }
    }

    public class FileNameAttribute : NtfsAttribute
    {
        public string FileName { get; set; }

        public FileNameAttribute()
        {
            Type = AttributeType.FileName;
            IsResident = true;
        }
    }

    public class DataAttribute : NtfsAttribute
    {
        public List<DataRun> DataRuns { get; } = new();

        public DataAttribute()
        {
            Type = AttributeType.Data;
        }

        public class DataRun
        {
            public long StartCluster { get; set; }
            public long Length { get; set; }
        }
    }
}
