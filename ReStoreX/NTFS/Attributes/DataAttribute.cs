using System;
using System.Collections.Generic;

namespace ReStoreX.NTFS.Attributes
{
    public class DataAttribute : FileRecordAttribute
    {
        public override AttributeType Type => AttributeType.Data;
        public List<DataRun> DataRuns { get; set; } = new List<DataRun>();

        public class DataRun
        {
            public long StartCluster { get; set; }
            public long Length { get; set; }
        }
    }
}
