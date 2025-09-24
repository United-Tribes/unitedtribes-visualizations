"""
Rolling Stone Article Scraper
Implements real content discovery for Rolling Stone magazine
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Import base components
from base_scraper import BaseArticleScraper, ScraperConfig, DiscoveryResult, PatternBasedDiscovery

# Import shared components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from models import ScrapedContent, SourceAttribution, ContentType
from fetcher import EnhancedFetcher

logger = logging.getLogger(__name__)


class RollingStoneScraper(BaseArticleScraper):
    """
    Rolling Stone magazine scraper with comprehensive music content discovery
    """

    def __init__(self, artist_tracker=None):
        config = ScraperConfig(
            source_name="rolling_stone",
            base_url="https://www.rollingstone.com",
            rate_limit=1.0,
            max_articles_per_run=1000,
            content_discovery_urls=[
                "https://www.rollingstone.com/music/",
                "https://www.rollingstone.com/music/music-news/",
                "https://www.rollingstone.com/music/music-album-reviews/",
                "https://www.rollingstone.com/music/music-features/"
            ]
        )
        super().__init__(config)
        self.artist_tracker = artist_tracker
        self.pattern_discovery = PatternBasedDiscovery(config.base_url, "rolling_stone")

        # Jazz artists for targeted discovery
        self.jazz_artists = [
            "John Coltrane", "Lee Morgan", "Art Blakey", "Horace Silver", "Charlie Parker",
            "Grant Green", "Dexter Gordon", "Kenny Drew", "Paul Chambers", "Philly Joe Jones",
            "Herbie Hancock", "Freddie Hubbard", "Joe Henderson", "Donald Byrd", "Wayne Shorter",
            "Thelonious Monk", "Duke Ellington", "Dizzy Gillespie", "Joe Pass",
            "Miles Davis", "Bill Evans", "Cannonball Adderley", "Bill Charlap", "John Scofield", "Pat Metheny"
        ]

    async def discover_content_urls(self) -> DiscoveryResult:
        """
        Discover Rolling Stone content URLs using artist search
        """
        logger.info("🎸 Discovering Rolling Stone content...")

        all_urls = []

        # Strategy 1: Search for each of our 25 artists specifically
        logger.info("🔍 Searching Rolling Stone for our 25 specific artists...")
        artist_search_urls = await self.pattern_discovery.discover_by_artist_search(self.jazz_artists)
        all_urls.extend(artist_search_urls)

        # Deduplicate and filter
        unique_urls = list(dict.fromkeys(all_urls))  # Preserve order, remove duplicates
        music_urls = [url for url in unique_urls if self._is_music_relevant_url(url)]

        logger.info(f"🔍 Rolling Stone discovery: {len(music_urls)} music URLs found from {len(all_urls)} total")

        # Strategy 2: Discover from music sections
        logger.info("🎵 Exploring music sections...")
        section_search_urls = await self._discover_from_music_sections()
        all_urls.extend(section_search_urls)

        # Deduplicate and filter again after adding section URLs
        unique_urls = list(dict.fromkeys(all_urls))  # Preserve order, remove duplicates
        music_urls = [url for url in unique_urls if self._is_music_relevant_url(url)]

        return DiscoveryResult(
            urls=music_urls,
            method="artist_search_and_sections",
            confidence=0.9,
            metadata={
                "artist_search_urls": len(artist_search_urls),
                "section_urls": len(section_search_urls),
                "total_before_filter": len(all_urls)
            }
        )

    async def _discover_from_music_sections(self) -> List[str]:
        """Discover URLs from Rolling Stone music sections"""
        discovered_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            for section_url in self.config.content_discovery_urls:
                try:
                    result = await fetcher.fetch_with_fallbacks(section_url)
                    if result.success and result.content:
                        urls = self._extract_article_urls_from_page(result.content, section_url)
                        discovered_urls.extend(urls)
                        logger.debug(f"Found {len(urls)} URLs from {section_url}")

                except Exception as e:
                    logger.debug(f"Error discovering from {section_url}: {e}")

        return discovered_urls

    async def _discover_recent_articles(self) -> List[str]:
        """Discover recent articles from main music page"""
        discovered_urls = []

        try:
            async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
                # Check main music page
                result = await fetcher.fetch_with_fallbacks("https://www.rollingstone.com/music/")

                if result.success and result.content:
                    soup = BeautifulSoup(result.content, 'html.parser')

                    # Find article links
                    article_links = soup.find_all('a', href=True)

                    for link in article_links:
                        href = link.get('href', '')
                        if href.startswith('/'):
                            full_url = urljoin("https://www.rollingstone.com", href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue

                        # Filter for music-related URLs
                        if self._is_music_relevant_url(full_url):
                            discovered_urls.append(full_url)

        except Exception as e:
            logger.debug(f"Error discovering recent articles: {e}")

        return discovered_urls[:20]  # Limit recent articles

    async def _search_for_artists(self) -> List[str]:
        """Search Rolling Stone for each of our 25 jazz artists"""
        discovered_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            for artist_name in self.jazz_artists:
                try:
                    # Use the exact search URL format you provided
                    search_term = artist_name.replace(' ', '+')
                    search_url = f"https://www.rollingstone.com/results/?q={search_term}"

                    logger.info(f"🔍 Searching Rolling Stone for: {artist_name}")
                    result = await fetcher.fetch_with_fallbacks(search_url)

                    if result.success and result.content:
                        # Try multiple approaches to extract URLs
                        urls = self._extract_urls_from_rolling_stone_search(result.content)

                        if urls:
                            discovered_urls.extend(urls)
                            logger.info(f"📊 Found {len(urls)} articles for {artist_name}")

                            # Update artist tracker
                            if self.artist_tracker:
                                self.artist_tracker.update_artist_discovery(artist_name, "rolling_stone", len(urls))
                        else:
                            logger.info(f"📊 Found 0 articles for {artist_name}")

                except Exception as e:
                    logger.error(f"Search failed for {artist_name}: {e}")

        return discovered_urls

    def _extract_urls_from_rolling_stone_search(self, content: str) -> List[str]:
        """Extract article URLs from Rolling Stone search results"""
        from bs4 import BeautifulSoup
        import json
        urls = []

        try:
            # Method 1: Look for JSON data in the page (common for JS-loaded content)
            if '"url"' in content and 'rollingstone.com' in content:
                # Extract URLs from JSON-like structures
                import re
                json_urls = re.findall(r'"url":\s*"(https://www\.rollingstone\.com/[^"]+)"', content)
                for url in json_urls:
                    if self._is_article_url(url):
                        urls.append(url)

            # Method 2: Look for direct URL references
            url_patterns = [
                r'https://www\.rollingstone\.com/music/[^"\s]+',
                r'/music/music-[^"\s]+',
                r'/music/[^"\s]+\d+/'
            ]

            for pattern in url_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.startswith('/'):
                        full_url = "https://www.rollingstone.com" + match
                    else:
                        full_url = match

                    if self._is_article_url(full_url):
                        urls.append(full_url)

            # Method 3: Traditional HTML parsing (fallback)
            soup = BeautifulSoup(content, 'html.parser')
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')
                if href.startswith('/'):
                    full_url = "https://www.rollingstone.com" + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                if self._is_article_url(full_url):
                    urls.append(full_url)

        except Exception as e:
            logger.debug(f"Search results parsing error: {e}")

        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    def _is_article_url(self, url: str) -> bool:
        """Check if URL is a Rolling Stone article"""
        url_lower = url.lower()

        # Must be Rolling Stone domain
        if 'rollingstone.com' not in url_lower:
            return False

        # Must be music-related
        if '/music/' not in url_lower:
            return False

        # Must look like an article (has number ID or specific path)
        if any(pattern in url_lower for pattern in ['/music-news/', '/music-features/', '/music-lists/', '/reviews/']):
            return True

        # Or has numeric ID at end
        import re
        if re.search(r'/music/.*\d+/$', url_lower):
            return True

        return False

    def _extract_article_urls_from_page(self, content: str, base_url: str) -> List[str]:
        """Extract article URLs from a section page"""
        urls = []

        try:
            soup = BeautifulSoup(content, 'html.parser')

            # Find all links
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')

                # Convert relative URLs to absolute
                if href.startswith('/'):
                    full_url = urljoin("https://www.rollingstone.com", href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                # Filter for article-like URLs
                if self._is_music_relevant_url(full_url):
                    urls.append(full_url)

        except Exception as e:
            logger.debug(f"Error extracting URLs from page: {e}")

        return urls

    def _is_music_relevant_url(self, url: str) -> bool:
        """Check if URL is relevant to music content"""
        url_lower = url.lower()

        # Must contain music-related paths
        music_paths = ['/music/', '/music-news/', '/music-album-reviews/', '/music-features/']
        if not any(path in url_lower for path in music_paths):
            return False

        # Exclude non-article content
        exclude_patterns = [
            '/tag/', '/author/', '/category/', '/search/',
            '/newsletter', '/subscribe', '/contact', '/about'
        ]
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        return True

    async def enhance_extracted_content(self, content, fetch_result, extraction_result):
        """Enhance content with Rolling Stone specific processing"""
        enhanced_content = await super().enhance_extracted_content(content, fetch_result, extraction_result)

        # Check for jazz artist mentions and update tracker
        if self.artist_tracker:
            detected_artists = self._detect_jazz_artists_in_content(enhanced_content)
            for artist_name in detected_artists:
                self.artist_tracker.update_artist_discovery(artist_name, "rolling_stone", 1)
                logger.info(f"🎺 Found {artist_name} in Rolling Stone article: {enhanced_content.title}")

        # Add Rolling Stone specific metadata
        enhanced_content.source_attribution.publication_type = "magazine_article"

        return enhanced_content

    def _detect_jazz_artists_in_content(self, content: ScrapedContent) -> List[str]:
        """Detect which jazz artists are mentioned in content"""
        text = (content.title + " " + content.content).lower()
        detected_artists = []

        for artist_name in self.jazz_artists:
            # Simple name matching with word boundaries
            import re
            pattern = re.compile(rf'\b{re.escape(artist_name.lower())}\b')
            if pattern.search(text):
                detected_artists.append(artist_name)

        return detected_artists