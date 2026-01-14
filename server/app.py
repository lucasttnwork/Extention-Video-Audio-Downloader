"""
Flask server for video downloader.

Endpoints:
    GET  /api/status              - Server status
    POST /api/download            - Start a new download
    GET  /api/download/<id>       - Get download status
    GET  /api/queue               - List all downloads
    POST /api/download/<id>/cancel - Cancel a download
    DELETE /api/download/<id>     - Remove completed download
    POST /api/clear               - Clear completed downloads
    POST /api/info                - Get video info without downloading
"""
import atexit
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

import config
from core import DownloadManager, AuthHandler, HublaExtractor, needs_special_extraction, transform_url_if_needed

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('video_downloader')

app = Flask(__name__)

# Configure CORS for extension
CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)

# Initialize managers
download_manager = DownloadManager()
auth_handler = AuthHandler()


@app.route("/api/status", methods=["GET"])
def get_status():
    """Check if server is running."""
    queue = download_manager.get_queue()
    active = sum(1 for t in queue if t["status"] in ("downloading", "processing", "pending"))

    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "download_dir": str(config.DOWNLOAD_DIR),
        "active_downloads": active,
        "total_downloads": len(queue),
    })


@app.route("/api/download", methods=["POST"])
def start_download():
    """
    Start a new download.

    Request body:
        {
            "url": "https://...",
            "title": "Optional title",
            "format": "Optional format ID",
            "cookies": [{"name": "...", "value": "...", ...}],
            "videoUrl": "Optional extracted video URL (for Hub.la, etc)"
        }
    """
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "URL is required"}), 400

    url = data["url"]
    title = data.get("title", "")
    format_id = data.get("format")
    output_format = data.get("outputFormat", "mp4")  # mp4 or mp3
    cookies = data.get("cookies", [])
    extracted_video_url = data.get("videoUrl")  # Video URL extracted by extension

    # Log incoming request
    logger.info(f"Download request received:")
    logger.info(f"  URL: {url[:100]}...")
    logger.info(f"  Title: {title}")
    logger.info(f"  Output format: {output_format}")
    logger.info(f"  Extracted video URL: {extracted_video_url[:100] if extracted_video_url else 'None'}...")
    logger.info(f"  Cookies count: {len(cookies)}")

    # Log if this is a Cloudflare Stream URL
    if extracted_video_url and 'cloudflarestream.com' in extracted_video_url:
        logger.info(f"  [CLOUDFLARE STREAM] Detected Cloudflare Stream URL")

    # Check if user wants audio-only (MP3)
    audio_only = output_format.lower() == "mp3"

    # Don't use container formats (mp4, webm, etc) as format_id
    # These are output preferences, not yt-dlp format selectors
    container_formats = {"mp4", "webm", "mkv", "mp3", "m4a", "wav", "flac"}
    if format_id and format_id.lower() in container_formats:
        format_id = None

    # Transform URL if needed (Hub.la support)
    download_url = transform_url_if_needed(url, extracted_video_url)
    logger.info(f"  Download URL after transform: {download_url[:100]}...")

    # Check if this is a course platform page URL without extracted video
    if needs_special_extraction(url) and not extracted_video_url:
        logger.warning(f"  Special extraction required but no video URL provided")
        return jsonify({
            "error": "This course platform requires browser extraction",
            "extraction_required": True,
            "hint": "Please wait for the video to load and use the extension to detect the stream URL"
        }), 400

    # Handle cookies if provided
    cookie_file = None
    if cookies:
        try:
            from urllib.parse import urlparse
            domain = urlparse(download_url).netloc
            cookie_file = auth_handler.save_cookies_from_extension(cookies, domain)
            logger.info(f"  Cookies saved to: {cookie_file}")
        except Exception as e:
            logger.error(f"  Failed to process cookies: {e}")
            return jsonify({"error": f"Failed to process cookies: {e}"}), 400

    # Add to download queue
    logger.info(f"  Adding to download queue with audio_only={audio_only}")
    task_id = download_manager.add_download(
        url=download_url,
        title=title,
        format_id=format_id,
        cookie_file=cookie_file,
        audio_only=audio_only,
    )
    logger.info(f"  Task created with ID: {task_id}")

    return jsonify({
        "success": True,
        "id": task_id,
        "message": "Download started",
        "url": download_url,
        "original_url": url if download_url != url else None,
    }), 201


@app.route("/api/download/<task_id>", methods=["GET"])
def get_download(task_id):
    """Get status of a specific download."""
    task = download_manager.get_task(task_id)

    if not task:
        return jsonify({"error": "Download not found"}), 404

    return jsonify(task.to_dict())


@app.route("/api/queue", methods=["GET"])
def get_queue():
    """Get all downloads in queue."""
    queue = download_manager.get_queue()
    return jsonify({
        "downloads": queue,
        "count": len(queue),
    })


@app.route("/api/download/<task_id>/cancel", methods=["POST"])
def cancel_download(task_id):
    """Cancel a download."""
    success = download_manager.cancel_download(task_id)

    if not success:
        return jsonify({"error": "Cannot cancel download"}), 400

    return jsonify({
        "id": task_id,
        "message": "Download cancelled",
    })


@app.route("/api/download/<task_id>", methods=["DELETE"])
def remove_download(task_id):
    """Remove a completed/cancelled download from the queue."""
    success = download_manager.remove_task(task_id)

    if not success:
        return jsonify({"error": "Cannot remove active download"}), 400

    return jsonify({
        "id": task_id,
        "message": "Download removed",
    })


@app.route("/api/clear", methods=["POST"])
def clear_completed():
    """Clear all completed/failed downloads from the queue."""
    download_manager.clear_completed()
    return jsonify({"success": True, "message": "Completed downloads cleared"})


@app.route("/api/open-folder", methods=["POST"])
def open_folder():
    """Open the downloads folder in the file manager."""
    import subprocess
    import sys

    folder_path = str(config.DOWNLOAD_DIR)

    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", folder_path], check=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(["explorer", folder_path], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", folder_path], check=True)

        return jsonify({
            "success": True,
            "path": folder_path
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "path": folder_path
        }), 500


@app.route("/api/info", methods=["POST"])
def get_video_info():
    """
    Get video information without downloading.

    Request body:
        {
            "url": "https://...",
            "cookies": [...]
        }
    """
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "URL is required"}), 400

    url = data["url"]
    cookies = data.get("cookies", [])

    cookie_file = None
    if cookies:
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            cookie_file = auth_handler.save_cookies_from_extension(cookies, domain)
        except Exception:
            pass

    try:
        from core.downloader import Downloader
        downloader = Downloader(url=url, cookie_file=cookie_file)
        info = downloader.get_info()

        # Clean up cookie file
        if cookie_file:
            auth_handler.cleanup_cookie_file(cookie_file)

        # Extract relevant info
        formats = []
        for f in info.get("formats", []):
            if f.get("vcodec") != "none" or f.get("acodec") != "none":
                formats.append({
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f.get("resolution", "audio only"),
                    "filesize": f.get("filesize"),
                    "format_note": f.get("format_note", ""),
                })

        return jsonify({
            "title": info.get("title"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "description": info.get("description", "")[:500],
            "uploader": info.get("uploader"),
            "formats": formats[-10:],  # Last 10 formats (usually best quality)
        })

    except Exception as e:
        if cookie_file:
            auth_handler.cleanup_cookie_file(cookie_file)
        return jsonify({"error": str(e)}), 400


def cleanup():
    """Cleanup on shutdown."""
    download_manager.shutdown()
    auth_handler.cleanup_old_cookies(max_age_hours=0)


atexit.register(cleanup)


if __name__ == "__main__":
    print(f"Starting Video Downloader Server on http://{config.HOST}:{config.PORT}")
    print(f"Downloads will be saved to: {config.DOWNLOAD_DIR}")
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
    )
