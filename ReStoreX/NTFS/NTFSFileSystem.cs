using ReStoreX.Core;
using DiscUtils.Ntfs;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace ReStoreX.NTFS
{
    public class NTFSFileSystem : IReStoreXFileSystem
    {
        private NtfsFileSystem? ntfs;
        private MftScanner? mftScanner;

        private MftScanner MftScanner
        {
            get
            {
                if (mftScanner == null || ntfs == null)
                    throw new InvalidOperationException("Filesystem not loaded");
                return mftScanner;
            }
        }

        public string Name => "NTFS";
        public long BytesPerCluster => ntfs?.ClusterSize ?? 0;
        public long MaxClusters => ntfs?.TotalClusters ?? 0;
        public long TotalSpace => ntfs?.Size ?? 0;
        public long FreeSpace => ntfs?.AvailableSpace ?? 0;
        public bool IsReady => ntfs != null;

        public void LoadFromStream(Stream diskStream)
        {
            if (diskStream == null)
                throw new ArgumentNullException(nameof(diskStream));
            ntfs = new NtfsFileSystem(diskStream);
        }

        public IEnumerable<FileEntry> GetFiles(string directory = "/")
        {
            if (ntfs == null)
                throw new InvalidOperationException("Filesystem not loaded");

            var files = new List<FileEntry>();
            foreach (var file in ntfs.GetFiles(directory))
            {
                var info = ntfs.GetFileInfo(file);
                files.Add(new FileEntry
                {
                    FileName = Path.GetFileName(file),
                    FileSize = info.Length,
                    CreationTime = info.CreationTimeUtc,
                    LastWriteTime = info.LastWriteTimeUtc,
                    LastAccessTime = info.LastAccessTimeUtc,
                    Attributes = info.Attributes
                });
            }
            return files;
        }

        public IEnumerable<DirectoryEntry> GetDirectories(string directory = "/")
        {
            if (ntfs == null)
                throw new InvalidOperationException("Filesystem not loaded");

            var entries = new List<DirectoryEntry>();
            foreach (var dir in ntfs.GetDirectories(directory))
            {
                var info = ntfs.GetDirectoryInfo(dir);
                var entry = new DirectoryEntry
                {
                    DirectoryName = Path.GetFileName(dir),
                    CreationTime = info.CreationTimeUtc,
                    LastWriteTime = info.LastWriteTimeUtc,
                    IsRoot = dir == "/"
                };

                entry.Files.AddRange(GetFiles(dir));
                entries.Add(entry);
            }
            return entries;
        }

        public byte[] ReadFile(string path)
        {
            if (ntfs == null)
                throw new InvalidOperationException("Filesystem not loaded");

            using var stream = ntfs.OpenFile(path, FileMode.Open);
            var buffer = new byte[stream.Length];
            stream.Read(buffer, 0, buffer.Length);
            return buffer;
        }

        public IEnumerable<DeletedFileEntry> ScanForDeletedFiles()
        {
            if (ntfs == null)
                throw new InvalidOperationException("Filesystem not loaded");

            var deletedFiles = new List<DeletedFileEntry>();

            try
            {
                // Access the MFT records through our scanner
                var records = MftScanner.ScanMft();
                foreach (var record in records)
                {
                    if (!IsFileRecoverable(record))
                        continue;

                    var deletedFile = new DeletedFileEntry
                    {
                        FileName = GetFileNameFromMft(record),
                        FileSize = GetFileSizeFromMft(record),
                        CreationTime = GetCreationTimeFromMft(record),
                        LastWriteTime = GetLastWriteTimeFromMft(record),
                        LastAccessTime = GetLastAccessTimeFromMft(record),
                        IsDeleted = true,
                        RecoveryStatus = FileRecoveryStatus.Recoverable
                    };

                    deletedFile.FragmentedClusters = GetFileClusters(record);
                    deletedFile.RecoveryProbability = CalculateRecoveryProbability(record);
                    deletedFile.SignatureType = DetectFileSignature(record);

                    deletedFiles.Add(deletedFile);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error scanning for deleted files: {ex.Message}");
            }

            return deletedFiles;
        }

        public bool RecoverFile(DeletedFileEntry file, string destinationPath)
        {
            if (ntfs == null || file.FragmentedClusters == null || file.FragmentedClusters.Count == 0)
                return false;

            try
            {
                using (var fs = File.Create(destinationPath))
                {
                    foreach (var cluster in file.FragmentedClusters)
                    {
                        var clusterData = ReadCluster(cluster);
                        fs.Write(clusterData, 0, clusterData.Length);
                    }
                }

                return true;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error recovering file: {ex.Message}");
                return false;
            }
        }

        public bool RecoverFileBySignature(string fileSignature, string destinationPath)
        {
            if (ntfs == null)
                return false;

            try
            {
                var signatures = new Dictionary<string, byte[]>
                {
                    { "JPEG", new byte[] { 0xFF, 0xD8, 0xFF } },
                    { "PNG", new byte[] { 0x89, 0x50, 0x4E, 0x47 } },
                    { "PDF", new byte[] { 0x25, 0x50, 0x44, 0x46 } },
                    // Add more signatures as needed
                };

                if (!signatures.TryGetValue(fileSignature, out var signature))
                    return false;

                // Scan clusters for the signature
                for (long cluster = 0; cluster < ntfs.TotalClusters; cluster++)
                {
                    var data = ReadCluster(cluster);
                    if (SignatureFound(data, signature))
                    {
                        // Found a matching file, try to recover it
                        var recoveredFile = new DeletedFileEntry
                        {
                            FileName = $"Recovered_{fileSignature}_{cluster}",
                            FileSize = EstimateFileSizeFromSignature(data, signature),
                            FragmentedClusters = new List<long> { cluster }
                        };

                        return RecoverFile(recoveredFile, destinationPath);
                    }
                }

                return false;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error recovering file by signature: {ex.Message}");
                return false;
            }
        }

        #region Helper Methods

        private byte[] ReadCluster(long clusterNumber)
        {
            if (ntfs == null)
                throw new InvalidOperationException("Filesystem not loaded");

            var clusterSize = (int)Math.Min(ntfs.ClusterSize, int.MaxValue);
            var buffer = new byte[clusterSize];
            
            using (var stream = ntfs.OpenCluster(clusterNumber))
            {
                stream.Read(buffer, 0, clusterSize);
            }
            
            return buffer;
        }

        private bool SignatureFound(byte[] data, byte[] signature)
        {
            if (data == null || signature == null || data.Length < signature.Length)
                return false;

            for (int i = 0; i < signature.Length; i++)
            {
                if (data[i] != signature[i])
                    return false;
            }

            return true;
        }

        private long EstimateFileSizeFromSignature(byte[] data, byte[] signature)
        {
            // This is a simplified implementation
            // In a real scenario, we would:
            // 1. Parse file format specific headers
            // 2. Look for format-specific end markers
            // 3. Validate file structure
            return data.Length;
        }

        private string GetFileNameFromMft(INtfsFileRecord record)
        {
            var nameAttribute = record.GetAttribute<FileNameAttribute>();
            return nameAttribute?.FileName ?? "Unknown";
        }

        private long GetFileSizeFromMft(INtfsFileRecord record)
        {
            var stdInfo = record.GetAttribute<StandardInformation>();
            return stdInfo?.FileSize ?? 0;
        }

        private DateTime GetCreationTimeFromMft(INtfsFileRecord record)
        {
            var stdInfo = record.GetAttribute<StandardInformation>();
            return stdInfo?.CreationTime ?? DateTime.MinValue;
        }

        private DateTime GetLastWriteTimeFromMft(INtfsFileRecord record)
        {
            var stdInfo = record.GetAttribute<StandardInformation>();
            return stdInfo?.LastWriteTime ?? DateTime.MinValue;
        }

        private DateTime GetLastAccessTimeFromMft(INtfsFileRecord record)
        {
            var stdInfo = record.GetAttribute<StandardInformation>();
            return stdInfo?.LastAccessTime ?? DateTime.MinValue;
        }

        private bool IsFileRecoverable(INtfsFileRecord record)
        {
            // Check if the file data is still intact
            var dataAttr = record.GetAttribute<DataAttribute>();
            return dataAttr != null && !dataAttr.IsCompressed && !dataAttr.IsEncrypted;
        }

        private List<long> GetFileClusters(INtfsFileRecord record)
        {
            var clusters = new List<long>();
            var dataAttr = record.GetAttribute<DataAttribute>();
            
            if (dataAttr != null)
            {
                foreach (var run in dataAttr.DataRuns)
                {
                    for (long i = 0; i < run.Length; i++)
                    {
                        clusters.Add(run.StartCluster + i);
                    }
                }
            }

            return clusters;
        }

        private double CalculateRecoveryProbability(INtfsFileRecord record)
        {
            // Analyze various factors to estimate recovery probability
            double probability = 1.0;

            // Check if basic attributes are present
            if (record.GetAttribute<StandardInformation>() == null)
                probability *= 0.7;
            if (record.GetAttribute<FileNameAttribute>() == null)
                probability *= 0.8;

            // Check data attribute
            var dataAttr = record.GetAttribute<DataAttribute>();
            if (dataAttr == null)
                return 0.0;

            // Check for compression/encryption
            if (dataAttr.IsCompressed)
                probability *= 0.6;
            if (dataAttr.IsEncrypted)
                probability *= 0.3;

            // Check for fragmentation
            if (dataAttr.DataRuns.Count > 1)
                probability *= 0.9;

            return probability;
        }

        private string? DetectFileSignature(INtfsFileRecord record)
        {
            try
            {
                var dataAttr = record.GetAttribute<DataAttribute>();
                if (dataAttr == null || dataAttr.DataRuns.Count == 0)
                    return null;

                // Read first few bytes to detect signature
                var firstCluster = dataAttr.DataRuns[0].StartCluster;
                var data = ReadCluster(firstCluster);

                if (data.Length >= 4)
                {
                    // Check common signatures
                    if (data[0] == 0xFF && data[1] == 0xD8 && data[2] == 0xFF)
                        return "JPEG";
                    if (data[0] == 0x89 && data[1] == 0x50 && data[2] == 0x4E && data[3] == 0x47)
                        return "PNG";
                    if (data[0] == 0x25 && data[1] == 0x50 && data[2] == 0x44 && data[3] == 0x46)
                        return "PDF";
                }

                return null;
            }
            catch
            {
                return null;
            }
        }

        #endregion

        public IEnumerable<ClusterInfo> GetClusterMap()
        {
            if (ntfs == null)
                throw new InvalidOperationException("Filesystem not loaded");

            var clusters = new List<ClusterInfo>();
            // TODO: Implement cluster mapping using NTFS Master File Table ($MFT)
            return clusters;
        }

        public DiskHealthInfo GetDiskHealth()
        {
            if (ntfs == null)
                throw new InvalidOperationException("Filesystem not loaded");

            return new DiskHealthInfo
            {
                SerialNumber = "Unknown",
                Model = "NTFS Volume",
                FirmwareVersion = "N/A",
                TotalHours = 0,
                Temperature = 0,
                BadSectorCount = 0
            };
        }

        public IEnumerable<BadSectorInfo> ScanForBadSectors()
        {
            // NTFS bad sector scanning implementation
            return new List<BadSectorInfo>();
        }

        public bool RepairBadSectors(IEnumerable<BadSectorInfo> sectors)
        {
            // NTFS bad sector repair implementation
            return false;
        }
    }
}
