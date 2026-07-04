#!/usr/bin/env bash
set -euo pipefail

# Build AutoScope for Linux
# Requires Flutter, GTK, and build tools. See README for prerequisites.

echo "Building AutoScope for Linux..."

flet build linux --project autoscope --product "AutoScope" --yes --no-rich-output

echo "Build complete. Executable: build/linux/"
