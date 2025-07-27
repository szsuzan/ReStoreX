namespace ReStoreX.NTFS
{
    public abstract class NtfsAttribute
    {
        public AttributeType Type { get; protected set; }
        public bool IsResident { get; protected set; }
    }

    public enum AttributeType : uint
    {
        StandardInformation = 0x10,
        FileName = 0x30,
        Data = 0x80
    }
}
