# Video Downloader Extension

A powerful Chrome/Edge extension with local server for downloading videos from web pages, including support for streaming platforms and course platforms with protected content.

## Features

- **Universal Video Detection**: Automatically detects videos on any webpage
- **HLS/DASH Stream Support**: Downloads streaming videos (m3u8, mpd formats)
- **Course Platform Support**: Works with Hub.la, Código Viral, Hotmart, Eduzz, and other platforms using Cloudflare Stream
- **Native Messaging Integration**: Extension automatically controls local server
- **Desktop GUI**: Optional PySide6 interface for managing downloads
- **High Quality Downloads**: Merges best video + audio streams using FFmpeg
- **Audio Extraction**: Download videos as MP3 audio files
- **Real-time Progress**: See download progress in both extension popup and desktop GUI
- **Multiple Format Options**: MP4, WebM, MKV, MP3 with quality selection
- **Cookie-based Authentication**: Access videos from platforms requiring login

## Architecture

```
┌─────────────────┐     Native Messaging    ┌──────────────────┐
│  Chrome/Edge    │ ←──────────────────────→ │  Native Host     │
│  Extension      │                          │  (Python Bridge) │
└─────────────────┘                          └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │  Flask Server    │
                                             │  (yt-dlp +       │
                                             │   FFmpeg)        │
                                             └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │  PySide6 GUI     │
                                             │  (Optional)      │
                                             └──────────────────┘
```

**How it works:**
1. Extension detects videos on webpages via content script
2. Native messaging host bridges extension and local Flask server
3. Server uses yt-dlp + FFmpeg to download and process videos
4. Optional GUI provides visual progress tracking

## Prerequisites

### Required
- **Python 3.10 or higher** - [Download Python](https://www.python.org/downloads/)
- **Chrome, Edge, or Chromium** browser
- **FFmpeg** - Required for most downloads (see installation below)

### Optional
- **PySide6** - For desktop GUI interface

## Installation

### Step 1: Install FFmpeg

FFmpeg is **required** for:
- Merging video and audio streams (most modern sites provide separate streams)
- Converting videos to different formats
- Extracting audio as MP3
- Embedding metadata in downloaded files

**Without FFmpeg**, the downloader will fall back to single-stream downloads (lower quality) and many sites will fail to download.

#### macOS
```bash
# Using Homebrew (recommended)
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### Windows
**Option 1: Chocolatey (recommended)**
```powershell
choco install ffmpeg
```

**Option 2: Manual Installation**
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
2. Extract to `C:\ffmpeg\`
3. Add `C:\ffmpeg\bin` to System PATH:
   - Right-click "This PC" → Properties
   - Advanced system settings → Environment Variables
   - Edit "Path" variable → Add `C:\ffmpeg\bin`
4. Restart terminal and verify: `ffmpeg -version`

#### Linux
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg

# Verify installation
ffmpeg -version
```

### Step 2: Clone Repository

```bash
git clone https://github.com/lucasttnwork/Extention-Video-Audio-Downloader.git
cd Extention-Video-Audio-Downloader
```

### Step 3: Install Python Dependencies

```bash
# Install server dependencies (required)
cd server
pip3 install -r requirements.txt
cd ..

# Install GUI dependencies (optional)
cd gui
pip3 install -r requirements.txt
cd ..
```

**Server Dependencies:**
- yt-dlp (video download engine)
- Flask (web server)
- Flask-CORS (cross-origin support)
- browser-cookie3 (cookie extraction)
- requests (HTTP library)

**GUI Dependencies:**
- PySide6 (Qt6 interface)
- requests

### Step 4: Configure Environment (Optional)

This step is **only needed** if you want to download from authenticated course platforms.

```bash
# Copy template
cp .env.example .env

# Edit .env with your credentials
# macOS/Linux:
nano .env

# Windows:
notepad .env
```

**Important Notes:**
- `.env` is **only** for course platforms requiring login (Hub.la, Código Viral, Hotmart, etc.)
- Public sites (YouTube, TikTok, Twitter, Vimeo) work **without** any credentials
- Credentials are stored locally and never sent to external servers

### Step 5: Install Native Messaging Host

The native messaging host allows the extension to control the Flask server automatically.

#### macOS
```bash
cd native-host
./install_host.sh
```

#### Windows
```cmd
cd native-host
install_host.bat
```

#### Linux
```bash
cd native-host
chmod +x install_host_linux.sh
./install_host_linux.sh
```

The installer will:
- Create necessary directories for your browser
- Install the native messaging manifest
- Make scripts executable
- Display next steps

### Step 6: Install Chrome/Edge Extension

1. Open your browser and navigate to:
   - **Chrome**: `chrome://extensions/`
   - **Edge**: `edge://extensions/`

2. Enable **Developer mode** (toggle in top-right corner)

3. Click **Load unpacked**

4. Navigate to the project folder and select the `extension/` directory

5. The extension will load. **Copy the Extension ID** displayed under the extension name
   - Example: `abcdefghijklmnopqrstuvwxyz123456`

### Step 7: Configure Native Messaging

1. Open the native messaging manifest file:
   ```
   native-host/com.videodownloader.host.json
   ```

2. Replace the placeholders with your actual values:

   **Before:**
   ```json
   {
     "name": "com.videodownloader.host",
     "description": "Video Downloader Native Messaging Host",
     "path": "/ABSOLUTE/PATH/TO/YOUR/PROJECT/native-host/video_downloader_host.py",
     "type": "stdio",
     "allowed_origins": [
       "chrome-extension://YOUR_EXTENSION_ID_HERE/"
     ]
   }
   ```

   **After (example):**
   ```json
   {
     "name": "com.videodownloader.host",
     "description": "Video Downloader Native Messaging Host",
     "path": "/Users/yourname/Downloads/Extention-Video-Audio-Downloader/native-host/video_downloader_host.py",
     "type": "stdio",
     "allowed_origins": [
       "chrome-extension://abcdefghijklmnopqrstuvwxyz123456/"
     ]
   }
   ```

   **Windows users**: Use forward slashes `/` or double backslashes `\\`:
   ```json
   "path": "C:/Users/YourName/Downloads/Extention-Video-Audio-Downloader/native-host/video_downloader_host.py"
   ```

3. Save the file

### Step 8: Update Native Messaging Installation

After updating the manifest, re-run the installer to apply changes:

#### macOS/Linux
```bash
cd native-host
./install_host.sh    # macOS
# or
./install_host_linux.sh    # Linux
```

#### Windows
```cmd
cd native-host
install_host.bat
```

### Step 9: Reload Extension

1. Go back to `chrome://extensions/` or `edge://extensions/`
2. Click the reload icon (🔄) on your extension card

**Installation Complete!** 🎉

## Usage

### Basic Download Workflow

1. **Navigate to a video page**
   - Example: Go to a YouTube video

2. **Click the extension icon**
   - The popup will show detected videos
   - Badge shows number of videos found

3. **Start the server** (first time only)
   - Click "Start Server" button in popup
   - Server will start automatically in background

4. **Select video quality and format**
   - Choose from available quality options
   - Select output format (MP4, WebM, MKV, MP3)

5. **Click Download**
   - Video will be added to download queue
   - Progress shown in real-time

6. **Access downloads**
   - Default location: `~/Downloads/VideoDownloader/`
   - Click "Open Folder" in popup to view files

### Using the Desktop GUI (Optional)

The GUI provides a dedicated interface for managing downloads:

```bash
cd gui
python3 main.py
```

**GUI Features:**
- Real-time progress bars with speed and ETA
- Download history
- Server status indicator (green = running, red = stopped)
- System tray integration (minimize to tray)
- Desktop notifications on completion
- Manual URL input for direct downloads

### Supported Platforms

**General Video Sites** (via yt-dlp):
- YouTube, YouTube Music
- TikTok, Instagram, Facebook, Twitter/X
- Vimeo, Dailymotion, Twitch
- Reddit, Imgur
- And 1000+ more sites

**Streaming Formats:**
- HLS streams (`.m3u8` playlists)
- DASH streams (`.mpd` manifests)
- Direct video files (MP4, WebM, MOV)

**Course Platforms** (requires authentication):
- Hub.la (hub.la, app.hub.la)
- Código Viral (codigoviral.com.br)
- Hotmart (hotmart.com)
- Eduzz (eduzz.com)
- Kiwify (kiwify.com.br)
- Monetizze (monetizze.com.br)
- Area de Membros (areademembros.com)

**Special Stream Handlers:**
- Cloudflare Stream (JWT-protected videos)
- SmartPlayer.io (separate audio/video streams)
- ScaleUp (playlist streams)

## Project Structure

```
Extention-Video-Audio-Downloader/
├── extension/              # Chrome extension (Manifest V3)
│   ├── manifest.json       # Extension configuration
│   ├── icons/              # Extension icons (16-128px)
│   └── src/
│       ├── background/     # Service worker (background processing)
│       ├── content/        # Content script (video detection)
│       └── popup/          # Extension popup UI
│
├── native-host/            # Native messaging bridge
│   ├── video_downloader_host.py        # Bridge script
│   ├── com.videodownloader.host.json   # Manifest file
│   ├── install_host.sh                 # macOS installer
│   ├── install_host.bat                # Windows installer
│   ├── install_host_linux.sh           # Linux installer
│   └── README.md                       # Native host docs
│
├── server/                 # Flask download server
│   ├── app.py              # Flask application
│   ├── config.py           # Configuration
│   ├── requirements.txt    # Python dependencies
│   └── core/
│       ├── downloader.py          # yt-dlp wrapper
│       ├── download_manager.py    # Queue management
│       ├── auth_handler.py        # Cookie handling
│       └── extractors/            # Custom extractors
│           ├── base.py            # Base extractor class
│           └── hubla.py           # Course platform extractor
│
├── gui/                    # Desktop interface (optional)
│   ├── main.py             # GUI entry point
│   ├── requirements.txt    # GUI dependencies
│   └── windows/
│       └── main_window.py  # Main window implementation
│
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Troubleshooting

### Extension shows "Native host not found"

**Symptoms:** Extension displays an error about native host connection failure.

**Causes & Solutions:**

1. **Extension ID mismatch**
   - Open `chrome://extensions/`
   - Copy the actual Extension ID
   - Update `native-host/com.videodownloader.host.json` with the correct ID
   - Re-run the native host installer

2. **Path is incorrect**
   - Verify the `path` in `com.videodownloader.host.json` points to the actual location
   - Use absolute paths, not relative
   - Windows: Use forward slashes `/` or double backslashes `\\`

3. **Manifest not installed**
   - **macOS**: Check `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/`
   - **Windows**: Check `%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts\`
   - **Linux**: Check `~/.config/google-chrome/NativeMessagingHosts/`
   - Re-run the installer if missing

4. **Script not executable** (macOS/Linux)
   ```bash
   chmod +x native-host/video_downloader_host.py
   ```

### Server fails to start

**Symptoms:** Clicking "Start Server" shows error or nothing happens.

**Solutions:**

1. **Python not found**
   ```bash
   # Check Python installation
   python3 --version

   # Should show 3.10 or higher
   ```
   If not installed, see Prerequisites section.

2. **Dependencies not installed**
   ```bash
   cd server
   pip3 install -r requirements.txt
   ```

3. **Port 5050 already in use**
   ```bash
   # macOS/Linux: Check what's using port 5050
   lsof -i :5050

   # Windows: Check port usage
   netstat -ano | findstr :5050
   ```
   Kill the process or change the port in `server/config.py`.

4. **Test server manually**
   ```bash
   cd server
   python3 app.py
   ```
   Check console output for errors.

### Downloads fail with "FFmpeg not found"

**Symptoms:** Downloads fail or show FFmpeg errors.

**Impact without FFmpeg:**
- Cannot merge separate video + audio streams (most sites)
- Cannot convert to different formats
- Cannot extract MP3 audio
- Many downloads will fail completely

**Solutions:**

1. **Install FFmpeg** (see Installation section above)

2. **Verify FFmpeg is in PATH**
   ```bash
   ffmpeg -version
   ```

3. **Specify FFmpeg location manually**
   Edit `.env` and add:
   ```env
   FFMPEG_LOCATION=/path/to/ffmpeg/bin/ffmpeg
   ```

4. **Restart server after installing FFmpeg**

### Downloads are slow or stuck

**Solutions:**

1. **Check internet connection**
   - Some sites rate-limit downloads
   - Try a different time of day

2. **Reduce concurrent downloads**
   Edit `.env`:
   ```env
   MAX_CONCURRENT_DOWNLOADS=1
   ```

3. **Check download progress**
   - Open GUI to see detailed progress
   - Check server console for errors

4. **Server logs**
   ```bash
   cd server
   python3 app.py
   ```
   Monitor console output while downloading.

### Course platform downloads fail

**Symptoms:** Downloads from Hub.la, Código Viral, etc. fail with authentication errors.

**Solutions:**

1. **Configure credentials**
   - Ensure `.env` file exists with correct credentials
   - Verify you're logged into the course platform in your browser

2. **Cookie extraction**
   - The extension extracts cookies automatically
   - Make sure you're on the course video page when downloading

3. **JWT token expired**
   - Some platforms use short-lived tokens
   - Reload the course page and try again immediately

4. **Platform-specific issues**
   - Ensure the platform is supported (see Supported Platforms)
   - Check if the video is actually downloadable (some use DRM)

### "Permission denied" error (macOS)

**Cause:** macOS Gatekeeper blocking Python script execution.

**Solutions:**

1. **Allow in Security & Privacy**
   - Go to **System Preferences** → **Security & Privacy**
   - Click "Allow" for the blocked application

2. **Make script executable**
   ```bash
   chmod +x native-host/video_downloader_host.py
   ```

3. **Disable Gatekeeper temporarily** (not recommended)
   ```bash
   sudo spctl --master-disable
   ```

### Extension not detecting videos

**Solutions:**

1. **Refresh the page**
   - Click the refresh button in extension popup
   - Or reload the webpage

2. **Check content script**
   - Open browser console (F12)
   - Look for any JavaScript errors

3. **Supported formats**
   - Extension detects `<video>` elements, m3u8, mpd, MP4 URLs
   - Blob URLs and data URLs are not supported
   - Some sites use proprietary players that can't be detected

4. **Try manual URL input**
   - Copy video URL
   - Use GUI's manual input field

## FAQ

### Is this legal?

This tool is for **personal use only**. You must:
- Only download content you have permission to download
- Respect copyright laws in your country
- Follow the terms of service of the websites you download from
- For course platforms: Only download courses you have purchased or have legitimate access to

**The developers are not responsible for misuse of this tool.**

### Why does it need credentials for course platforms?

Many online course platforms (Hub.la, Código Viral, Hotmart) protect their videos with authentication. The credentials are:
- **Stored locally** in your `.env` file on your computer
- **Never sent** to any external server except the course platform's own authentication servers
- **Not required** for public sites like YouTube, TikTok, Twitter
- **Only used** to authenticate with the course platform you have access to

This is similar to logging into the website manually in your browser.

### Does the server send data externally?

**No.** The Flask server runs **entirely on your local machine** (`127.0.0.1:5050`). All downloads are:
- Processed locally using yt-dlp
- Saved to your local Downloads folder
- **No data is sent** to any external server (except the video source itself to download the file)

This is a completely local, privacy-focused solution.

### Can I use this on multiple browsers?

**Yes!** The installation scripts support:
- **macOS**: Chrome, Chromium, Edge
- **Windows**: Chrome, Edge
- **Linux**: Chrome, Chromium, Brave

To use on multiple browsers:
1. Load the extension in each browser
2. Copy each browser's Extension ID
3. Add all Extension IDs to `allowed_origins` in the manifest:
   ```json
   "allowed_origins": [
     "chrome-extension://CHROME_ID_HERE/",
     "chrome-extension://EDGE_ID_HERE/"
   ]
   ```
4. Re-run the native host installer for each browser

### Why are there FFmpeg binaries in the repo?

**Note:** The current repository includes FFmpeg binaries for convenience, but:
- These are large files (~150MB total)
- It's **recommended** to install FFmpeg via package manager instead
- The system auto-detects system-installed FFmpeg first
- You can safely ignore or delete `server/bin/` after installing FFmpeg system-wide

The binaries are provided as a fallback for users who have trouble installing FFmpeg.

### How do I update yt-dlp?

yt-dlp is updated frequently to support site changes:

```bash
cd server
pip3 install --upgrade yt-dlp
```

It's recommended to update yt-dlp every few weeks, especially if a site stops working.

### Where are downloads saved?

**Default location:** `~/Downloads/VideoDownloader/`

To change:
1. Edit `.env` file
2. Set `DOWNLOAD_DIR=/path/to/your/folder`
3. Restart server

### Can I download from YouTube?

**Yes!** yt-dlp supports YouTube, including:
- Standard videos
- YouTube Music
- Live streams
- Playlists (use manual URL input)
- Age-restricted videos
- High-quality formats (4K, 8K with FFmpeg)

### Why can't I download some videos?

Some videos cannot be downloaded because:
1. **DRM protection** (Netflix, Amazon Prime, Disney+, etc.)
2. **Blob/Data URLs** (video generated in browser)
3. **Platform restrictions** (site actively blocks downloaders)
4. **Private videos** (requires specific authentication we don't support)
5. **Live streams** (some formats not supported)

**Tip:** If a video doesn't work, try:
- Refreshing the page
- Checking if yt-dlp supports that site: [Supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- Updating yt-dlp: `pip3 install --upgrade yt-dlp`

## Development

### Running Server Manually

For development or debugging:

```bash
cd server
export FLASK_DEBUG=true  # Enable debug mode
python3 app.py
```

Server will run on `http://127.0.0.1:5050`

### API Endpoints

The Flask server exposes the following REST API:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Server health check + active downloads count |
| POST | `/api/download` | Start new download |
| GET | `/api/download/<id>` | Get specific download status |
| GET | `/api/queue` | List all downloads in queue |
| POST | `/api/download/<id>/cancel` | Cancel active download |
| DELETE | `/api/download/<id>` | Remove completed/cancelled download |
| POST | `/api/clear` | Clear all completed downloads |
| POST | `/api/info` | Get video info without downloading |
| POST | `/api/open-folder` | Open downloads folder in file manager |

**Example download request:**
```json
POST /api/download
{
  "url": "https://youtube.com/watch?v=...",
  "title": "Optional custom title",
  "format": "best",
  "outputFormat": "mp4",
  "cookies": [...],
  "videoUrl": "optional extracted video URL"
}
```

### Testing Extension Changes

1. Make changes to extension code
2. Go to `chrome://extensions/`
3. Click reload icon (🔄) on the extension card
4. Test on a video page

### Adding Custom Extractors

To add support for new platforms:

1. Create new extractor in `server/core/extractors/`:
   ```python
   from .base import BaseExtractor, ExtractorResult

   class MyPlatformExtractor(BaseExtractor):
       def matches(self, url):
           return 'myplatform.com' in url

       def extract(self, url, cookies=None):
           # Extraction logic
           return ExtractorResult(...)
   ```

2. Register in `server/core/extractors/__init__.py`

3. Test with your platform's URLs

## Contributing

Contributions are welcome! To contribute:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Make your changes**
4. **Test thoroughly** on your platform
5. **Commit your changes** (`git commit -m 'Add AmazingFeature'`)
6. **Push to the branch** (`git push origin feature/AmazingFeature`)
7. **Open a Pull Request**

Please ensure:
- Code follows existing style
- All features are tested
- Documentation is updated
- No sensitive data (credentials, API keys) in commits

## License

[Specify your license here - e.g., MIT, GPL-3.0, etc.]

## Credits

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video download engine supporting 1000+ sites
- [FFmpeg](https://ffmpeg.org/) - Media processing and conversion
- [Flask](https://flask.palletsprojects.com/) - Lightweight web server framework
- [PySide6](https://wiki.qt.io/Qt_for_Python) - Qt6 Python bindings for desktop GUI
- [browser-cookie3](https://github.com/borisbabic/browser_cookie3) - Browser cookie extraction

## Support

If you encounter issues:

1. **Check Troubleshooting section** above
2. **Review console logs**:
   - Extension: F12 → Console
   - Server: Terminal output
3. **Open a GitHub Issue** with:
   - Your OS and version (macOS 14, Windows 11, Ubuntu 22.04, etc.)
   - Python version (`python3 --version`)
   - FFmpeg version (`ffmpeg -version`)
   - Browser and extension version
   - Extension ID
   - Error messages from console/terminal
   - Steps to reproduce

## Changelog

### Version 1.0.0 (Initial Release)
- Chrome/Edge Extension with Manifest V3
- Native messaging host integration
- Flask server with yt-dlp + FFmpeg
- PySide6 desktop GUI
- Support for 1000+ sites via yt-dlp
- Custom extractors for course platforms
- Cloudflare Stream support
- SmartPlayer and ScaleUp stream handling
- Real-time download progress tracking
- MP3 audio extraction
- Cookie-based authentication
- Cross-platform support (macOS, Windows, Linux)

---

**Enjoy downloading! 🎬**

For updates, follow the repository: https://github.com/lucasttnwork/Extention-Video-Audio-Downloader
