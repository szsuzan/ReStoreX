using ReStoreX.Core;
using System;
using System.Collections.Generic;

namespace ReStoreX.Analyzers
{
    public class IntegrityAnalyzer
    {
        private readonly IReStoreXFileSystem fileSystem;

        public IntegrityAnalyzer(IReStoreXFileSystem fs)
        {
            fileSystem = fs;
        }

        public List<string> Analyze()
        {
            var report = new List<string>();
            try
            {
                foreach (var dir in fileSystem.GetDirectories("/"))
                {
                    AnalyzeDirectory(dir, report);
                }
            }
            catch (Exception ex)
            {
                report.Add($"Error during analysis: {ex.Message}");
            }
            return report;
        }

        private void AnalyzeDirectory(DirectoryEntry dir, List<string> report)
        {
            foreach (var file in dir.Files)
            {
                if (file.FileSize < 0)
                {
                    report.Add($"Invalid file size detected: {file.FileName}");
                }
            }
            foreach (var subDir in dir.SubDirectories)
            {
                AnalyzeDirectory(subDir, report);
            }
        }
    }
}
