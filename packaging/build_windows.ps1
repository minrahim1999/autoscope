# Build AutoScope for Windows
# Run in PowerShell on a Windows machine with Visual Studio and Flutter installed.

# Avoid cp1252 UnicodeEncodeError in CI/console hosts when flet prints progress chars.
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "UTF-8"

Write-Host "Building AutoScope for Windows..."

# Pipe flet build output to a log file so rich doesn't write spinner chars to the
# legacy Windows console, which crashes with cp1252 on hosted runners.
flet build windows --project autoscope --product "AutoScope" --yes --no-rich-output | Tee-Object -FilePath "flet-build.log" | Write-Host

if ($LASTEXITCODE -ne 0) {
    Write-Host "flet build failed (exit $LASTEXITCODE). Log:"
    Get-Content "flet-build.log" -ErrorAction SilentlyContinue | Write-Host
    exit $LASTEXITCODE
}

Write-Host "Build complete. Installer/output: build/windows/"
