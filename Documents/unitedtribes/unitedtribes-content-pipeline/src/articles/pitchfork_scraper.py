"""
Pitchfork Music Publication Scraper
Specialized scraper for Pitchfork reviews, features, and news
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re

from base_scraper import BaseArticleScraper, ScraperConfig, DiscoveryResult, PatternBasedDiscovery
from models import ScrapedContent, SourceAttribution, ContentType

logger = logging.getLogger(__name__)


class PitchforkScraper(BaseArticleScraper):
    """
    Specialized scraper for Pitchfork music content
    Focuses on album reviews, music features, and industry news
    """

    def __init__(self, artist_tracker=None):
        config = ScraperConfig(
            source_name="pitchfork",
            base_url="https://pitchfork.com",
            rate_limit=1.0,  # Respectful rate limiting
            max_articles_per_run=1000,
            content_discovery_urls=[
                "https://pitchfork.com/reviews/albums/",
                "https://pitchfork.com/features/",
                "https://pitchfork.com/news/",
                "https://pitchfork.com/thepitch/"
            ],
            custom_selectors={
                # Pitchfork-specific selectors based on deprecated scraper
                "title": "h1[data-testid='ContentHeaderHed'], h1.single-album-tombstone__review-title",
                "content": "[data-testid='ContentBody'], .contents-wrapper .review-detail",
                "author": "[data-testid='BylineWrapper'] a, .byline a",
                "date": "time[datetime], .pub-date time",
                "rating": ".score, .rating .score-value",
                "tags": ".tags a, .genre a, .tag-list a",
                "album_info": ".single-album-tombstone__meta, .album-info"
            },
            archive_bypass_enabled=True,
            validation_required=True
        )
        super().__init__(config)
        self.artist_tracker = artist_tracker

        # Jazz artists for targeted discovery
        self.jazz_artists = [
            "John Coltrane", "Lee Morgan", "Art Blakey", "Horace Silver", "Charlie Parker",
            "Grant Green", "Dexter Gordon", "Kenny Drew", "Paul Chambers", "Philly Joe Jones",
            "Herbie Hancock", "Freddie Hubbard", "Joe Henderson", "Donald Byrd", "Wayne Shorter",
            "Thelonious Monk", "Duke Ellington", "Dizzy Gillespie", "Joe Pass",
            "Miles Davis", "Bill Evans", "Cannonball Adderley", "Bill Charlap", "John Scofield", "Pat Metheny"
        ]

        # Pitchfork-specific patterns
        self.discovery = PatternBasedDiscovery(config.base_url, "pitchfork")

    async def discover_content_urls(self) -> DiscoveryResult:
        """
        Discover Pitchfork content URLs using artist search
        """
        logger.info("🎯 Discovering Pitchfork content...")

        all_urls = []

        # Strategy 1: Search for each of our 25 artists specifically
        logger.info("🔍 Searching Pitchfork for our 25 specific artists...")
        artist_search_urls = await self.discovery.discover_by_artist_search(self.jazz_artists)
        all_urls.extend(artist_search_urls)

        # Strategy 2: Discover from music sections
        logger.info("🎵 Exploring music sections...")
        section_search_urls = await self._discover_from_sections()
        all_urls.extend(section_search_urls)

        # Deduplicate and filter
        unique_urls = list(dict.fromkeys(all_urls))  # Preserve order, remove duplicates
        music_urls = [url for url in unique_urls if self._is_valid_pitchfork_url(url)]

        logger.info(f"🔍 Pitchfork discovery: {len(music_urls)} music URLs found from {len(all_urls)} total")

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
        """Search Pitchfork for each of our 25 jazz artists"""
        from fetcher import EnhancedFetcher
        discovered_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            for artist_name in self.jazz_artists:
                try:
                    # Use the exact search URL format provided by user
                    search_term = artist_name.replace(' ', '+')
                    search_url = f"https://pitchfork.com/search/?q={search_term}"

                    logger.info(f"🔍 Searching Pitchfork for: {artist_name}")
                    result = await fetcher.fetch_with_fallbacks(search_url)

                    if result.success and result.content:
                        # Extract URLs from Pitchfork search results
                        urls = self._extract_urls_from_pitchfork_search(result.content)

                        if urls:
                            discovered_urls.extend(urls)
                            logger.info(f"📊 Found {len(urls)} articles for {artist_name}")

                            # Update artist tracker
                            if self.artist_tracker:
                                self.artist_tracker.update_artist_discovery(artist_name, "pitchfork", len(urls))
                        else:
                            logger.info(f"📊 Found 0 articles for {artist_name}")

                except Exception as e:
                    logger.error(f"Search failed for {artist_name}: {e}")

        return discovered_urls

    def _extract_urls_from_pitchfork_search(self, content: str) -> List[str]:
        """Extract article URLs from Pitchfork search results"""
        from bs4 import BeautifulSoup
        import re
        urls = []

        try:
            # Method 1: Look for JSON data in the page (common for JS-loaded content)
            if '\"url\"' in content and 'pitchfork.com' in content:
                # Extract URLs from JSON-like structures
                json_urls = re.findall(r'\"url\":\s*\"(https://pitchfork\.com/[^\"]+)\"', content)
                for url in json_urls:
                    if self._is_valid_pitchfork_url(url):
                        urls.append(url)

            # Method 2: Look for direct URL references
            url_patterns = [
                r'https://pitchfork\.com/reviews/[^\"\\s]+',
                r'https://pitchfork\.com/features/[^\"\\s]+',
                r'https://pitchfork\.com/news/[^\"\\s]+',
                r'/reviews/[^\"\\s]+',
                r'/features/[^\"\\s]+',
                r'/news/[^\"\\s]+'
            ]

            for pattern in url_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.startswith('/'):
                        full_url = "https://pitchfork.com" + match
                    else:
                        full_url = match

                    if self._is_valid_pitchfork_url(full_url):
                        urls.append(full_url)

            # Method 3: Traditional HTML parsing (fallback)
            soup = BeautifulSoup(content, 'html.parser')
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')
                if href.startswith('/'):
                    full_url = "https://pitchfork.com" + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                if self._is_valid_pitchfork_url(full_url):
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

    async def _discover_from_sections(self) -> List[str]:
        """Discover URLs from Pitchfork section pages"""
        from fetcher import EnhancedFetcher
        from bs4 import BeautifulSoup

        section_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            for section_url in self.config.content_discovery_urls:
                try:
                    result = await fetcher.fetch_with_fallbacks(section_url)
                    if result.success and result.content:
                        soup = BeautifulSoup(result.content, 'html.parser')

                        # Extract article links from section pages
                        article_links = soup.find_all('a', href=True)
                        for link in article_links:
                            href = link.get('href')
                            if href:
                                full_url = urljoin(self.config.base_url, href)
                                if self._is_valid_pitchfork_url(full_url):
                                    section_urls.append(full_url)

                except Exception as e:
                    logger.debug(f"Section discovery failed for {section_url}: {e}")

        return section_urls

    def _is_valid_pitchfork_url(self, url: str) -> bool:
        """Check if URL is a valid Pitchfork article"""
        if not url.startswith('https://pitchfork.com'):
            return False

        # Valid patterns
        valid_patterns = [
            r'/reviews/albums/[^/]+/?$',  # Album reviews
            r'/reviews/tracks/[^/]+/?$',  # Track reviews
            r'/features/[^/]+/?$',        # Features
            r'/news/[^/]+/?$',           # News articles
            r'/thepitch/[^/]+/?$'        # The Pitch articles
        ]

        # Invalid patterns to exclude
        invalid_patterns = [
            r'/tag/',
            r'/search',
            r'/best/',
            r'/lists/',
            r'\.json$',
            r'\.xml$'
        ]

        # Check against invalid patterns first
        for pattern in invalid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        # Check against valid patterns
        for pattern in valid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        return False

    def _prioritize_urls(self, urls: List[str]) -> List[str]:
        """Prioritize URLs by content type importance"""
        reviews = []
        features = []
        news = []
        other = []

        for url in urls:
            if '/reviews/' in url:
                reviews.append(url)
            elif '/features/' in url:
                features.append(url)
            elif '/news/' in url:
                news.append(url)
            else:
                other.append(url)

        # Return in priority order: reviews, features, news, other
        return reviews + features + news + other

    async def enhance_extracted_content(
        self,
        content: ScrapedContent,
        fetch_result,
        extraction_result
    ) -> ScrapedContent:
        """
        Enhance content with Pitchfork-specific metadata
        """
        from bs4 import BeautifulSoup

        # Parse HTML for additional metadata
        soup = BeautifulSoup(fetch_result.content, 'html.parser')

        # Extract Pitchfork rating if present
        rating = self._extract_rating(soup)
        if rating:
            content.source_attribution.episode_info = {"rating": rating}

        # Determine content type based on URL and content
        content_type = self._determine_content_type(content.url, content.title)
        content.content_type = content_type

        # Extract album/artist info for reviews
        if content_type == ContentType.REVIEW:
            album_info = self._extract_album_info(soup, content.title)
            if album_info:
                if not content.source_attribution.episode_info:
                    content.source_attribution.episode_info = {}
                content.source_attribution.episode_info.update(album_info)

        # Set publication type
        content.source_attribution.publication_type = "article"
        content.source_attribution.content_type = content_type.value

        # Enhance source attribution
        content.source_attribution.source = "Pitchfork"

        # Check for jazz artist mentions and update tracker
        if self.artist_tracker:
            detected_artists = self._detect_jazz_artists_in_content(content)
            for artist_name in detected_artists:
                self.artist_tracker.update_artist_discovery(artist_name, "pitchfork", 1)
                logger.info(f"🎺 Found {artist_name} in Pitchfork article: {content.title}")

        return content

    def _extract_rating(self, soup) -> Optional[float]:
        """Extract Pitchfork rating from page"""
        rating_selectors = [
            '.score',
            '.rating .score-value',
            '[data-testid="ScoreCircle"]'
        ]

        for selector in rating_selectors:
            rating_elem = soup.select_one(selector)
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                try:
                    # Extract numeric rating
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        return float(rating_match.group(1))
                except ValueError:
                    continue

        return None

    def _determine_content_type(self, url: str, title: str) -> ContentType:
        """Determine content type based on URL and title"""
        if '/reviews/' in url:
            return ContentType.REVIEW
        elif '/features/' in url or 'interview' in title.lower():
            if 'interview' in title.lower() or 'talks' in title.lower():
                return ContentType.INTERVIEW
            return ContentType.ARTICLE
        elif '/news/' in url:
            return ContentType.NEWS
        else:
            return ContentType.ARTICLE

    def _extract_album_info(self, soup, title: str) -> Optional[Dict[str, Any]]:
        """Extract album information for reviews"""
        album_info = {}

        # Try to extract from title
        # Format usually: "Artist: Album Title"
        if ':' in title:
            parts = title.split(':', 1)
            if len(parts) == 2:
                album_info['artist'] = parts[0].strip()
                album_info['album'] = parts[1].strip()

        # Try to extract from album metadata section
        album_meta = soup.select_one('.single-album-tombstone__meta, .album-info')
        if album_meta:
            # Extract label, year, etc.
            meta_text = album_meta.get_text()

            # Look for year
            year_match = re.search(r'(19|20)\d{2}', meta_text)
            if year_match:
                album_info['year'] = year_match.group()

        return album_info if album_info else None

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
    """Test the Pitchfork scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    scraper = PitchforkScraper()

    try:
        # Run scraping with limited articles for testing
        batch = await scraper.scrape_articles(max_articles=5)

        print(f"\n🎯 Pitchfork Scraping Results:")
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