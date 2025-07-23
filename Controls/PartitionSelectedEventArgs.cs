using System;

namespace ReStoreX.Controls
{
    public class PartitionSelectedEventArgs : EventArgs
    {
        public Volume? volume { get; set; }

        public PartitionSelectedEventArgs(Volume? vol)
        {
            volume = vol;
        }
    }
}
