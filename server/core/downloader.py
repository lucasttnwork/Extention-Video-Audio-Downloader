"""
yt-dlp wrapper with progress callbacks.
"""
import logging
import subprocess
import yt_dlp
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import config

logger = logging.getLogger('video_downloader.downloader')


def is_smartplayer_url(url: str) -> bool:
    """Check if URL is from SmartPlayer/ScaleUp (requires special audio handling)."""
    lower = url.lower()
    return 'smartplayer.io' in lower or 'scaleup.com.br' in lower


def get_smartplayer_audio_url(video_url: str) -> str:
    """Convert SmartPlayer video URL to audio URL.

    SmartPlayer uses separate streams:
    - Video: *_720p.mp4, *_480p.mp4, etc.
    - Audio: *_en_192k.mp4

    We replace the quality suffix with the audio suffix.
    """
    import re
    # Pattern: match _XXXp or _XXX before .mp4 at the end
    pattern = r'_(\d+p)\.mp4'
    audio_url = re.sub(pattern, '_en_192k.mp4', video_url)

    # Also handle m3u8 if needed
    if audio_url == video_url:
        pattern = r'_(\d+p)\.m3u8'
        audio_url = re.sub(pattern, '_en_192k.m3u8', video_url)

    return audio_url


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    total_bytes: int = 0
    downloaded_bytes: int = 0
    error: str = ""


@dataclass
class DownloadResult:
    success: bool
    filename: str = ""
    filepath: str = ""
    title: str = ""
    duration: int = 0
    error: str = ""


class Downloader:
    """Wrapper for yt-dlp with progress tracking."""

    def __init__(
        self,
        url: str,
        output_dir: Optional[Path] = None,
        format_id: Optional[str] = None,
        cookies: Optional[dict] = None,
        cookie_file: Optional[str] = None,
        audio_only: bool = False,
    ):
        self.url = url
        self.output_dir = output_dir or config.DOWNLOAD_DIR
        self.format_id = format_id
        self.cookies = cookies
        self.cookie_file = cookie_file
        self.audio_only = audio_only
        self.progress = DownloadProgress()
        self._cancelled = False
        self._progress_callback: Optional[Callable[[DownloadProgress], None]] = None

    def set_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """Set callback function for progress updates."""
        self._progress_callback = callback

    def cancel(self):
        """Cancel the download."""
        self._cancelled = True
        self.progress.status = DownloadStatus.CANCELLED

    def _progress_hook(self, d: dict):
        """Hook called by yt-dlp during download."""
        if self._cancelled:
            raise Exception("Download cancelled")

        status = d.get("status", "")

        if status == "downloading":
            self.progress.status = DownloadStatus.DOWNLOADING
            self.progress.filename = d.get("filename", "")
            self.progress.total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            self.progress.downloaded_bytes = d.get("downloaded_bytes", 0)
            self.progress.speed = d.get("_speed_str", "")
            self.progress.eta = d.get("_eta_str", "")

            if self.progress.total_bytes > 0:
                self.progress.progress = (
                    self.progress.downloaded_bytes / self.progress.total_bytes * 100
                )

        elif status == "finished":
            self.progress.status = DownloadStatus.PROCESSING
            self.progress.progress = 100.0

        if self._progress_callback:
            self._progress_callback(self.progress)

    def _postprocessor_hook(self, d: dict):
        """Hook called by yt-dlp during post-processing."""
        status = d.get("status")
        if status == "started":
            self.progress.status = DownloadStatus.PROCESSING
            if self._progress_callback:
                self._progress_callback(self.progress)
        elif status == "finished":
            # Post-processing finished - notify UI
            if self._progress_callback:
                self._progress_callback(self.progress)

    def get_info(self) -> dict:
        """Get video info without downloading."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        if self.cookie_file:
            ydl_opts["cookiefile"] = self.cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(self.url, download=False)

    def _convert_to_mp3(self, video_path: Path) -> Optional[Path]:
        """Convert video file to MP3 using ffmpeg directly."""
        if not config.FFMPEG_AVAILABLE:
            logger.error("  FFmpeg not available for MP3 conversion")
            return None

        import sys
        mp3_path = video_path.with_suffix(".mp3")
        exe_suffix = ".exe" if sys.platform == "win32" else ""
        ffmpeg_path = Path(config.FFMPEG_LOCATION) / f"ffmpeg{exe_suffix}"

        logger.info(f"  Converting to MP3: {video_path.name} -> {mp3_path.name}")

        try:
            cmd = [
                str(ffmpeg_path),
                "-i", str(video_path),
                "-vn",  # No video
                "-acodec", "libmp3lame",
                "-ab", "192k",
                "-y",  # Overwrite
                str(mp3_path)
            ]
            logger.info(f"  FFmpeg command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0 and mp3_path.exists():
                logger.info(f"  MP3 conversion successful: {mp3_path.name}")
                # Remove original video file
                video_path.unlink()
                logger.info(f"  Removed original file: {video_path.name}")
                return mp3_path
            else:
                logger.error(f"  FFmpeg error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("  FFmpeg conversion timed out")
            return None
        except Exception as e:
            logger.error(f"  FFmpeg conversion failed: {e}")
            return None

    def download(self) -> DownloadResult:
        """Execute the download and return result."""
        download_url = self.url
        logger.info(f"Starting download: {self.url[:100]}...")
        logger.info(f"  Audio only: {self.audio_only}")
        logger.info(f"  Cookie file: {self.cookie_file}")
        logger.info(f"  Output dir: {self.output_dir}")

        # Check if SmartPlayer URL needs special audio handling
        is_smartplayer = is_smartplayer_url(self.url)
        use_manual_mp3_conversion = self.audio_only and is_smartplayer

        if use_manual_mp3_conversion:
            # SmartPlayer separates video and audio streams
            # For MP3, download the audio stream directly (it's a separate file)
            audio_url = get_smartplayer_audio_url(self.url)
            if audio_url != self.url:
                download_url = audio_url
                logger.info(f"  SmartPlayer: Using audio stream URL: {audio_url[:100]}...")
            base_opts = config.YTDLP_OPTIONS.copy()
            # Remove audio-related postprocessors - we'll convert manually
            base_opts.pop('postprocessors', None)
            logger.info("  Using VIDEO options (SmartPlayer - will convert to MP3 after download)")
        elif self.audio_only and config.YTDLP_AUDIO_OPTIONS:
            base_opts = config.YTDLP_AUDIO_OPTIONS
            logger.info("  Using AUDIO options (MP3 extraction)")
        else:
            base_opts = config.YTDLP_OPTIONS
            logger.info("  Using VIDEO options")

        ydl_opts = {
            **base_opts,
            "outtmpl": str(self.output_dir / "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
        }

        if self.format_id and not self.audio_only:
            ydl_opts["format"] = self.format_id
            logger.info(f"  Format ID: {self.format_id}")

        if self.cookie_file:
            ydl_opts["cookiefile"] = self.cookie_file

        try:
            self.progress.status = DownloadStatus.DOWNLOADING
            logger.info("  Calling yt-dlp extract_info...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(download_url, download=True)
                logger.info(f"  yt-dlp extract_info completed. Title: {info.get('title', 'N/A')}")

                if self._cancelled:
                    return DownloadResult(
                        success=False,
                        error="Download cancelled"
                    )

                filename = ydl.prepare_filename(info)
                filepath = Path(filename)

                # Handle merged/converted files (may have different extension)
                if not filepath.exists():
                    # Try MP4 for video
                    mp4_path = filepath.with_suffix(".mp4")
                    if mp4_path.exists():
                        filepath = mp4_path
                    # Try MP3 for audio extraction
                    elif self.audio_only:
                        mp3_path = filepath.with_suffix(".mp3")
                        if mp3_path.exists():
                            filepath = mp3_path

                # SmartPlayer: convert downloaded video to MP3
                if use_manual_mp3_conversion and filepath.exists():
                    self.progress.status = DownloadStatus.PROCESSING
                    if self._progress_callback:
                        self._progress_callback(self.progress)

                    mp3_path = self._convert_to_mp3(filepath)
                    if mp3_path:
                        filepath = mp3_path
                    else:
                        # Notify error via callback before returning
                        error_msg = "Failed to convert to MP3"
                        self.progress.status = DownloadStatus.ERROR
                        self.progress.error = error_msg
                        if self._progress_callback:
                            self._progress_callback(self.progress)
                        return DownloadResult(
                            success=False,
                            error=error_msg
                        )

                self.progress.status = DownloadStatus.COMPLETED
                self.progress.progress = 100.0
                self.progress.filename = filepath.name

                if self._progress_callback:
                    self._progress_callback(self.progress)

                return DownloadResult(
                    success=True,
                    filename=filepath.name,
                    filepath=str(filepath),
                    title=info.get("title", ""),
                    duration=info.get("duration", 0),
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"  Download failed: {error_msg}")
            logger.exception("  Full exception:")
            self.progress.status = DownloadStatus.ERROR
            self.progress.error = error_msg

            if self._progress_callback:
                self._progress_callback(self.progress)

            return DownloadResult(
                success=False,
                error=error_msg
            )
