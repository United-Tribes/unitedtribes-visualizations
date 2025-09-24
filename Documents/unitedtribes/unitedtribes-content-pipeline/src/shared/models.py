"""
Shared data models for United Tribes Content Scrapers v3
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field
import hashlib
from ulid import ULID, new


class ContentType(str, Enum):
    """Types of content we scrape"""
    ARTICLE = "article"
    REVIEW = "review"
    INTERVIEW = "interview"
    NEWS = "news"
    PODCAST_TRANSCRIPT = "podcast_transcript"
    PODCAST_EPISODE = "podcast_episode"


class Source(str, Enum):
    """Supported content sources"""
    BILLBOARD = "billboard"
    ROLLING_STONE = "rolling_stone"
    PITCHFORK = "pitchfork"
    NPR = "npr"
    SPOTIFY = "spotify"
    APPLE_PODCASTS = "apple_podcasts"
    SUBSTACK = "substack"


@dataclass
class SourceAttribution:
    """Complete source attribution for citations"""
    source: str                          # "Rolling Stone", "Pitchfork", etc.
    title: str                          # Article/episode title
    url: str                            # Original URL
    author: Optional[str] = None        # Author/host name
    publication_date: Optional[str] = None  # ISO date string
    publication_type: str = "article"   # article, podcast, interview, etc.
    content_type: Optional[str] = None  # review, news, feature, etc.
    episode_info: Optional[Dict[str, Any]] = None  # For podcasts

    def to_citation_format(self) -> str:
        """Generate citation string for API responses"""
        base = f'[Source: "{self.source}"'
        if self.title and len(self.title) < 60:
            base += f', "{self.title}"'
        base += ']'
        return base


@dataclass
class ScrapedContent:
    """Main scraped content container"""
    # Identifiers
    id: str = field(default_factory=lambda: str(new()))
    url: str = ""

    # Content
    title: str = ""
    content: str = ""
    content_type: ContentType = ContentType.ARTICLE

    # Metadata
    source_attribution: SourceAttribution = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 0.0
    word_count: int = 0

    # Processing info
    extraction_method: str = "unknown"
    validation_passed: bool = False

    # S3 storage
    s3_key: Optional[str] = None
    content_hash: Optional[str] = None

    def __post_init__(self):
        """Calculate derived fields"""
        if self.content:
            self.word_count = len(self.content.split())
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]

        if not self.s3_key and self.source_attribution:
            # Generate S3 key: source/YYYY/MM/DD/content-{hash}.json
            date_str = self.scraped_at.strftime("%Y/%m/%d")
            source = self.source_attribution.source.lower().replace(" ", "_")
            self.s3_key = f"scraped-content/{source}/{date_str}/content-{self.content_hash}.json"

    def to_v3_format(self) -> Dict[str, Any]:
        """Convert to v3 data lake format"""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type.value,
            "source_attribution": {
                "source": self.source_attribution.source,
                "title": self.source_attribution.title,
                "url": self.source_attribution.url,
                "author": self.source_attribution.author,
                "publication_date": self.source_attribution.publication_date,
                "publication_type": self.source_attribution.publication_type,
                "content_type": self.source_attribution.content_type,
                "episode_info": self.source_attribution.episode_info
            },
            "metadata": {
                "scraped_at": self.scraped_at.isoformat(),
                "confidence_score": self.confidence_score,
                "word_count": self.word_count,
                "extraction_method": self.extraction_method,
                "validation_passed": self.validation_passed,
                "content_hash": self.content_hash
            },
            "s3_key": self.s3_key
        }


@dataclass
class DiscoveryResult:
    """Result from content discovery"""
    urls: List[str]
    method: str  # "rss", "search", "pattern", "archive"
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScrapingBatch:
    """Collection of scraped content for processing"""
    batch_id: str = field(default_factory=lambda: str(new()))
    source: Source = None
    content_items: List[ScrapedContent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Quality metrics
    total_discovered: int = 0
    total_scraped: int = 0
    success_rate: float = 0.0

    # S3 manifest path
    manifest_s3_key: Optional[str] = None

    def __post_init__(self):
        """Calculate metrics and S3 paths"""
        self.total_scraped = len(self.content_items)
        if self.total_discovered > 0:
            self.success_rate = self.total_scraped / self.total_discovered

        # Generate manifest S3 key
        if not self.manifest_s3_key:
            date_str = self.created_at.strftime("%Y/%m/%d")
            source_name = self.source.value if self.source else "unknown"
            self.manifest_s3_key = f"manifests/scraped/{source_name}/{date_str}/batch-{self.batch_id}.json"

    def to_manifest(self) -> Dict[str, Any]:
        """Generate processing manifest"""
        return {
            "manifest_version": "1.0",
            "batch_id": self.batch_id,
            "source": self.source.value if self.source else None,
            "created_at": self.created_at.isoformat(),
            "processor_version": "content_scraper_v3.0",

            # Content summary
            "total_items": self.total_scraped,
            "content_types": list(set(item.content_type.value for item in self.content_items)),
            "content_s3_keys": [item.s3_key for item in self.content_items],

            # Quality metrics
            "metrics": {
                "total_discovered": self.total_discovered,
                "total_scraped": self.total_scraped,
                "success_rate": self.success_rate,
                "avg_confidence": sum(item.confidence_score for item in self.content_items) / max(1, len(self.content_items)),
                "avg_word_count": sum(item.word_count for item in self.content_items) / max(1, len(self.content_items))
            },

            # S3 locations
            "manifest_s3_key": self.manifest_s3_key,
            "data_prefix": f"scraped-content/{self.source.value if self.source else 'unknown'}"
        }


class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    def __init__(self, message: str, url: str = None, source: str = None):
        self.message = message
        self.url = url
        self.source = source
        super().__init__(f"{source or 'Unknown'}: {message}" + (f" ({url})" if url else ""))