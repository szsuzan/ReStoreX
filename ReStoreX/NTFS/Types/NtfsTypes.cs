using System;
using System.Collections.Generic;
using System.IO;

namespace ReStoreX.NTFS
{
    public interface INtfsFileRecord
    {
        long RecordNumber { get; }
        T GetAttribute<T>() where T : NtfsAttribute;
        void AddAttribute(NtfsAttribute attribute);
    }

    public abstract class NtfsAttribute
    {
        public abstract AttributeType Type { get; }
        public bool IsResident { get; protected set; }
        public bool IsCompressed { get; protected set; }
        public bool IsEncrypted { get; protected set; }
    }

    public enum AttributeType
    {
        StandardInformation = 0x10,
        FileName = 0x30,
        Data = 0x80
    }

    public class StandardInformation : NtfsAttribute
    {
        public override AttributeType Type => AttributeType.StandardInformation;
        public DateTime CreationTime { get; set; }
        public DateTime LastWriteTime { get; set; }
        public DateTime LastAccessTime { get; set; }
        public long FileSize { get; set; }
    }

    public class FileNameAttribute : NtfsAttribute
    {
        public override AttributeType Type => AttributeType.FileName;
        public string FileName { get; set; }
    }

    public class DataAttribute : NtfsAttribute
    {
        public override AttributeType Type => AttributeType.Data;
        public List<DataRun> DataRuns { get; } = new List<DataRun>();

        public class DataRun
        {
            public long StartCluster { get; set; }
            public long Length { get; set; }
        }
    }

    public class NtfsFileRecord : INtfsFileRecord
    {
        private Dictionary<Type, NtfsAttribute> _attributes = new Dictionary<Type, NtfsAttribute>();

        public long RecordNumber { get; }

        public NtfsFileRecord(long recordNumber)
        {
            RecordNumber = recordNumber;
        }

        public T GetAttribute<T>() where T : NtfsAttribute
        {
            if (_attributes.TryGetValue(typeof(T), out var attribute))
            {
                return (T)attribute;
            }
            return null;
        }

        public void AddAttribute(NtfsAttribute attribute)
        {
            _attributes[attribute.GetType()] = attribute;
        }
    }
}
