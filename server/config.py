"""
Server configuration settings.
"""
import os
from pathlib import Path

# Server settings
HOST = "127.0.0.1"
PORT = 5050
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# Download settings
DOWNLOAD_DIR = Path(os.environ.get(
    "DOWNLOAD_DIR",
    Path.home() / "Downloads" / "VideoDownloader"
))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Queue settings
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", 3))

# FFmpeg settings
# Try environment variable first, then known locations
_BASE_DIR = Path(__file__).parent
_FFMPEG_DIRS = [
    os.environ.get("FFMPEG_LOCATION"),
    str(_BASE_DIR / "bin"),  # Local bin directory
    "/opt/homebrew/bin",
    "/usr/local/bin",
]

def _find_ffmpeg():
    """Find ffmpeg directory that has both ffmpeg and ffprobe."""
    for path in _FFMPEG_DIRS:
        if not path:
            continue
        # If path is a file, get its directory
        if os.path.isfile(path):
            path = os.path.dirname(path)
        ffmpeg = os.path.join(path, "ffmpeg")
        ffprobe = os.path.join(path, "ffprobe")
        if os.path.isfile(ffmpeg) and os.path.isfile(ffprobe):
            return path
    return None

FFMPEG_LOCATION = _find_ffmpeg()
FFMPEG_AVAILABLE = FFMPEG_LOCATION is not None

# yt-dlp settings - adjust based on ffmpeg availability
if FFMPEG_AVAILABLE:
    # Full quality with merging when ffmpeg is available
    # Using flexible format selection that works with YouTube's new SABR streaming
    YTDLP_OPTIONS = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",  # More flexible format selection
        "merge_output_format": "mp4",
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "restrictfilenames": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_LOCATION,
        "postprocessors": [
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            },
        ],
    }
else:
    # Fallback: single stream format when ffmpeg not available
    YTDLP_OPTIONS = {
        "format": "b[ext=mp4]/b",  # Best single stream
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "restrictfilenames": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

# CORS settings - allow extension origin
CORS_ORIGINS = [
    "chrome-extension://*",
    "moz-extension://*",
]

# Temporary cookie storage
TEMP_COOKIE_DIR = Path("/tmp/video_downloader_cookies")
TEMP_COOKIE_DIR.mkdir(parents=True, exist_ok=True)

# Audio (MP3) extraction options - requires FFmpeg
if FFMPEG_AVAILABLE:
    YTDLP_AUDIO_OPTIONS = {
        "format": "ba[ext=m4a]/ba/b",  # Best audio, flexible selection
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "restrictfilenames": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_LOCATION,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            },
        ],
    }
else:
    YTDLP_AUDIO_OPTIONS = None  # MP3 extraction not available without FFmpeg
