using System;

namespace ReStoreX.NTFS.Attributes
{
    public class FileNameAttribute : FileRecordAttribute
    {
        public override AttributeType Type => AttributeType.FileName;
        public string FileName { get; set; }
    }
}
