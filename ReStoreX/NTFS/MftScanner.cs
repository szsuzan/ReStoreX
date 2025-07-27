using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using DiscUtils.Ntfs;

namespace ReStoreX.NTFS
{
    public class MftScanner
    {
        private readonly NtfsFileSystem _ntfs;
        private readonly Stream _diskStream;

        public MftScanner(NtfsFileSystem ntfs)
        {
            _ntfs = ntfs;
            var property = typeof(NtfsFileSystem).GetProperty("DiskStream", 
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            
            if (property == null)
                throw new InvalidOperationException("Could not find DiskStream property");
                
            _diskStream = property.GetValue(ntfs) as Stream ?? 
                throw new InvalidOperationException("Could not access disk stream");
        }

        public IEnumerable<INtfsFileRecord> ScanMft()
        {
            var records = new List<INtfsFileRecord>();
            var mftStream = GetMftStream();
            if (mftStream == null) yield break;

            long mftRecordSize = GetMftRecordSize();
            byte[] recordBuffer = new byte[mftRecordSize];

            while (mftStream.Position < mftStream.Length)
            {
                if (mftStream.Read(recordBuffer, 0, (int)mftRecordSize) != mftRecordSize)
                    break;

                if (IsValidFileRecord(recordBuffer))
                {
                    var record = ParseFileRecord(recordBuffer);
                    if (record != null)
                        yield return record;
                }
            }
        }

        private Stream GetMftStream()
        {
            // Get the MFT location from NTFS boot sector
            _diskStream.Position = 0;
            byte[] bootSector = new byte[512];
            _diskStream.Read(bootSector, 0, 512);

            // MFT location is at offset 0x30 in boot sector (8 bytes)
            long mftLocation = BitConverter.ToInt64(bootSector, 0x30) * _ntfs.ClusterSize;
            
            var stream = new MemoryStream();
            _diskStream.Position = mftLocation;
            _diskStream.CopyTo(stream);
            stream.Position = 0;
            
            return stream;
        }

        private long GetMftRecordSize()
        {
            // Get MFT record size from boot sector
            _diskStream.Position = 0;
            byte[] bootSector = new byte[512];
            _diskStream.Read(bootSector, 0, 512);

            // MFT record size is at offset 0x40 in boot sector (1 byte)
            int mftRecordSizeClusterShift = bootSector[0x40];
            return mftRecordSizeClusterShift < 0 ? 
                1 << -mftRecordSizeClusterShift : 
                mftRecordSizeClusterShift * _ntfs.ClusterSize;
        }

        private bool IsValidFileRecord(byte[] recordBuffer)
        {
            // Check "FILE" signature at offset 0
            return recordBuffer.Length >= 4 &&
                   recordBuffer[0] == 0x46 && // 'F'
                   recordBuffer[1] == 0x49 && // 'I'
                   recordBuffer[2] == 0x4C && // 'L'
                   recordBuffer[3] == 0x45;   // 'E'
        }

        private NtfsFileRecord ParseFileRecord(byte[] recordBuffer)
        {
            try
            {
                // Parse basic record header
                var record = new NtfsFileRecord(BitConverter.ToInt64(recordBuffer, 0x20));

                // Find and parse attributes
                int offset = BitConverter.ToUInt16(recordBuffer, 0x14); // Offset to first attribute

                while (offset < recordBuffer.Length - 4)
                {
                    uint attributeType = BitConverter.ToUInt32(recordBuffer, offset);
                    if (attributeType == 0xFFFFFFFF) // End marker
                        break;

                    var attribute = ParseAttribute(recordBuffer, ref offset);
                    if (attribute != null)
                        record.AddAttribute(attribute);

                    offset += BitConverter.ToInt32(recordBuffer, offset + 4); // Move to next attribute
                }

                return record;
            }
            catch
            {
                return new NtfsFileRecord(-1); // Return a dummy record for invalid entries
            }
        }

        private NtfsAttribute? ParseAttribute(byte[] buffer, ref int offset)
        {
            var type = (AttributeType)BitConverter.ToUInt32(buffer, offset);
            bool isResident = (buffer[offset + 8] & 0x01) == 0;

            return type switch
            {
                AttributeType.StandardInformation => ParseStandardInformation(buffer, offset, isResident),
                AttributeType.FileName => ParseFileName(buffer, offset, isResident),
                AttributeType.Data => ParseData(buffer, offset, isResident),
                _ => null
            };
        }

        private StandardInformation? ParseStandardInformation(byte[] buffer, int offset, bool isResident)
        {
            if (!isResident) return null;

            var contentOffset = offset + BitConverter.ToUInt16(buffer, offset + 0x14);
            return new StandardInformation
            {
                CreationTime = DateTime.FromFileTime(BitConverter.ToInt64(buffer, contentOffset)),
                LastWriteTime = DateTime.FromFileTime(BitConverter.ToInt64(buffer, contentOffset + 8)),
                LastAccessTime = DateTime.FromFileTime(BitConverter.ToInt64(buffer, contentOffset + 16)),
                FileSize = BitConverter.ToInt64(buffer, contentOffset + 48)
            };
        }

        private FileNameAttribute? ParseFileName(byte[] buffer, int offset, bool isResident)
        {
            if (!isResident) return null;

            var contentOffset = offset + BitConverter.ToUInt16(buffer, offset + 0x14);
            var nameLength = buffer[contentOffset + 0x40];
            var nameBytes = new byte[nameLength * 2];
            Array.Copy(buffer, contentOffset + 0x42, nameBytes, 0, nameLength * 2);
            
            return new FileNameAttribute
            {
                FileName = System.Text.Encoding.Unicode.GetString(nameBytes)
            };
        }

        private DataAttribute ParseData(byte[] buffer, int offset, bool isResident)
        {
            var attr = new DataAttribute();

            if (!isResident)
            {
                // Parse non-resident data runs
                var runListOffset = offset + BitConverter.ToUInt16(buffer, offset + 0x20);
                long currentLcn = 0;

                while (buffer[runListOffset] != 0)
                {
                    byte header = buffer[runListOffset++];
                    int lengthBytes = header & 0x0F;
                    int lcnBytes = (header >> 4) & 0x0F;

                    long runLength = 0;
                    for (int i = 0; i < lengthBytes; i++)
                        runLength |= (long)buffer[runListOffset + i] << (i * 8);

                    long lcnOffset = 0;
                    for (int i = 0; i < lcnBytes; i++)
                        lcnOffset |= (long)buffer[runListOffset + lengthBytes + i] << (i * 8);

                    if ((lcnOffset & (1L << ((lcnBytes * 8) - 1))) != 0)
                        lcnOffset |= -1L << (lcnBytes * 8);

                    currentLcn += lcnOffset;

                    attr.DataRuns.Add(new DataAttribute.DataRun
                    {
                        StartCluster = currentLcn,
                        Length = runLength
                    });

                    runListOffset += lengthBytes + lcnBytes;
                }
            }

            return attr;
        }
    }
}
