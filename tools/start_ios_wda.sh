#!/usr/bin/env bash
set -euo pipefail

# One-time helper: build and launch WebDriverAgent (WDA) against the
# currently booted iOS Simulator, so IOSDriver can connect to it over HTTP.
#
# WDA is not vendored in this repo -- it's a full Xcode project with a
# multi-minute first build -- so this script clones it once into a cache
# directory (~/.autoscope/WebDriverAgent by default) and rebuilds only when
# that directory doesn't already exist. Requires Xcode command line tools
# and a booted Simulator (Simulator.app -> Device -> boot one first).
#
# For real devices, WDA needs code signing and USB tunneling; use `tidevice`
# instead (see README's iOS section) -- this script is Simulator-only.

WDA_DIR="${WDA_CACHE_DIR:-$HOME/.autoscope/WebDriverAgent}"
WDA_PORT="${WDA_PORT:-8100}"

UDID=$(xcrun simctl list devices | grep -m1 "(Booted)" | grep -oE '[0-9A-Fa-f-]{36}' || true)
if [ -z "$UDID" ]; then
    echo "No booted iOS Simulator found. Open Simulator.app and boot a device first." >&2
    exit 1
fi
echo "Target simulator: $UDID"

if [ ! -d "$WDA_DIR" ]; then
    echo "Cloning WebDriverAgent into $WDA_DIR ..."
    git clone --depth 1 https://github.com/appium/WebDriverAgent.git "$WDA_DIR"
fi

if curl -s --max-time 3 "http://localhost:$WDA_PORT/status" > /dev/null 2>&1; then
    echo "WebDriverAgent already running at http://localhost:$WDA_PORT"
    exit 0
fi

echo "Building and launching WebDriverAgent (this can take a few minutes on first run)..."
cd "$WDA_DIR"
nohup xcodebuild -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner \
    -destination "id=$UDID" test > /tmp/autoscope_wda.log 2>&1 &
echo $! > /tmp/autoscope_wda.pid

echo "Waiting for WebDriverAgent to come up on port $WDA_PORT..."
for _ in $(seq 1 90); do
    if curl -s --max-time 3 "http://localhost:$WDA_PORT/status" > /dev/null 2>&1; then
        echo "WebDriverAgent is ready at http://localhost:$WDA_PORT"
        exit 0
    fi
    sleep 2
done

echo "Timed out waiting for WebDriverAgent. Check /tmp/autoscope_wda.log" >&2
exit 1
