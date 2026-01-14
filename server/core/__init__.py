"""Core modules for video downloader server."""
from .downloader import Downloader
from .download_manager import DownloadManager
from .auth_handler import AuthHandler
from .extractors import HublaExtractor, get_extractor_for_url, needs_special_extraction, transform_url_if_needed

__all__ = [
    "Downloader",
    "DownloadManager",
    "AuthHandler",
    "HublaExtractor",
    "get_extractor_for_url",
    "needs_special_extraction",
    "transform_url_if_needed",
]
