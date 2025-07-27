using System;

namespace ReStoreX.NTFS.Attributes
{
    public class StandardInformation : FileRecordAttribute
    {
        public override AttributeType Type => AttributeType.StandardInformation;
        public DateTime CreationTime { get; set; }
        public DateTime LastWriteTime { get; set; }
        public DateTime LastAccessTime { get; set; }
        public long FileSize { get; set; }
    }
}
