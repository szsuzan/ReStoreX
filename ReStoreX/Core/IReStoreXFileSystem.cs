// ============================================================================
// ReStoreX Core Interface and Filesystem Definitions
// ============================================================================

using System;
using System.Collections.Generic;
using System.IO;

namespace ReStoreX.Core
{
    public interface IDisk
    {
        string DeviceId { get; }
        long Length { get; }
        byte[] ReadSector(long offset, int size);
        void WriteSector(long offset, byte[] data);
    }

    /// <summary>
    /// Generic interface for all supported filesystems (FATX, FAT32, NTFS).
    /// </summary>
    public interface IReStoreXFileSystem
    {
        string Name { get; }
        long BytesPerCluster { get; }
        long MaxClusters { get; }
        long TotalSpace { get; }
        long FreeSpace { get; }
        bool IsReady { get; }

        void LoadFromStream(Stream diskStream);
        IEnumerable<FileEntry> GetFiles(string directory = "/");
        IEnumerable<DirectoryEntry> GetDirectories(string directory = "/");
        byte[] ReadFile(string path);
        
        // Recovery features
        IEnumerable<DeletedFileEntry> ScanForDeletedFiles();
        bool RecoverFile(DeletedFileEntry file, string destinationPath);
        bool RecoverFileBySignature(string fileSignature, string destinationPath);
        IEnumerable<ClusterInfo> GetClusterMap();
        
        // Disk health and analysis
        DiskHealthInfo GetDiskHealth();
        IEnumerable<BadSectorInfo> ScanForBadSectors();
        bool RepairBadSectors(IEnumerable<BadSectorInfo> sectors);
    }

    /// <summary>
    /// Represents a generic file entry.
    /// </summary>
    public class FileEntry
    {
        public required string FileName { get; set; }
        public string FullPath { get; set; } = "";
        public long FileSize { get; set; }
        public long FirstCluster { get; set; }
        public DateTime CreationTime { get; set; }
        public DateTime LastWriteTime { get; set; }
        public DateTime LastAccessTime { get; set; }
        public FileAttributes Attributes { get; set; }
        public bool IsCorrupted { get; set; }
        public bool IsDeleted { get; set; }
        public string? ErrorMessage { get; set; }
    }

    /// <summary>
    /// Represents a generic directory entry.
    /// </summary>
    public class DirectoryEntry
    {
        public required string DirectoryName { get; set; }
        public string FullPath { get; set; } = "";
        public List<FileEntry> Files { get; set; } = new List<FileEntry>();
        public List<DirectoryEntry> SubDirectories { get; set; } = new List<DirectoryEntry>();
        public DateTime CreationTime { get; set; }
        public DateTime LastWriteTime { get; set; }
        public DateTime LastAccessTime { get; set; }
        public bool IsRoot { get; set; }
    }

    public class DeletedFileEntry : FileEntry
    {
        public FileRecoveryStatus RecoveryStatus { get; set; }
        public double RecoveryProbability { get; set; }
        public string? SignatureType { get; set; }
        public string? DirectoryPath { get; set; }
        public List<long> FragmentedClusters { get; set; } = new();
    }

    public enum FileRecoveryStatus
    {
        Recoverable,
        Fragmented,
        PartiallyOverwritten,
        Unrecoverable
    }

    public class ClusterInfo
    {
        public long ClusterId { get; set; }
        public ClusterStatus Status { get; set; }
        public string? FileName { get; set; }
        public long Size { get; set; }
    }

    public enum ClusterStatus
    {
        Free,
        Used,
        Bad,
        Reserved
    }

    public class DiskHealthInfo
    {
        public required string SerialNumber { get; set; }
        public required string Model { get; set; }
        public required string FirmwareVersion { get; set; }
        public long TotalHours { get; set; }
        public int Temperature { get; set; }
        public int BadSectorCount { get; set; }
        public long PowerCycleCount { get; set; }
        public Dictionary<SmartAttribute, SmartData> SmartAttributes { get; set; } = new();
        public DiskHealthStatus Status { get; set; }
        
        public DiskHealthInfo()
        {
            Status = CalculateHealthStatus();
        }

        private DiskHealthStatus CalculateHealthStatus()
        {
            if (BadSectorCount > 100 || Temperature > 65)
                return DiskHealthStatus.Critical;
                
            if (BadSectorCount > 10 || Temperature > 55)
                return DiskHealthStatus.Warning;
                
            return DiskHealthStatus.Healthy;
        }
    }

    public class RecoveryReport
    {
        public required string FileName { get; set; }
        public long FileSize { get; set; }
        public string? OriginalPath { get; set; }
        public bool IsFragmented { get; set; }
        public int FragmentCount { get; set; }
        public bool HasBadSectors { get; set; }
        public int BadSectorCount { get; set; }
        public bool IsRecoverable { get; set; }
        public bool SignatureFound { get; set; }

        public string GetSuggestions()
        {
            var suggestions = new List<string>();

            if (IsFragmented)
                suggestions.Add($"File is fragmented into {FragmentCount} pieces.");

            if (HasBadSectors)
                suggestions.Add($"File has {BadSectorCount} bad sectors.");

            if (!IsRecoverable && SignatureFound)
                suggestions.Add("Try recovering by file signature.");

            return string.Join(" ", suggestions);
        }
    }

    public class SmartData
    {
        public int CurrentValue { get; set; }
        public int WorstValue { get; set; }
        public int ThresholdValue { get; set; }
        public bool IsOK => CurrentValue >= ThresholdValue;
    }

    public enum SmartAttribute
    {
        ReadErrorRate = 1,
        ThroughputPerformance = 2,
        SpinUpTime = 3,
        StartStopCount = 4,
        ReallocatedSectorsCount = 5,
        SeekErrorRate = 7,
        PowerOnHours = 9,
        SpinRetryCount = 10,
        CalibrationRetryCount = 11,
        PowerCycleCount = 12,
        Temperature = 194,
        ReallocationEventCount = 196,
        CurrentPendingSectorCount = 197,
        UncorrectableSectorCount = 198,
        DiskShiftStatus = 200
    }

    public enum DiskHealthStatus
    {
        Healthy,    // All parameters within normal range
        Warning,    // Some parameters need attention but disk is functional
        Critical    // Immediate action required to prevent data loss
    }

    public class BadSectorInfo
    {
        public required long SectorNumber { get; set; }
        public required BadSectorType Type { get; set; }
        public bool IsRepairable { get; set; }
        public byte[]? OriginalData { get; set; }
        public DateTime DetectedTime { get; set; } = DateTime.UtcNow;
        public int RetryCount { get; set; }
        public string? AffectedFile { get; set; }
        public long? ClusterNumber { get; set; }
        
        public bool AttemptRepair(IReStoreXFileSystem fileSystem)
        {
            if (!IsRepairable || RetryCount >= 3)
                return false;

            RetryCount++;
            return fileSystem.RepairBadSectors(new[] { this });
        }
    }

    public enum BadSectorType
    {
        ReadError,           // Cannot read sector data
        WriteError,          // Cannot write to sector
        UnstableSector,     // Sector occasionally fails
        PhysicalDamage,     // Physical damage detected
        CrosslinkedSector,  // Sector claimed by multiple files
        LostCluster         // Cluster marked bad in FAT/MFT
    }
}

