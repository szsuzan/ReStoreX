using System;
using System.Collections.Generic;

namespace ReStoreX.NTFS
{
    public interface INtfsFileRecord
    {
        long ReferenceNumber { get; }
        IReadOnlyList<NtfsAttribute?> Attributes { get; }
        StandardInformation? StandardInformation { get; }
        FileNameAttribute? FileName { get; }
        DataAttribute? Data { get; }
    }
}
