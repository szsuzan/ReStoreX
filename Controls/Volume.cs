using System;
using ReStoreX.Core;

namespace ReStoreX.Controls
{
    /// <summary>
    /// Simplified Volume class placeholder for ReStoreX.
    /// </summary>
    public class Volume
    {
    private IDisk disk;
    private string name;
    private long offset;
    private long length;
    private IReStoreXFileSystem? fileSystem;
    private bool mounted;

    public Volume(IDisk disk, string name, long offset, long length)
    {
        this.disk = disk;
        this.name = name;
        this.offset = offset;
        this.length = length;
        this.mounted = false;
    }

    public string DeviceId => disk.DeviceId;
    public string Name => name;
    public long Offset => offset;
    public long Length => length;
    public bool Mounted => mounted;
    public IReStoreXFileSystem? FileSystem => fileSystem;

    public long GetUsedSpace() => FileSystem?.TotalSpace - FileSystem?.FreeSpace ?? 0;
    public long GetFreeSpace() => FileSystem?.FreeSpace ?? 0;
    public long GetTotalSpace() => FileSystem?.TotalSpace ?? 0;
    public long GetClusterSize() => FileSystem?.BytesPerCluster ?? 0;

    public void Mount(IReStoreXFileSystem fs)
    {
        fileSystem = fs;
        mounted = true;
    }

    public void Unmount()
    {
        fileSystem = null;
        mounted = false;
    }
    }
}
