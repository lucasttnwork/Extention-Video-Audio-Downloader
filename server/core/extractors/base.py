"""
Base extractor class for custom URL handlers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class ExtractorResult:
    """Result from URL extraction."""
    success: bool
    video_url: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    error: Optional[str] = None
    requires_cookies: bool = False
    extra_data: Optional[dict] = None


class BaseExtractor(ABC):
    """Base class for custom URL extractors."""

    # URL patterns this extractor handles
    URL_PATTERNS: list[str] = []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Check if this extractor can handle the given URL."""
        for pattern in cls.URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    @abstractmethod
    def extract(self, url: str, cookies: Optional[list] = None) -> ExtractorResult:
        """
        Extract the actual video URL from the page URL.

        Args:
            url: The page URL to extract from
            cookies: Optional list of cookie dicts for authentication

        Returns:
            ExtractorResult with the video URL or error
        """
        pass

    @abstractmethod
    def get_info(self, url: str, cookies: Optional[list] = None) -> ExtractorResult:
        """
        Get video information without the actual URL.

        Args:
            url: The page URL
            cookies: Optional list of cookie dicts

        Returns:
            ExtractorResult with video metadata
        """
        pass
