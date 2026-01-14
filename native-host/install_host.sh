#!/bin/bash
# Installation script for Native Messaging Host on macOS

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST_NAME="com.videodownloader.host"
MANIFEST_FILE="$SCRIPT_DIR/$HOST_NAME.json"
HOST_SCRIPT="$SCRIPT_DIR/video_downloader_host.py"

# Chrome Native Messaging Hosts directory (user-level)
CHROME_NM_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"

# Chromium Native Messaging Hosts directory
CHROMIUM_NM_DIR="$HOME/Library/Application Support/Chromium/NativeMessagingHosts"

echo "======================================"
echo "Video Downloader Native Host Installer"
echo "======================================"
echo ""

# Make the host script executable
echo "Making host script executable..."
chmod +x "$HOST_SCRIPT"

# Create directories if they don't exist
echo "Creating Native Messaging directories..."
mkdir -p "$CHROME_NM_DIR"
mkdir -p "$CHROMIUM_NM_DIR"

# Create symlinks to the manifest
echo "Installing manifest..."
ln -sf "$MANIFEST_FILE" "$CHROME_NM_DIR/$HOST_NAME.json"
ln -sf "$MANIFEST_FILE" "$CHROMIUM_NM_DIR/$HOST_NAME.json"

echo ""
echo "✓ Native Messaging Host installed successfully!"
echo ""
echo "Manifest linked to:"
echo "  - Chrome:   $CHROME_NM_DIR/$HOST_NAME.json"
echo "  - Chromium: $CHROMIUM_NM_DIR/$HOST_NAME.json"
echo ""
echo "======================================"
echo "IMPORTANT NEXT STEPS:"
echo "======================================"
echo ""
echo "1. Load the extension in Chrome:"
echo "   - Open chrome://extensions/"
echo "   - Enable 'Developer mode'"
echo "   - Click 'Load unpacked'"
echo "   - Select: $(dirname "$SCRIPT_DIR")/extension/"
echo ""
echo "2. Copy the Extension ID (it looks like: abcdefghijklmnopqrstuvwxyz123456)"
echo ""
echo "3. Update the manifest with your Extension ID:"
echo "   Edit: $MANIFEST_FILE"
echo "   Replace 'EXTENSION_ID_PLACEHOLDER' with your actual Extension ID"
echo ""
echo "4. Reload the extension in Chrome"
echo ""
echo "Done!"
