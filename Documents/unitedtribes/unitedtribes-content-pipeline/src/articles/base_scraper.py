"""
Base article scraper with comprehensive validation
Foundation for all music publication scrapers
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlparse

# Import shared components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from models import ScrapedContent, ScrapingBatch, SourceAttribution, ContentType, Source
from validator import ContentValidator, SafetyChecker, ValidationResult
from fetcher import EnhancedFetcher, FetchResult
from extractor import EnhancedContentExtractor, ExtractionResult
from s3_uploader import S3ContentUploader

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for article scrapers"""
    source_name: str
    base_url: str
    rate_limit: float = 1.0  # requests per second
    max_articles_per_run: int = 1000
    content_discovery_urls: List[str] = field(default_factory=list)
    custom_selectors: Dict[str, str] = field(default_factory=dict)
    archive_bypass_enabled: bool = True
    validation_required: bool = True


@dataclass
class DiscoveryResult:
    """Result from URL discovery"""
    urls: List[str]
    method: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseArticleScraper(ABC):
    """
    Base class for music publication scrapers
    Implements comprehensive validation and safety measures
    """

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.validator = ContentValidator()
        self.safety_checker = SafetyChecker()
        self.extractor = EnhancedContentExtractor()
        self.s3_uploader = S3ContentUploader()

        # Statistics
        self.stats = {
            "discovered": 0,
            "fetched": 0,
            "extracted": 0,
            "validated": 0,
            "uploaded": 0,
            "errors": []
        }

    async def scrape_articles(self, max_articles: Optional[int] = None) -> ScrapingBatch:
        """
        Main scraping workflow with comprehensive validation
        """
        max_articles = max_articles or self.config.max_articles_per_run
        logger.info(f"🚀 Starting {self.config.source_name} scraping (max: {max_articles})")

        try:
            # Phase 1: Discover content URLs
            logger.info("🔍 Phase 1: Discovering content URLs")
            discovery_result = await self.discover_content_urls()
            self.stats["discovered"] = len(discovery_result.urls)

            if not discovery_result.urls:
                logger.warning("No URLs discovered - ending scraping")
                return self._create_empty_batch("No URLs discovered")

            # Limit URLs to process
            urls_to_process = discovery_result.urls[:max_articles]
            logger.info(f"📋 Processing {len(urls_to_process)} URLs")

            # Phase 2: Fetch and extract content
            logger.info("📥 Phase 2: Fetching and extracting content")
            scraped_items = []

            async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
                # Process URLs with concurrency control
                semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

                async def process_url(url: str) -> Optional[ScrapedContent]:
                    async with semaphore:
                        return await self._process_single_url(url, fetcher)

                tasks = [process_url(url) for url in urls_to_process]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Collect successful results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.stats["errors"].append(f"URL {urls_to_process[i]}: {result}")
                        logger.error(f"Error processing {urls_to_process[i]}: {result}")
                    elif result:
                        scraped_items.append(result)

            self.stats["extracted"] = len(scraped_items)
            logger.info(f"✅ Extracted {len(scraped_items)} articles")

            # Phase 3: Validation and safety checks
            logger.info("🔍 Phase 3: Validation and safety checks")
            validated_items = []

            for item in scraped_items:
                if self.config.validation_required:
                    validation_result = self.validator.validate_scraped_content(item)
                    if validation_result.passed:
                        item.validation_passed = True
                        item.confidence_score = validation_result.score
                        validated_items.append(item)
                    else:
                        logger.warning(f"Validation failed for {item.url}: {validation_result.errors}")
                        self.stats["errors"].extend(validation_result.errors)
                else:
                    validated_items.append(item)

            self.stats["validated"] = len(validated_items)
            logger.info(f"✅ Validated {len(validated_items)} articles")

            # Phase 4: Create and validate batch
            logger.info("📦 Phase 4: Creating batch")

            # Map source name to enum value
            source_mapping = {
                "pitchfork": Source.PITCHFORK,
                "npr": Source.NPR,
                "rolling stone": Source.ROLLING_STONE,
                "billboard": Source.BILLBOARD
            }
            source_enum = source_mapping.get(self.config.source_name.lower(), Source.PITCHFORK)

            batch = ScrapingBatch(
                source=source_enum,
                content_items=validated_items,
                total_discovered=self.stats["discovered"],
                total_scraped=len(validated_items)
            )

            # Final safety check
            is_safe, safety_errors = self.safety_checker.pre_processing_safety_check(batch)
            if not is_safe:
                logger.error(f"❌ Batch failed safety check: {safety_errors}")
                self.stats["errors"].extend(safety_errors)
                return self._create_empty_batch(f"Safety check failed: {safety_errors}")

            # Phase 5: Upload to S3 with proper organization
            logger.info("📤 Phase 5: Uploading to S3")
            try:
                upload_results = await self.s3_uploader.upload_batch(batch)
                self.stats["uploaded"] = upload_results["successful_uploads"]

                if upload_results["successful_uploads"] > 0:
                    logger.info(f"✅ Uploaded {upload_results['successful_uploads']}/{upload_results['total_items']} articles to S3")
                    logger.info(f"📊 S3 organization: [artist]/[thematic]/[filename] pattern")

                    if upload_results["errors"]:
                        logger.warning(f"⚠️ Upload warnings: {upload_results['errors']}")
                        self.stats["errors"].extend(upload_results["errors"])
                else:
                    logger.error("❌ No articles were uploaded to S3")
                    self.stats["errors"].append("S3 upload failed for all items")

            except Exception as e:
                logger.error(f"💥 S3 upload failed: {e}")
                self.stats["errors"].append(f"S3 upload exception: {e}")

            logger.info(f"🎉 Scraping completed - {len(validated_items)} articles processed, {self.stats['uploaded']} uploaded")
            return batch

        except Exception as e:
            logger.error(f"💥 Scraping failed: {e}")
            self.stats["errors"].append(str(e))
            return self._create_empty_batch(f"Scraping exception: {e}")

    async def _process_single_url(self, url: str, fetcher: EnhancedFetcher) -> Optional[ScrapedContent]:
        """Process a single URL through the complete pipeline"""
        try:
            # Step 1: Fetch content
            fetch_result = await fetcher.fetch_with_fallbacks(url)
            if not fetch_result.success or not fetch_result.content:
                logger.debug(f"Failed to fetch {url}: {fetch_result.error_message}")
                return None

            self.stats["fetched"] += 1

            # Step 2: Extract structured content
            extraction_result = self.extractor.extract_content(
                html=fetch_result.content,
                url=url,
                source_name=self.config.source_name
            )

            if not extraction_result.success or not extraction_result.content:
                logger.debug(f"Failed to extract content from {url}: {extraction_result.errors}")
                return None

            # Step 3: Apply source-specific enhancements
            enhanced_content = await self.enhance_extracted_content(
                extraction_result.content,
                fetch_result,
                extraction_result
            )

            # Step 4: Apply music relevance filtering
            if not self._is_music_relevant(enhanced_content):
                logger.debug(f"Content not music-relevant: {url}")
                return None

            return enhanced_content

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None

    def _is_music_relevant(self, content: ScrapedContent) -> bool:
        """Check if content is relevant to music/culture"""
        # Quick relevance check before full validation
        text = (content.title + " " + content.content).lower()

        music_keywords = [
            'music', 'album', 'song', 'artist', 'band', 'musician', 'singer',
            'concert', 'tour', 'festival', 'record', 'recording', 'studio',
            'genre', 'jazz', 'rock', 'pop', 'hip-hop', 'classical', 'folk',
            'guitar', 'piano', 'drums', 'vocals', 'lyrics', 'melody'
        ]

        # Content is relevant if it contains at least 2 music keywords
        music_mentions = sum(1 for keyword in music_keywords if keyword in text)
        return music_mentions >= 2

    @abstractmethod
    async def discover_content_urls(self) -> DiscoveryResult:
        """Discover URLs to scrape - implemented by each source"""
        pass

    async def enhance_extracted_content(
        self,
        content: ScrapedContent,
        fetch_result: FetchResult,
        extraction_result: ExtractionResult
    ) -> ScrapedContent:
        """
        Source-specific content enhancement
        Override in subclasses for custom processing
        """
        # Default: update metadata with extraction info
        content.extraction_method = extraction_result.method
        content.confidence_score = extraction_result.confidence

        # Add fetch metadata
        if fetch_result.metadata:
            content.source_attribution.publication_type = "article"

        return content

    def get_statistics(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        return {
            **self.stats,
            "success_rate": self.stats["validated"] / max(1, self.stats["discovered"]),
            "extraction_rate": self.stats["extracted"] / max(1, self.stats["fetched"]),
            "validation_rate": self.stats["validated"] / max(1, self.stats["extracted"]),
            "upload_rate": self.stats["uploaded"] / max(1, self.stats["validated"]),
            "end_to_end_success": self.stats["uploaded"] / max(1, self.stats["discovered"])
        }

    def _create_empty_batch(self, reason: str) -> ScrapingBatch:
        """Create empty batch with error information"""
        return ScrapingBatch(
            source=Source(self.config.source_name.lower()),
            content_items=[],
            total_discovered=self.stats["discovered"],
            total_scraped=0
        )


class PatternBasedDiscovery:
    """
    URL discovery using pattern-based generation
    Inspired by the sophisticated discovery in deprecated scrapers
    """

    def __init__(self, base_url: str, source_name: str):
        self.base_url = base_url
        self.source_name = source_name

    async def discover_by_sitemap(self) -> List[str]:
        """Discover URLs via sitemap"""
        sitemap_urls = [
            urljoin(self.base_url, "/sitemap.xml"),
            urljoin(self.base_url, "/sitemap_index.xml"),
            urljoin(self.base_url, "/robots.txt")  # May contain sitemap references
        ]

        discovered_urls = []

        async with EnhancedFetcher(rate_limit=2.0) as fetcher:
            for sitemap_url in sitemap_urls:
                try:
                    result = await fetcher.fetch_with_fallbacks(sitemap_url)
                    if result.success and result.content:
                        urls = self._extract_urls_from_sitemap(result.content)
                        discovered_urls.extend(urls)
                except Exception as e:
                    logger.debug(f"Sitemap discovery failed for {sitemap_url}: {e}")

        return discovered_urls[:100]  # Limit results

    def _extract_urls_from_sitemap(self, content: str) -> List[str]:
        """Extract URLs from sitemap XML"""
        from xml.etree import ElementTree as ET

        urls = []
        try:
            root = ET.fromstring(content)

            # Handle both regular sitemaps and sitemap indexes
            for elem in root.iter():
                if elem.tag.endswith('loc') and elem.text:
                    url = elem.text.strip()
                    # Filter for article-like URLs
                    if self._is_article_url(url):
                        urls.append(url)

        except ET.ParseError:
            # Fallback: regex extraction for malformed XML
            url_pattern = r'<loc>(https?://[^<]+)</loc>'
            matches = re.findall(url_pattern, content, re.IGNORECASE)
            urls.extend([url for url in matches if self._is_article_url(url)])

        return urls

    def _is_article_url(self, url: str) -> bool:
        """Check if URL looks like an article"""
        # Source-specific patterns
        article_patterns = {
            'pitchfork': ['/reviews/', '/features/', '/news/'],
            'rolling_stone': ['/music/', '/music-news/', '/reviews/'],
            'billboard': ['/music/', '/pro/', '/news/'],
            'npr': ['/sections/music/', '/music/']
        }

        patterns = article_patterns.get(self.source_name.lower(), ['/music/', '/review', '/article'])

        return any(pattern in url.lower() for pattern in patterns)

    async def discover_by_rss(self) -> List[str]:
        """Discover URLs via RSS feeds"""
        rss_feeds = self._get_rss_feeds()
        discovered_urls = []

        async with EnhancedFetcher(rate_limit=2.0) as fetcher:
            for feed_url in rss_feeds:
                try:
                    result = await fetcher.fetch_with_fallbacks(feed_url)
                    if result.success and result.content:
                        urls = self._extract_urls_from_rss(result.content)
                        discovered_urls.extend(urls)
                except Exception as e:
                    logger.debug(f"RSS discovery failed for {feed_url}: {e}")

        return discovered_urls[:50]  # Limit results

    def _get_rss_feeds(self) -> List[str]:
        """Get RSS feed URLs for each source"""
        rss_feeds = {
            'pitchfork': [
                'https://pitchfork.com/rss/reviews/',
                'https://pitchfork.com/rss/news/'
            ],
            'rolling_stone': [
                'https://www.rollingstone.com/music/feed/',
                'https://www.rollingstone.com/feed/'
            ],
            'billboard': [
                'https://www.billboard.com/feed/',
                'https://www.billboard.com/music/feed/'
            ],
            'npr': [
                'https://feeds.npr.org/1039/rss.xml',  # Music
                'https://feeds.npr.org/510019/podcast.xml'  # Fresh Air
            ]
        }

        return rss_feeds.get(self.source_name.lower(), [])

    def _extract_urls_from_rss(self, content: str) -> List[str]:
        """Extract URLs from RSS feed"""
        from xml.etree import ElementTree as ET

        urls = []
        try:
            root = ET.fromstring(content)

            # Look for item links
            for item in root.iter('item'):
                link_elem = item.find('link')
                if link_elem is not None and link_elem.text:
                    urls.append(link_elem.text.strip())

            # Also check for guid elements that might be URLs
            for guid in root.iter('guid'):
                if guid.text and guid.text.startswith('http'):
                    urls.append(guid.text.strip())

        except ET.ParseError as e:
            logger.debug(f"RSS parsing failed: {e}")

        return urls

    async def discover_by_artist_search(self, artist_names: List[str]) -> List[str]:
        """Discover URLs by searching for specific artists using direct search fallback"""

        try:
            # Import the direct search fallback that bypasses EnhancedFetcher issues
            from direct_search_fallback import DirectSearchFallback

            logger.info(f"🔄 Using direct search fallback for {self.source_name}")
            fallback = DirectSearchFallback()

            all_urls = []
            for artist_name in artist_names:
                try:
                    urls = await fallback.search_for_artist(self.source_name.lower(), artist_name)
                    all_urls.extend(urls)
                    logger.info(f"📊 Found {len(urls)} URLs for {artist_name}")
                except Exception as e:
                    logger.error(f"Direct search failed for {artist_name}: {e}")

            # Remove duplicates while preserving order - no artificial limit
            unique_urls = list(dict.fromkeys(all_urls))
            logger.info(f"📊 Total unique URLs from artist search: {len(unique_urls)}")

            return unique_urls

        except ImportError:
            logger.warning("Direct search fallback not available, using original method")

            # Original method as fallback
            discovered_urls = []

            # Search URL patterns for each source
            search_patterns = {
                'pitchfork': 'https://pitchfork.com/search/?q={}',
                'rolling_stone': 'https://www.rollingstone.com/results/?q={}',
                'billboard': 'https://www.billboard.com/results/?q={}&size=n_10_n&sort-field=relevance&sort-direction=desc',
                'npr': 'https://www.npr.org/search/?query={}&page=1'
            }

            pattern = search_patterns.get(self.source_name.lower())
            if not pattern:
                return []

            async with EnhancedFetcher(rate_limit=1.0) as fetcher:
                for artist_name in artist_names:
                    try:
                        # Format artist name for URL
                        search_term = artist_name.replace(' ', '+')
                        search_url = pattern.format(search_term)

                        result = await fetcher.fetch_with_fallbacks(search_url)
                        if result.success and result.content:
                            urls = self._extract_article_urls_from_search_results(result.content)
                            discovered_urls.extend(urls)
                            logger.info(f"Found {len(urls)} articles for {artist_name}")

                    except Exception as e:
                        logger.debug(f"Search failed for {artist_name}: {e}")

            return discovered_urls  # No artificial limit

    def _extract_article_urls_from_search_results(self, content: str) -> List[str]:
        """Extract article URLs from search results page"""
        from bs4 import BeautifulSoup
        urls = []

        try:
            soup = BeautifulSoup(content, 'html.parser')

            # Find links in search results
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')

                # Convert relative URLs to absolute
                if href.startswith('/'):
                    full_url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                # Filter for article-like URLs from this source
                if self._is_source_article_url(full_url):
                    urls.append(full_url)

        except Exception as e:
            logger.debug(f"Search results parsing error: {e}")

        return urls

    def _is_source_article_url(self, url: str) -> bool:
        """Check if URL is an article from this source"""
        # Source-specific patterns
        article_patterns = {
            'pitchfork': ['/reviews/', '/features/', '/news/'],
            'rolling stone': ['/music/', '/music-news/', '/reviews/', '/features/'],
            'billboard': ['/music/', '/pro/', '/news/', '/charts/'],
            'npr': ['/sections/music/', '/music/', '/2024/', '/2023/']
        }

        patterns = article_patterns.get(self.source_name.lower(), ['/music/', '/review', '/article'])
        return any(pattern in url.lower() for pattern in patterns)

    def _get_url_patterns(self) -> List[str]:
        """Get URL patterns for each source"""
        patterns = {
            'pitchfork': [
                'https://pitchfork.com/reviews/albums/',
                'https://pitchfork.com/features/'
            ],
            'rolling_stone': [
                'https://www.rollingstone.com/music/music-news/',
                'https://www.rollingstone.com/music/music-album-reviews/'
            ],
            'billboard': [
                'https://www.billboard.com/music/',
                'https://www.billboard.com/pro/'
            ],
            'npr': [
                'https://www.npr.org/sections/music/',
                'https://www.npr.org/podcasts/510019/fresh-air'
            ]
        }

        return patterns.get(self.source_name.lower(), [])