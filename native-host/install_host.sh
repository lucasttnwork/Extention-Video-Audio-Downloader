#!/bin/bash
# Installation script for Native Messaging Host on macOS

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST_NAME="com.videodownloader.host"
MANIFEST_FILE="$SCRIPT_DIR/$HOST_NAME.json"
HOST_SCRIPT="$SCRIPT_DIR/video_downloader_host.py"

# Native Messaging Hosts directories (user-level)
CHROME_NM_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
CHROMIUM_NM_DIR="$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
EDGE_NM_DIR="$HOME/Library/Application Support/Microsoft Edge/NativeMessagingHosts"

echo "======================================"
echo "Video Downloader Native Host Installer"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✓ Python 3 found: $PYTHON_VERSION"
else
    echo "✗ ERROR: Python 3 not found!"
    echo "  Please install Python 3.10 or higher"
    exit 1
fi

# Make the host script executable
echo "Making host script executable..."
chmod +x "$HOST_SCRIPT"

# Create directories if they don't exist
echo "Creating Native Messaging directories..."
mkdir -p "$CHROME_NM_DIR"
mkdir -p "$CHROMIUM_NM_DIR"
mkdir -p "$EDGE_NM_DIR"

# Create symlinks to the manifest
echo "Installing manifest..."
ln -sf "$MANIFEST_FILE" "$CHROME_NM_DIR/$HOST_NAME.json"
ln -sf "$MANIFEST_FILE" "$CHROMIUM_NM_DIR/$HOST_NAME.json"
ln -sf "$MANIFEST_FILE" "$EDGE_NM_DIR/$HOST_NAME.json"

echo ""
echo "✓ Native Messaging Host installed successfully!"
echo ""
echo "Manifest linked to:"
echo "  - Chrome:     $CHROME_NM_DIR/$HOST_NAME.json"
echo "  - Chromium:   $CHROMIUM_NM_DIR/$HOST_NAME.json"
echo "  - Edge:       $EDGE_NM_DIR/$HOST_NAME.json"
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
echo "3. Update the manifest file:"
echo "   Edit: $MANIFEST_FILE"
echo "   Replace placeholders with your actual values:"
echo "     - YOUR_EXTENSION_ID_HERE → your Extension ID"
echo "     - /ABSOLUTE/PATH/TO/YOUR/PROJECT → actual project path"
echo ""
echo "4. Run this installer script again to update the symlinks:"
echo "   ./install_host.sh"
echo ""
echo "5. Reload the extension in Chrome"
echo ""
echo "Done!"
