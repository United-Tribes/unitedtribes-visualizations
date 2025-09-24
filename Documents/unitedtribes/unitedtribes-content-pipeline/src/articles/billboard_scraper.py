"""
Billboard Article Scraper
Implements real content discovery for Billboard magazine
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


class BillboardScraper(BaseArticleScraper):
    """
    Billboard magazine scraper with comprehensive music content discovery
    """

    def __init__(self, artist_tracker=None):
        config = ScraperConfig(
            source_name="billboard",
            base_url="https://www.billboard.com",
            rate_limit=1.0,
            max_articles_per_run=1000,
            content_discovery_urls=[
                "https://www.billboard.com/music/",
                "https://www.billboard.com/music/music-news/",
                "https://www.billboard.com/pro/",
                "https://www.billboard.com/culture/"
            ]
        )
        super().__init__(config)
        self.artist_tracker = artist_tracker
        self.pattern_discovery = PatternBasedDiscovery(config.base_url, "billboard")

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
        Discover Billboard content URLs using artist search
        """
        logger.info("📊 Discovering Billboard content...")

        all_urls = []

        # Strategy 1: Search for each of our 25 artists specifically
        logger.info("🔍 Searching Billboard for our 25 specific artists...")
        artist_search_urls = await self.pattern_discovery.discover_by_artist_search(self.jazz_artists)
        all_urls.extend(artist_search_urls)

        # Strategy 2: Music section discovery
        logger.info("🎵 Exploring music sections...")
        section_urls = await self._discover_from_music_sections()
        all_urls.extend(section_urls)

        # Strategy 3: Chart-related content (Billboard specialty)
        logger.info("📈 Finding chart and industry content...")
        chart_urls = await self._discover_chart_content()
        all_urls.extend(chart_urls)

        # Deduplicate and filter
        unique_urls = list(dict.fromkeys(all_urls))  # Preserve order, remove duplicates
        music_urls = [url for url in unique_urls if self._is_music_relevant_url(url)]

        logger.info(f"🔍 Billboard discovery: {len(music_urls)} music URLs found from {len(all_urls)} total")

        return DiscoveryResult(
            urls=music_urls,
            method="artist_search_section_and_charts",
            confidence=0.9,
            metadata={
                "artist_search_urls": len(artist_search_urls),
                "section_urls": len(section_urls),
                "chart_urls": len(chart_urls),
                "total_before_filter": len(all_urls)
            }
        )

    async def _search_for_artists(self) -> List[str]:
        """Search Billboard for each of our 25 jazz artists"""
        discovered_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            for artist_name in self.jazz_artists:
                try:
                    # Use the exact search URL format provided by user
                    search_term = artist_name.replace(' ', '%20')
                    search_url = f"https://www.billboard.com/results/?q={search_term}&size=n_10_n&sort-field=relevance&sort-direction=desc"

                    logger.info(f"🔍 Searching Billboard for: {artist_name}")
                    result = await fetcher.fetch_with_fallbacks(search_url)

                    if result.success and result.content:
                        # Extract URLs from Billboard search results
                        urls = self._extract_urls_from_billboard_search(result.content)

                        if urls:
                            discovered_urls.extend(urls)
                            logger.info(f"📊 Found {len(urls)} articles for {artist_name}")

                            # Update artist tracker
                            if self.artist_tracker:
                                self.artist_tracker.update_artist_discovery(artist_name, "billboard", len(urls))
                        else:
                            logger.info(f"📊 Found 0 articles for {artist_name}")

                except Exception as e:
                    logger.error(f"Search failed for {artist_name}: {e}")

        return discovered_urls

    def _extract_urls_from_billboard_search(self, content: str) -> List[str]:
        """Extract article URLs from Billboard search results"""
        from bs4 import BeautifulSoup
        import re
        urls = []

        try:
            # Method 1: Look for JSON data in the page (common for JS-loaded content)
            if '"url"' in content and 'billboard.com' in content:
                # Extract URLs from JSON-like structures
                json_urls = re.findall(r'"url":\s*"(https://www\.billboard\.com/[^"]+)"', content)
                for url in json_urls:
                    if self._is_billboard_article_url(url):
                        urls.append(url)

            # Method 2: Look for direct URL references
            url_patterns = [
                r'https://www\.billboard\.com/music/[^"\s]+',
                r'https://www\.billboard\.com/pro/[^"\s]+',
                r'https://www\.billboard\.com/culture/[^"\s]+',
                r'/music/[^"\s]+',
                r'/pro/[^"\s]+',
                r'/culture/[^"\s]+'
            ]

            for pattern in url_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.startswith('/'):
                        full_url = "https://www.billboard.com" + match
                    else:
                        full_url = match

                    if self._is_billboard_article_url(full_url):
                        urls.append(full_url)

            # Method 3: Traditional HTML parsing (fallback)
            soup = BeautifulSoup(content, 'html.parser')
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')
                if href.startswith('/'):
                    full_url = "https://www.billboard.com" + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                if self._is_billboard_article_url(full_url):
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

    def _is_billboard_article_url(self, url: str) -> bool:
        """Check if URL is a Billboard article"""
        url_lower = url.lower()

        # Must be Billboard domain
        if 'billboard.com' not in url_lower:
            return False

        # Must be music-related content
        valid_paths = ['/music/', '/pro/', '/culture/', '/news/']
        if not any(path in url_lower for path in valid_paths):
            return False

        # Exclude non-article patterns
        exclude_patterns = [
            '/tag/', '/author/', '/category/', '/search/',
            '/newsletter', '/subscribe', '/contact', '/about',
            '/shop/', '/events/', '/awards/', '/chart/'
        ]
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # Must look like an article (has meaningful path structure)
        import re
        if re.search(r'/(music|pro|culture)/[^/]+/$', url_lower):
            return True

        # Or has content indicators
        if any(indicator in url_lower for indicator in ['/interview', '/review', '/feature', '/news']):
            return True

        return False

    async def _discover_from_music_sections(self) -> List[str]:
        """Discover URLs from Billboard music sections"""
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

    async def _discover_chart_content(self) -> List[str]:
        """Discover Billboard chart and industry content"""
        discovered_urls = []

        chart_sections = [
            "https://www.billboard.com/charts/",
            "https://www.billboard.com/pro/",
            "https://www.billboard.com/music/music-news/"
        ]

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            for section_url in chart_sections:
                try:
                    result = await fetcher.fetch_with_fallbacks(section_url)
                    if result.success and result.content:
                        urls = self._extract_article_urls_from_page(result.content, section_url)
                        discovered_urls.extend(urls)

                except Exception as e:
                    logger.debug(f"Error discovering chart content from {section_url}: {e}")

        return discovered_urls

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
                    full_url = urljoin("https://www.billboard.com", href)
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

        # Must contain music-related paths or be a Billboard article
        music_paths = ['/music/', '/pro/', '/culture/', '/charts/']
        if not any(path in url_lower for path in music_paths):
            return False

        # Must be a Billboard domain
        if 'billboard.com' not in url_lower:
            return False

        # Exclude non-article content
        exclude_patterns = [
            '/tag/', '/author/', '/category/', '/search/',
            '/newsletter', '/subscribe', '/contact', '/about',
            '/shop/', '/events/', '/awards/'
        ]
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # Include article indicators
        article_indicators = [
            '/music/', '/pro/', '/culture/', '/news/',
            '/interview', '/review', '/feature'
        ]

        return any(indicator in url_lower for indicator in article_indicators)

    async def enhance_extracted_content(self, content, fetch_result, extraction_result):
        """Enhance content with Billboard specific processing"""
        enhanced_content = await super().enhance_extracted_content(content, fetch_result, extraction_result)

        # Check for jazz artist mentions and update tracker
        if self.artist_tracker:
            detected_artists = self._detect_jazz_artists_in_content(enhanced_content)
            for artist_name in detected_artists:
                self.artist_tracker.update_artist_discovery(artist_name, "billboard", 1)
                logger.info(f"📊 Found {artist_name} in Billboard article: {enhanced_content.title}")

        # Add Billboard specific metadata
        enhanced_content.source_attribution.publication_type = "industry_magazine_article"

        # Billboard often has chart and industry focus
        text_lower = enhanced_content.content.lower()
        if any(term in text_lower for term in ['chart', 'billboard 200', 'hot 100', 'industry']):
            enhanced_content.source_attribution.publication_type = "industry_analysis"

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