#!/bin/bash
# Installation script for Native Messaging Host on Linux

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST_NAME="com.videodownloader.host"
MANIFEST_FILE="$SCRIPT_DIR/$HOST_NAME.json"
HOST_SCRIPT="$SCRIPT_DIR/video_downloader_host.py"

# Native Messaging Hosts directories for different browsers
CHROME_NM_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
CHROMIUM_NM_DIR="$HOME/.config/chromium/NativeMessagingHosts"
BRAVE_NM_DIR="$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"

echo "======================================"
echo "Video Downloader Native Host Installer"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    echo "✓ Python 3 found: $PYTHON_VERSION"

    # Check if version is 3.10 or higher
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        echo "✗ WARNING: Python 3.10 or higher is recommended"
        echo "  Your version: $PYTHON_VERSION"
    fi
else
    echo "✗ ERROR: Python 3 not found!"
    echo "  Please install Python 3.10 or higher"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Fedora:        sudo dnf install python3 python3-pip"
    echo "  Arch:          sudo pacman -S python python-pip"
    exit 1
fi

echo ""

# Make the host script executable
echo "Making host script executable..."
chmod +x "$HOST_SCRIPT"

# Detect which browsers are installed and install for them
echo "Detecting installed browsers..."
INSTALLED_BROWSERS=()

if [ -d "$HOME/.config/google-chrome" ] || command -v google-chrome &> /dev/null; then
    mkdir -p "$CHROME_NM_DIR"
    ln -sf "$MANIFEST_FILE" "$CHROME_NM_DIR/$HOST_NAME.json"
    INSTALLED_BROWSERS+=("Chrome")
    echo "  ✓ Google Chrome detected"
fi

if [ -d "$HOME/.config/chromium" ] || command -v chromium &> /dev/null || command -v chromium-browser &> /dev/null; then
    mkdir -p "$CHROMIUM_NM_DIR"
    ln -sf "$MANIFEST_FILE" "$CHROMIUM_NM_DIR/$HOST_NAME.json"
    INSTALLED_BROWSERS+=("Chromium")
    echo "  ✓ Chromium detected"
fi

if [ -d "$HOME/.config/BraveSoftware" ] || command -v brave &> /dev/null || command -v brave-browser &> /dev/null; then
    mkdir -p "$BRAVE_NM_DIR"
    ln -sf "$MANIFEST_FILE" "$BRAVE_NM_DIR/$HOST_NAME.json"
    INSTALLED_BROWSERS+=("Brave")
    echo "  ✓ Brave detected"
fi

echo ""

if [ ${#INSTALLED_BROWSERS[@]} -eq 0 ]; then
    echo "✗ WARNING: No supported browsers detected"
    echo "  The installer will create directories anyway"
    echo "  Install Chrome, Chromium, or Brave to use this extension"
    echo ""
    # Create at least the Chrome directory
    mkdir -p "$CHROME_NM_DIR"
    ln -sf "$MANIFEST_FILE" "$CHROME_NM_DIR/$HOST_NAME.json"
fi

echo "✓ Native Messaging Host installed successfully!"
echo ""

if [ ${#INSTALLED_BROWSERS[@]} -gt 0 ]; then
    echo "Installed for: ${INSTALLED_BROWSERS[@]}"
    echo ""
fi

echo "Manifest linked to:"
[ -L "$CHROME_NM_DIR/$HOST_NAME.json" ] && echo "  - Chrome:     $CHROME_NM_DIR/$HOST_NAME.json"
[ -L "$CHROMIUM_NM_DIR/$HOST_NAME.json" ] && echo "  - Chromium:   $CHROMIUM_NM_DIR/$HOST_NAME.json"
[ -L "$BRAVE_NM_DIR/$HOST_NAME.json" ] && echo "  - Brave:      $BRAVE_NM_DIR/$HOST_NAME.json"

echo ""
echo "======================================"
echo "IMPORTANT NEXT STEPS:"
echo "======================================"
echo ""
echo "1. Load the extension in your browser:"
echo "   - Chrome:    chrome://extensions/"
echo "   - Chromium:  chromium://extensions/"
echo "   - Brave:     brave://extensions/"
echo "   - Enable 'Developer mode'"
echo "   - Click 'Load unpacked'"
echo "   - Select: $(dirname "$SCRIPT_DIR")/extension/"
echo ""
echo "2. Copy the Extension ID (looks like: abcdefghijklmnopqrstuvwxyz123456)"
echo ""
echo "3. Update the manifest file:"
echo "   Edit: $MANIFEST_FILE"
echo "   Replace placeholders with your actual values:"
echo "     - YOUR_EXTENSION_ID_HERE → your Extension ID"
echo "     - /ABSOLUTE/PATH/TO/YOUR/PROJECT → actual project path"
echo ""
echo "4. Run this installer script again to update the symlinks:"
echo "   ./install_host_linux.sh"
echo ""
echo "5. Reload the extension in your browser"
echo ""
echo "Done!"
echo ""
