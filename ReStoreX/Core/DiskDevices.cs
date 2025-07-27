using Microsoft.Win32.SafeHandles;
using System.IO;

namespace ReStoreX.Core
{
    public class DiskImage : Stream, IDisk
    {
        private readonly FileStream fileStream;
        private readonly string path;

        public DiskImage(string path)
        {
            this.path = path;
            fileStream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        }

        public string DeviceId => path;

        public byte[] ReadSector(long offset, int size)
        {
            var buffer = new byte[size];
            fileStream.Position = offset;
            fileStream.Read(buffer, 0, size);
            return buffer;
        }

        public void WriteSector(long offset, byte[] data)
        {
            fileStream.Position = offset;
            fileStream.Write(data, 0, data.Length);
        }

        public override bool CanRead => fileStream.CanRead;
        public override bool CanSeek => fileStream.CanSeek;
        public override bool CanWrite => false;
        public override long Length => fileStream.Length;
        public override long Position 
        { 
            get => fileStream.Position;
            set => fileStream.Position = value;
        }

        public override void Flush() => fileStream.Flush();
        public override int Read(byte[] buffer, int offset, int count) => fileStream.Read(buffer, offset, count);
        public override long Seek(long offset, SeekOrigin origin) => fileStream.Seek(offset, origin);
        public override void SetLength(long value) => throw new System.NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new System.NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                fileStream.Dispose();
            }
            base.Dispose(disposing);
        }
    }

    public class PhysicalDisk : Stream, IDisk
    {
        private readonly SafeFileHandle handle;
        private readonly FileStream fileStream;
        private readonly long diskLength;
        private readonly long sectorSize;
        private readonly string deviceId;

        public PhysicalDisk(SafeFileHandle handle, string deviceId, long length, long sectorSize)
        {
            this.handle = handle;
            this.deviceId = deviceId;
            this.diskLength = length;
            this.sectorSize = sectorSize;
            this.fileStream = new FileStream(handle, FileAccess.Read);
        }

        public string DeviceId => deviceId;
        
        public byte[] ReadSector(long offset, int size)
        {
            var buffer = new byte[size];
            fileStream.Position = offset;
            fileStream.Read(buffer, 0, size);
            return buffer;
        }

        public void WriteSector(long offset, byte[] data)
        {
            fileStream.Position = offset;
            fileStream.Write(data, 0, data.Length);
        }

        public override bool CanRead => true;
        public override bool CanSeek => true;
        public override bool CanWrite => false;
        public override long Length => diskLength;
        public override long Position
        {
            get => fileStream.Position;
            set => fileStream.Position = value;
        }

        public override void Flush() => fileStream.Flush();
        public override int Read(byte[] buffer, int offset, int count) => fileStream.Read(buffer, offset, count);
        public override long Seek(long offset, SeekOrigin origin) => fileStream.Seek(offset, origin);
        public override void SetLength(long value) => throw new System.NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new System.NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                fileStream.Dispose();
                handle.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}
