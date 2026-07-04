# Build AutoScope for Windows
# Run in PowerShell on a Windows machine with Visual Studio and Flutter installed.

Write-Host "Building AutoScope for Windows..."

flet build windows --project autoscope --product "AutoScope"

Write-Host "Build complete. Installer/output: build/windows/"
