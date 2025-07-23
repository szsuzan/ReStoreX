using System;

namespace ReStoreX.DiskTypes
{
    public enum DiskType
    {
        Physical,
        Logical,
        Image
    }

    public class DiskInfo
    {
        public required string Path { get; set; }
        public required DiskType Type { get; set; }
        public required string Name { get; set; }
        public required long Size { get; set; }
        public string? FileSystem { get; set; }
        public string? Label { get; set; }
        public bool IsRemovable { get; set; }
    }
}
