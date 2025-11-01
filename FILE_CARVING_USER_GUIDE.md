# File Carving User Guide

## Understanding Your Recovery Results

### File Quality Scores
After a file carving scan, each recovered file is assigned a **quality score** from 0-100:

- **90-100**: ✅ **Excellent** - Complete file with all markers present
- **70-89**: ⚠️ **Good** - File appears complete but may have minor issues
- **50-69**: ⚠️ **Fair** - File passed validation but shows signs of fragmentation
- **0-49**: ❌ **Poor** - File may be corrupted or severely fragmented

### Partial Files
Files marked as **partial** (`is_partial: true`) indicate:
- Missing file termination markers (e.g., JPEG EOI, PNG IEND, PDF %%EOF)
- Incomplete internal structure
- Likely fragmented or truncated during deletion

**File Naming**: Partial files are saved with `.partial` extension
- Example: `12345.partial.jpg` instead of `12345.jpg`

### Manifest File
Every recovery creates a `manifest.json` file containing:
- **Scan Info**: When, where, and how the scan was performed
- **Statistics**: Total files, partial files, total size
- **File Details**: Complete metadata for every recovered file

## Reading the Manifest

### Quick Stats
```json
{
  "statistics": {
    "total_files_recovered": 150,
    "unique_files": 150,
    "total_size_bytes": 52428800,
    "partial_files": 12
  }
}
```

### Individual File Info
```json
{
  "filename": "12345.jpg",
  "path": "C:\\recovered\\12345.jpg",
  "size_bytes": 524288,
  "offset": 1048576,
  "file_type": "jpg",
  "md5": "abc123...",
  "sha256": "def456...",
  "validation_score": 95,
  "is_partial": false,
  "method": "signature_carving"
}
```

### Key Fields Explained
- **offset**: Where the file was found on the drive (in bytes)
- **md5**: Quick hash for duplicate detection
- **sha256**: Secure hash for integrity verification
- **validation_score**: Quality score (0-100)
- **is_partial**: Whether file appears fragmented

## Using the Manifest

### Filter by Quality (PowerShell)
```powershell
# Get only high-quality files (score >= 80)
$manifest = Get-Content manifest.json | ConvertFrom-Json
$goodFiles = $manifest.files | Where-Object {$_.validation_score -ge 80}
$goodFiles | Format-Table filename, validation_score, size_bytes
```

### Find Partial Files
```powershell
# List all partial files
$manifest = Get-Content manifest.json | ConvertFrom-Json
$partial = $manifest.files | Where-Object {$_.is_partial -eq $true}
$partial | Format-Table filename, validation_score
```

### Verify File Integrity
```powershell
# Verify SHA256 hash matches
$manifest = Get-Content manifest.json | ConvertFrom-Json
$file = $manifest.files[0]
$actualHash = (Get-FileHash $file.path -Algorithm SHA256).Hash
if ($actualHash -eq $file.sha256.ToUpper()) {
    Write-Host "✅ File integrity verified"
} else {
    Write-Host "❌ File may be corrupted"
}
```

### Export Specific File Types
```powershell
# Export only JPEGs with score >= 70
$manifest = Get-Content manifest.json | ConvertFrom-Json
$goodJpegs = $manifest.files | Where-Object {
    $_.file_type -eq "jpg" -and $_.validation_score -ge 70
}
$goodJpegs | Export-Csv good_jpegs.csv -NoTypeInformation
```

### Calculate Statistics
```powershell
# Average score by file type
$manifest = Get-Content manifest.json | ConvertFrom-Json
$manifest.files | Group-Object file_type | ForEach-Object {
    [PSCustomObject]@{
        FileType = $_.Name
        Count = $_.Count
        AvgScore = ($_.Group | Measure-Object validation_score -Average).Average
    }
}
```

## Best Practices

### 1. Review Manifest Before Opening Files
- Check validation scores to prioritize recovery efforts
- Filter out low-quality files to save time
- Focus on high-score, non-partial files first

### 2. Verify Important Files
```powershell
# For critical files, verify SHA256 hash
Get-FileHash important_document.pdf -Algorithm SHA256
# Compare with hash in manifest.json
```

### 3. Handle Partial Files Carefully
- Partial files may open but could be incomplete
- Try opening with multiple applications
- Some viewers can handle partial files better than others

### 4. Archive Manifest with Recovered Files
- Keep `manifest.json` with your recovered files
- It serves as an audit trail and recovery log
- Useful for forensic analysis or documentation

### 5. Sort by Quality, Not Quantity
- Don't be overwhelmed by file count
- Use validation scores to identify best candidates
- Partial files might still be recoverable by specialists

## Troubleshooting

### Why Are There Partial Files?
Partial files occur when:
- File was fragmented across non-contiguous sectors
- File was partially overwritten
- File deletion was interrupted
- Drive has bad sectors

### Can Partial Files Be Recovered?
- **Images (JPG/PNG)**: Often viewable even when partial (may show partial image)
- **Documents (PDF/DOCX)**: May open with errors or missing pages
- **Videos (MP4/AVI)**: Might play partially or not at all
- **Archives (ZIP/RAR)**: Usually unreadable when partial

### Why Do Some Files Have Low Scores?
Low scores indicate:
- Missing file structure elements
- Incomplete format validation
- Possible data corruption
- Fragmentation across multiple locations

### What If No High-Score Files Are Found?
1. **Try Different File Types**: Some types recover better than others
2. **Check Drive Health**: Bad sectors affect recovery quality
3. **Avoid Writing to Drive**: Further use reduces recovery chances
4. **Professional Recovery**: Consider data recovery services for critical data

## Command Reference

### View Manifest Summary
```powershell
# Windows PowerShell
$m = Get-Content recovered_files\manifest.json | ConvertFrom-Json
Write-Host "Total Files: $($m.statistics.total_files_recovered)"
Write-Host "Partial Files: $($m.statistics.partial_files)"
Write-Host "Total Size: $([math]::Round($m.statistics.total_size_bytes/1MB, 2)) MB"
```

### List All Files with Scores
```powershell
$m = Get-Content recovered_files\manifest.json | ConvertFrom-Json
$m.files | Select-Object filename, validation_score, is_partial | Format-Table
```

### Export High-Quality Files List
```powershell
$m = Get-Content recovered_files\manifest.json | ConvertFrom-Json
$m.files | Where-Object {$_.validation_score -ge 80} | 
    Export-Csv high_quality_files.csv -NoTypeInformation
```

### Calculate Recovery Success Rate
```powershell
$m = Get-Content recovered_files\manifest.json | ConvertFrom-Json
$totalFiles = $m.statistics.total_files_recovered
$highQuality = ($m.files | Where-Object {$_.validation_score -ge 70}).Count
$successRate = [math]::Round(($highQuality / $totalFiles) * 100, 1)
Write-Host "Recovery Success Rate: $successRate%"
```

## Tips for Better Recovery

1. **Stop Using the Drive Immediately** - Every write reduces recovery chances
2. **Scan as Soon as Possible** - Data becomes harder to recover over time
3. **Use File Type Filters** - Select only the types you need to reduce scan time
4. **Review Manifest First** - Don't manually check every file
5. **Prioritize by Score** - Focus on high-quality files (80+)
6. **Keep Original Files** - Don't delete low-score files until verified
7. **Document Recovery** - Keep manifest for audit trail

---

**For Technical Support**: See `PROFESSIONAL_CARVING_PHASE1.md` for implementation details.
