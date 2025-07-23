using System;

namespace ReStoreX.Controls
{
    /// <summary>
    /// Simplified Volume class placeholder for ReStoreX.
    /// </summary>
    public class Volume
    {
        public bool Mounted { get; set; } = false;
        public long Offset { get; set; } = 0;
        public long Length { get; set; } = 0;

        // Example usage: these values are placeholders for now.
        public long GetUsedSpace() => Length / 2;   // Dummy: 50% used
        public long GetFreeSpace() => Length - GetUsedSpace();
        public long GetTotalSpace() => Length;
    }
}
