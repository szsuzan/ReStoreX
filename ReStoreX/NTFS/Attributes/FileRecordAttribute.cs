using System;

namespace ReStoreX.NTFS.Attributes
{
    public abstract class FileRecordAttribute
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
}
