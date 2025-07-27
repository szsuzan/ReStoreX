using System;
using System.Collections.Generic;
using System.Linq;

namespace ReStoreX.NTFS
{
    public class NtfsFileRecord : INtfsFileRecord
    {
        private readonly List<NtfsAttribute> _attributes = new();

        public NtfsFileRecord(long referenceNumber)
        {
            ReferenceNumber = referenceNumber;
        }

        public long ReferenceNumber { get; }

        public IReadOnlyList<NtfsAttribute?> Attributes => _attributes.AsReadOnly();

        public StandardInformation? StandardInformation => 
            _attributes.OfType<StandardInformation>().FirstOrDefault();

        public FileNameAttribute? FileName => 
            _attributes.OfType<FileNameAttribute>().FirstOrDefault();

        public DataAttribute? Data => 
            _attributes.OfType<DataAttribute>().FirstOrDefault();

        public void AddAttribute(NtfsAttribute? attribute)
        {
            if (attribute != null)
                _attributes.Add(attribute);
        }
    }
}
