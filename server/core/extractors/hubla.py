"""
Cloudflare Stream video extractor for course platforms.

Many course platforms (Hub.la, Código Viral, Hotmart, etc.) use Cloudflare Stream
for video hosting with JWT-authenticated HLS URLs.
The actual video URLs are in the format:
https://customer-XXXX.cloudflarestream.com/JWTTOKEN/manifest/video.m3u8

This extractor provides utilities to:
1. Detect course platform URLs that use Cloudflare Stream
2. Validate and process Cloudflare Stream URLs
3. Guide the extension on how to extract video URLs
"""
import re
import logging
from typing import Optional
from urllib.parse import urlparse

from .base import BaseExtractor, ExtractorResult

logger = logging.getLogger('video_downloader.extractor')

# Platforms known to use special video players (Cloudflare Stream, SmartPlayer, etc)
SPECIAL_PLAYER_PLATFORMS = [
    r"hub\.la",
    r"app\.hub\.la",
    r"codigoviral\.com\.br",
    r"cursos\.codigoviral\.com\.br",
    r"hotmart\.com",
    r"eduzz\.com",
    r"kiwify\.com\.br",
    r"monetizze\.com\.br",
    r"areademembros\.com",
]


class HublaExtractor(BaseExtractor):
    """Extractor for course platforms using special video players."""

    # URL patterns for platforms using special players
    URL_PATTERNS = SPECIAL_PLAYER_PLATFORMS

    # Cloudflare Stream URL pattern
    CLOUDFLARE_STREAM_PATTERN = r"https?://[^/]*cloudflarestream\.com/[^/]+/manifest/video\.m3u8"

    # SmartPlayer/ScaleUp URL patterns
    SMARTPLAYER_PATTERN = r"https?://stream\.smartplayer\.io/[a-f0-9]+/[a-f0-9]+/[^\"'\s]+\.(mp4|m3u8)"
    SCALEUP_PATTERN = r"https?://stream\.scaleup\.com\.br/player/v1/playlists/[^\"'\s]+\.m3u8"

    @classmethod
    def is_hubla_url(cls, url: str) -> bool:
        """Check if URL is from a Cloudflare Stream platform (Hub.la, Código Viral, etc)."""
        return cls.can_handle(url)

    @classmethod
    def is_cloudflare_platform_url(cls, url: str) -> bool:
        """Check if URL is from a known Cloudflare Stream platform."""
        return cls.can_handle(url)

    @classmethod
    def is_cloudflare_stream_url(cls, url: str) -> bool:
        """Check if URL is a Cloudflare Stream manifest."""
        return bool(re.search(cls.CLOUDFLARE_STREAM_PATTERN, url, re.IGNORECASE))

    @classmethod
    def is_smartplayer_url(cls, url: str) -> bool:
        """Check if URL is a SmartPlayer/ScaleUp stream."""
        return bool(re.search(cls.SMARTPLAYER_PATTERN, url, re.IGNORECASE)) or \
               bool(re.search(cls.SCALEUP_PATTERN, url, re.IGNORECASE))

    @classmethod
    def is_direct_stream_url(cls, url: str) -> bool:
        """Check if URL is a direct stream URL (Cloudflare or SmartPlayer)."""
        return cls.is_cloudflare_stream_url(url) or cls.is_smartplayer_url(url)

    @classmethod
    def extract_cloudflare_url_from_text(cls, text: str) -> Optional[str]:
        """
        Extract Cloudflare Stream URL from text (HTML, JSON, etc).

        Args:
            text: Text content to search

        Returns:
            Cloudflare Stream URL if found, None otherwise
        """
        # Pattern to match Cloudflare Stream URLs with JWT tokens
        pattern = r'https?://customer-[a-z0-9]+\.cloudflarestream\.com/[A-Za-z0-9_-]+/manifest/video\.m3u8'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def extract(self, url: str, cookies: Optional[list] = None) -> ExtractorResult:
        """
        Extract video URL from Hub.la page.

        Note: Hub.la requires authentication and loads video URLs dynamically.
        The actual extraction should happen client-side via the browser extension.
        This method handles the case where the video URL is already extracted.
        """
        # If it's already a Cloudflare Stream URL, return it directly
        if self.is_cloudflare_stream_url(url):
            return ExtractorResult(
                success=True,
                video_url=url,
                requires_cookies=False,
                extra_data={"source": "cloudflare_stream"}
            )

        # If it's a course platform page URL, we need the extension to extract the video
        if self.is_cloudflare_platform_url(url):
            logger.info(f"Cloudflare Stream platform detected, requires browser extraction: {url[:50]}...")
            return ExtractorResult(
                success=False,
                error="This course platform requires browser-based extraction. Please use the browser extension to extract the video URL.",
                requires_cookies=True,
                extra_data={
                    "extraction_hint": "cloudflare_extension_required",
                    "instructions": [
                        "1. Open the video page in your browser",
                        "2. Wait for the video to load and start playing",
                        "3. Use the Video Downloader extension",
                        "4. The extension will detect the Cloudflare Stream URL"
                    ]
                }
            )

        return ExtractorResult(
            success=False,
            error="URL not recognized as Hub.la or Cloudflare Stream"
        )

    def get_info(self, url: str, cookies: Optional[list] = None) -> ExtractorResult:
        """Get video info from Hub.la."""
        # For Cloudflare Stream URLs, yt-dlp can extract info directly
        if self.is_cloudflare_stream_url(url):
            return ExtractorResult(
                success=True,
                video_url=url,
                extra_data={"source": "cloudflare_stream"}
            )

        # For Hub.la page URLs, extraction requires browser
        return ExtractorResult(
            success=False,
            error="Hub.la page URLs require browser-based extraction",
            requires_cookies=True
        )


def get_extractor_for_url(url: str) -> Optional[BaseExtractor]:
    """
    Get the appropriate extractor for a URL.

    Args:
        url: URL to find extractor for

    Returns:
        Extractor instance if one matches, None otherwise
    """
    extractors = [HublaExtractor]

    for extractor_class in extractors:
        if extractor_class.can_handle(url):
            return extractor_class()

    return None


def needs_special_extraction(url: str) -> bool:
    """Check if URL needs special extraction (not natively supported by yt-dlp)."""
    # Course platform page URLs need special handling
    # Cloudflare Stream URLs themselves can be handled directly
    if HublaExtractor.is_cloudflare_platform_url(url) and not HublaExtractor.is_cloudflare_stream_url(url):
        logger.debug(f"URL needs special extraction: {url[:50]}...")
        return True
    return False


def transform_url_if_needed(url: str, extracted_video_url: Optional[str] = None) -> str:
    """
    Transform URL if needed for download.

    Args:
        url: Original URL
        extracted_video_url: Video URL extracted by extension (if available)

    Returns:
        URL to use for download
    """
    # If we have an extracted video URL that's a direct stream, use it
    if extracted_video_url and HublaExtractor.is_direct_stream_url(extracted_video_url):
        logger.info(f"Using extracted stream URL: {extracted_video_url[:80]}...")
        return extracted_video_url

    # If URL is already a direct stream URL, use it directly
    if HublaExtractor.is_direct_stream_url(url):
        logger.info(f"URL is direct stream, using as-is: {url[:80]}...")
        return url

    # Return original URL for yt-dlp to handle
    return url
