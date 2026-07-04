# Build AutoScope for Windows
# Run in PowerShell on a Windows machine with Visual Studio and Flutter installed.

# Avoid cp1252 UnicodeEncodeError in CI/console hosts when flet prints progress chars.
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Building AutoScope for Windows..."

flet build windows --project autoscope --product "AutoScope" --yes --no-rich-output

Write-Host "Build complete. Installer/output: build/windows/"
