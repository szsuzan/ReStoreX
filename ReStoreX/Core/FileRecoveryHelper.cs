using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using FileSignatures;

namespace ReStoreX.Core
{
    public static class FileRecoveryHelper
    {
        private static readonly Dictionary<string, byte[]> CommonSignatures = new()
        {
            { ".jpg", new byte[] { 0xFF, 0xD8, 0xFF } },
            { ".png", new byte[] { 0x89, 0x50, 0x4E, 0x47 } },
            { ".pdf", new byte[] { 0x25, 0x50, 0x44, 0x46 } },
            { ".zip", new byte[] { 0x50, 0x4B, 0x03, 0x04 } },
            { ".docx", new byte[] { 0x50, 0x4B, 0x03, 0x04 } },
            { ".mp3", new byte[] { 0x49, 0x44, 0x33 } },
            { ".mp4", new byte[] { 0x66, 0x74, 0x79, 0x70 } }
        };

        public static async Task<List<FileSignatureMatch>> ScanForKnownFileTypes(Stream stream, long offset, int length)
        {
            var matches = new List<FileSignatureMatch>();
            var buffer = new byte[Math.Min(length, 8192)];
            
            stream.Position = offset;
            await stream.ReadAsync(buffer.AsMemory(0, buffer.Length));

            foreach (var signature in CommonSignatures)
            {
                if (IsMatch(buffer, signature.Value))
                {
                    matches.Add(new FileSignatureMatch
                    {
                        Extension = signature.Key,
                        Offset = offset,
                        Confidence = CalculateConfidence(buffer, signature.Value)
                    });
                }
            }

            return matches;
        }

        public static async Task<byte[]?> RecoverFileContent(Stream stream, FileSignatureMatch match, long maxSize)
        {
            try
            {
                using var memStream = new MemoryStream();
                stream.Position = match.Offset;

                var endMarker = GetEndMarker(match.Extension);
                var buffer = new byte[8192];
                var totalRead = 0L;
                var markerFound = false;

                while (totalRead < maxSize)
                {
                    var read = await stream.ReadAsync(buffer.AsMemory(0, buffer.Length));
                    if (read == 0) break;

                    if (endMarker != null)
                    {
                        var endPos = FindEndMarker(buffer, read, endMarker);
                        if (endPos >= 0)
                        {
                            await memStream.WriteAsync(buffer.AsMemory(0, endPos + endMarker.Length));
                            markerFound = true;
                            break;
                        }
                    }

                    await memStream.WriteAsync(buffer.AsMemory(0, read));
                    totalRead += read;
                }

                return markerFound || endMarker == null ? memStream.ToArray() : null;
            }
            catch
            {
                return null;
            }
        }

        private static bool IsMatch(byte[] buffer, byte[] signature)
        {
            if (buffer.Length < signature.Length) return false;
            
            for (int i = 0; i < signature.Length; i++)
            {
                if (buffer[i] != signature[i])
                    return false;
            }
            
            return true;
        }

        private static double CalculateConfidence(byte[] buffer, byte[] signature)
        {
            // Base confidence on signature match and surrounding content
            double confidence = 1.0;
            
            // Check for common file contents after signature
            if (buffer.Length > signature.Length + 32)
            {
                // Analyze entropy and patterns in the data
                var entropy = CalculateEntropy(buffer, signature.Length, 32);
                confidence *= entropy;
            }
            
            return confidence;
        }

        private static double CalculateEntropy(byte[] data, int start, int length)
        {
            var frequencies = new int[256];
            var end = Math.Min(start + length, data.Length);
            
            for (int i = start; i < end; i++)
            {
                frequencies[data[i]]++;
            }
            
            double entropy = 0;
            var actualLength = end - start;
            
            for (int i = 0; i < 256; i++)
            {
                if (frequencies[i] > 0)
                {
                    var probability = (double)frequencies[i] / actualLength;
                    entropy -= probability * Math.Log2(probability);
                }
            }
            
            // Normalize entropy to 0-1 range
            return entropy / 8.0;
        }

        private static byte[]? GetEndMarker(string extension)
        {
            return extension.ToLower() switch
            {
                ".jpg" => new byte[] { 0xFF, 0xD9 },
                ".png" => new byte[] { 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82 },
                ".pdf" => new byte[] { 0x25, 0x25, 0x45, 0x4F, 0x46 },
                _ => null
            };
        }

        private static int FindEndMarker(byte[] buffer, int length, byte[] marker)
        {
            for (int i = 0; i <= length - marker.Length; i++)
            {
                bool found = true;
                for (int j = 0; j < marker.Length; j++)
                {
                    if (buffer[i + j] != marker[j])
                    {
                        found = false;
                        break;
                    }
                }
                if (found) return i;
            }
            return -1;
        }
    }

    public class FileSignatureMatch
    {
        public required string Extension { get; set; }
        public long Offset { get; set; }
        public double Confidence { get; set; }
    }
}
