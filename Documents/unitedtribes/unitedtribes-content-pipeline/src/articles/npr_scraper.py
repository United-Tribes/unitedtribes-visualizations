"""
NPR Article Scraper
Implements real content discovery for NPR music coverage
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


class NPRScraper(BaseArticleScraper):
    """
    NPR scraper with comprehensive music content discovery
    """

    def __init__(self, artist_tracker=None):
        config = ScraperConfig(
            source_name="npr",
            base_url="https://www.npr.org",
            rate_limit=1.0,
            max_articles_per_run=1000,
            content_discovery_urls=[
                "https://www.npr.org/sections/music/",
                "https://www.npr.org/sections/music-interviews/",
                "https://www.npr.org/sections/music-reviews/",
                "https://www.npr.org/sections/jazz/"
            ]
        )
        super().__init__(config)
        self.artist_tracker = artist_tracker
        self.pattern_discovery = PatternBasedDiscovery(config.base_url, "npr")

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
        Discover NPR content URLs using artist search
        """
        logger.info("📻 Discovering NPR content...")

        all_urls = []

        # Strategy 1: Search for each of our 25 artists specifically
        logger.info("🔍 Searching NPR for our 25 specific artists...")
        artist_search_urls = await self.pattern_discovery.discover_by_artist_search(self.jazz_artists)
        all_urls.extend(artist_search_urls)

        # Strategy 2: Discover from music sections
        logger.info("🎵 Exploring music sections...")
        section_search_urls = await self._discover_from_music_sections()
        all_urls.extend(section_search_urls)

        # Deduplicate and filter
        unique_urls = list(dict.fromkeys(all_urls))  # Preserve order, remove duplicates
        music_urls = [url for url in unique_urls if self._is_music_relevant_url(url)]

        logger.info(f"🔍 NPR discovery: {len(music_urls)} music URLs found from {len(all_urls)} total")

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

    async def _search_for_artists(self) -> List[str]:
        """Search NPR for each of our 25 jazz artists"""
        discovered_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            for artist_name in self.jazz_artists:
                try:
                    # Use the exact search URL format provided by user
                    search_term = artist_name.replace(' ', '%20')
                    search_url = f"https://www.npr.org/search/?query={search_term}&page=1"

                    logger.info(f"🔍 Searching NPR for: {artist_name}")
                    result = await fetcher.fetch_with_fallbacks(search_url)

                    if result.success and result.content:
                        # Extract URLs from NPR search results
                        urls = self._extract_urls_from_npr_search(result.content)

                        if urls:
                            discovered_urls.extend(urls)
                            logger.info(f"📊 Found {len(urls)} articles for {artist_name}")

                            # Update artist tracker
                            if self.artist_tracker:
                                self.artist_tracker.update_artist_discovery(artist_name, "npr", len(urls))
                        else:
                            logger.info(f"📊 Found 0 articles for {artist_name}")

                except Exception as e:
                    logger.error(f"Search failed for {artist_name}: {e}")

        return discovered_urls

    def _extract_urls_from_npr_search(self, content: str) -> List[str]:
        """Extract article URLs from NPR search results"""
        from bs4 import BeautifulSoup
        import re
        urls = []

        try:
            # Method 1: Look for JSON data in the page (common for JS-loaded content)
            if '"url"' in content and 'npr.org' in content:
                # Extract URLs from JSON-like structures
                json_urls = re.findall(r'"url":\s*"(https://www\.npr\.org/[^"]+)"', content)
                for url in json_urls:
                    if self._is_npr_article_url(url):
                        urls.append(url)

            # Method 2: Look for direct URL references
            url_patterns = [
                r'https://www\.npr\.org/\d{4}/\d{2}/\d{2}/[^"\s]+',
                r'https://www\.npr\.org/sections/[^"\s]+',
                r'/\d{4}/\d{2}/\d{2}/[^"\s]+',
                r'/sections/[^"\s]+'
            ]

            for pattern in url_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.startswith('/'):
                        full_url = "https://www.npr.org" + match
                    else:
                        full_url = match

                    if self._is_npr_article_url(full_url):
                        urls.append(full_url)

            # Method 3: Traditional HTML parsing (fallback)
            soup = BeautifulSoup(content, 'html.parser')
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')
                if href.startswith('/'):
                    full_url = "https://www.npr.org" + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                if self._is_npr_article_url(full_url):
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

    def _is_npr_article_url(self, url: str) -> bool:
        """Check if URL is an NPR article"""
        url_lower = url.lower()

        # Must be NPR domain
        if 'npr.org' not in url_lower:
            return False

        # NPR article patterns
        import re

        # Standard NPR article pattern: /YYYY/MM/DD/article-id/title
        if re.search(r'/\d{4}/\d{2}/\d{2}/\d+/', url_lower):
            return True

        # Section articles: /sections/section-name/article
        if re.search(r'/sections/[^/]+/\d{4}/\d{2}/\d{2}/', url_lower):
            return True

        # Music-specific sections
        music_sections = ['/sections/music', '/sections/jazz', '/sections/music-interviews', '/sections/music-reviews']
        if any(section in url_lower for section in music_sections):
            return True

        return False

    async def _discover_from_music_sections(self) -> List[str]:
        """Discover URLs from NPR music sections"""
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
                    full_url = urljoin("https://www.npr.org", href)
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
        music_paths = ['/sections/music', '/sections/jazz', '/sections/music-interviews', '/sections/music-reviews']
        music_keywords = ['music', 'jazz', 'album', 'song', 'artist', 'concert', 'performance']

        # Check for music sections
        if any(path in url_lower for path in music_paths):
            return True

        # Check for music keywords in URL or if it's a regular NPR article (let content filtering handle relevance)
        if any(keyword in url_lower for keyword in music_keywords):
            return True

        # Include general NPR articles for broader coverage (we'll filter by content)
        import re
        if re.search(r'/\d{4}/\d{2}/\d{2}/\d+/', url_lower):
            return True

        # Exclude non-article content
        exclude_patterns = [
            '/tag/', '/author/', '/category/', '/search/',
            '/newsletter', '/subscribe', '/contact', '/about',
            '/donate', '/support', '/programs/', '/stations/'
        ]
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        return False

    async def enhance_extracted_content(self, content, fetch_result, extraction_result):
        """Enhance content with NPR specific processing"""
        enhanced_content = await super().enhance_extracted_content(content, fetch_result, extraction_result)

        # Check for jazz artist mentions and update tracker
        if self.artist_tracker:
            detected_artists = self._detect_jazz_artists_in_content(enhanced_content)
            for artist_name in detected_artists:
                self.artist_tracker.update_artist_discovery(artist_name, "npr", 1)
                logger.info(f"📻 Found {artist_name} in NPR article: {enhanced_content.title}")

        # Add NPR specific metadata
        enhanced_content.source_attribution.publication_type = "public_radio_article"

        # NPR often has interview and in-depth coverage
        text_lower = enhanced_content.content.lower()
        if any(term in text_lower for term in ['interview', 'conversation', 'talks with', 'speaks with']):
            enhanced_content.source_attribution.publication_type = "interview"

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


async def main():
    """Test the NPR scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    scraper = NPRScraper()

    try:
        # Run scraping with limited articles for testing
        batch = await scraper.scrape_articles(max_articles=5)

        print(f"\n📻 NPR Scraping Results:")
        print(f"===============================")

        stats = scraper.get_statistics()
        print(f"Discovered: {stats['discovered']}")
        print(f"Fetched: {stats['fetched']}")
        print(f"Extracted: {stats['extracted']}")
        print(f"Validated: {stats['validated']}")
        print(f"Uploaded: {stats['uploaded']}")
        print(f"Success Rate: {stats['end_to_end_success']:.2%}")

        if stats['errors']:
            print(f"\nErrors encountered:")
            for error in stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")

        if batch.content_items:
            print(f"\nSample content:")
            item = batch.content_items[0]
            print(f"  Title: {item.title[:80]}...")
            print(f"  Type: {item.content_type}")
            print(f"  S3 Key: {item.s3_key}")
            print(f"  Confidence: {item.confidence_score:.2f}")

    except Exception as e:
        print(f"❌ Scraper test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())