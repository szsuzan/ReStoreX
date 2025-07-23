using Microsoft.Win32.SafeHandles;
using System.IO;

namespace ReStoreX.Core
{
    public class RawImage : Stream
    {
        private readonly FileStream fileStream;

        public RawImage(string path)
        {
            fileStream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
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

    public class PhysicalDisk : Stream
    {
        private readonly SafeFileHandle handle;
        private readonly FileStream fileStream;
        private readonly long diskLength;
        private readonly long sectorSize;

        public PhysicalDisk(SafeFileHandle handle, long length, long sectorSize)
        {
            this.handle = handle;
            this.diskLength = length;
            this.sectorSize = sectorSize;
            this.fileStream = new FileStream(handle, FileAccess.Read);
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
