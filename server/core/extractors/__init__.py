"""
Custom URL extractors for platforms not directly supported by yt-dlp.
"""
from .hubla import HublaExtractor, get_extractor_for_url, needs_special_extraction, transform_url_if_needed
from .base import BaseExtractor, ExtractorResult

__all__ = [
    "HublaExtractor",
    "BaseExtractor",
    "ExtractorResult",
    "get_extractor_for_url",
    "needs_special_extraction",
    "transform_url_if_needed",
]
