# Refresh PATH Environment Variable
# Run this script if smartctl command is not found after installation

Write-Host "Refreshing PATH environment variable..." -ForegroundColor Cyan

# Get the Machine and User PATH
$machinePath = [System.Environment]::GetEnvironmentVariable("Path","Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path","User")

# Combine them
$env:Path = $machinePath + ";" + $userPath

Write-Host "✓ PATH refreshed successfully!" -ForegroundColor Green
Write-Host ""

# Test if smartctl is now available
Write-Host "Testing smartctl..." -ForegroundColor Cyan
try {
    $version = & smartctl --version 2>&1
    if ($LASTEXITCODE -eq 0 -or $version -match "smartctl") {
        Write-Host "✓ smartctl is working!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Available drives:" -ForegroundColor Yellow
        & smartctl --scan
    } else {
        Write-Host "✗ smartctl not found in PATH" -ForegroundColor Red
        Write-Host "  Make sure smartmontools is installed and added to PATH" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ smartctl not found" -ForegroundColor Red
    Write-Host "  Install from: https://www.smartmontools.org/" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Note: This refresh is temporary for this terminal session." -ForegroundColor Yellow
Write-Host "To make it permanent, restart VS Code or your terminal." -ForegroundColor Yellow
