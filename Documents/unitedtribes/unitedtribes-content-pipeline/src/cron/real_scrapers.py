"""
Real Content Scrapers for Jazz Artist Discovery
Implements actual content fetching and artist detection
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import aiohttp

# Import shared components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "shared"))
sys.path.append(str(Path(__file__).parent.parent / "articles"))

from models import ScrapedContent, SourceAttribution, ContentType
from fetcher import EnhancedFetcher
from extractor import EnhancedContentExtractor

# Import the new scrapers
try:
    from rolling_stone_scraper import RollingStoneScraper
    from billboard_scraper import BillboardScraper
    from pitchfork_scraper import PitchforkScraper
    from npr_scraper import NPRScraper
except ImportError:
    # Fallback if imports fail
    RollingStoneScraper = None
    BillboardScraper = None
    PitchforkScraper = None
    NPRScraper = None

logger = logging.getLogger(__name__)


class RealPitchforkScraper:
    """
    Real Pitchfork scraper using the comprehensive article scraper
    """

    def __init__(self, artist_tracker):
        self.artist_tracker = artist_tracker
        self.scraper = None

    async def discover_jazz_content(self, max_articles: int = 30) -> List[ScrapedContent]:
        """
        Discover jazz content from Pitchfork using the article scraper
        """
        logger.info(f"🎯 Starting Pitchfork jazz content discovery (max: {max_articles})")

        if PitchforkScraper is None:
            logger.error("Pitchfork scraper not available")
            return []

        try:
            # Initialize scraper with artist tracker
            self.scraper = PitchforkScraper(self.artist_tracker)

            # Run the scraper
            batch = await self.scraper.scrape_articles(max_articles)

            # Extract content items
            scraped_items = batch.content_items if batch else []

            logger.info(f"✅ Pitchfork discovery complete: {len(scraped_items)} jazz articles found")
            return scraped_items

        except Exception as e:
            logger.error(f"Pitchfork scraper failed: {e}")
            return []


class RealNPRScraper:
    """
    Real NPR scraper focusing on Fresh Air and music content
    """

    def __init__(self, artist_tracker):
        self.artist_tracker = artist_tracker
        self.fetcher = None
        self.extractor = EnhancedContentExtractor()

        # Same jazz artists list
        self.jazz_artists = [
            "John Coltrane", "Lee Morgan", "Art Blakey", "Horace Silver", "Charlie Parker",
            "Grant Green", "Dexter Gordon", "Kenny Drew", "Paul Chambers", "Philly Joe Jones",
            "Herbie Hancock", "Freddie Hubbard", "Joe Henderson", "Donald Byrd", "Wayne Shorter",
            "Thelonious Monk", "Duke Ellington", "Dizzy Gillespie", "Joe Pass",
            "Miles Davis", "Bill Evans", "Cannonball Adderley", "Bill Charlap", "John Scofield", "Pat Metheny"
        ]

        self.artist_patterns = {}
        for artist in self.jazz_artists:
            pattern = artist.replace(" ", r"\s+")
            self.artist_patterns[artist] = re.compile(rf"\b{pattern}\b", re.IGNORECASE)

    async def discover_jazz_content(self, max_articles: int = 30) -> List[ScrapedContent]:
        """
        Discover jazz content from NPR
        """
        logger.info(f"🎯 Starting NPR jazz content discovery (max: {max_articles})")

        scraped_items = []

        async with EnhancedFetcher(rate_limit=0.5) as fetcher:  # More conservative for NPR
            self.fetcher = fetcher

            # Strategy 1: Fresh Air RSS feed
            fresh_air_content = await self._discover_from_fresh_air()
            scraped_items.extend(fresh_air_content)

            # Strategy 2: NPR Music section
            music_content = await self._discover_from_music_section()
            scraped_items.extend(music_content)

        # Filter and deduplicate
        unique_items = self._deduplicate_content(scraped_items)
        jazz_items = self._filter_jazz_content(unique_items)

        # Limit results
        final_items = jazz_items[:max_articles]

        logger.info(f"✅ NPR discovery complete: {len(final_items)} jazz articles found")
        return final_items

    async def _discover_from_fresh_air(self) -> List[ScrapedContent]:
        """Discover from Fresh Air podcast feed"""
        logger.info("🎙️ Checking Fresh Air episodes...")

        try:
            rss_url = "https://feeds.npr.org/510019/podcast.xml"
            result = await self.fetcher.fetch_with_fallbacks(rss_url)

            if not result.success:
                logger.warning("Failed to fetch Fresh Air RSS")
                return []

            urls = self._extract_urls_from_rss(result.content)
            scraped_items = []

            # Check recent episodes for jazz content
            for url in urls[:15]:  # Check recent episodes
                try:
                    content = await self._scrape_npr_episode(url)
                    if content:
                        artist_names = self._detect_artists_in_content(content)
                        if artist_names:
                            for artist_name in artist_names:
                                self.artist_tracker.update_artist_discovery(artist_name, "npr", 1)
                            scraped_items.append(content)

                except Exception as e:
                    logger.debug(f"Error scraping Fresh Air episode {url}: {e}")

            logger.info(f"📊 Fresh Air: {len(scraped_items)} jazz episodes found")
            return scraped_items

        except Exception as e:
            logger.error(f"Error in Fresh Air discovery: {e}")
            return []

    async def _discover_from_music_section(self) -> List[ScrapedContent]:
        """Discover from NPR Music section"""
        logger.info("🎵 Checking NPR Music section...")

        try:
            result = await self.fetcher.fetch_with_fallbacks("https://www.npr.org/sections/music/")

            if not result.success:
                logger.warning("Failed to fetch NPR Music section")
                return []

            soup = BeautifulSoup(result.content, 'html.parser')

            # Find article links
            article_links = soup.find_all('a', href=True)
            urls_to_check = []

            for link in article_links:
                href = link.get('href', '')
                if '/sections/music/' in href or any(year in href for year in ['2024', '2023']):
                    full_url = urljoin("https://www.npr.org", href)
                    urls_to_check.append(full_url)

            # Limit and check URLs
            urls_to_check = urls_to_check[:15]
            scraped_items = []

            for url in urls_to_check:
                try:
                    content = await self._scrape_npr_article(url)
                    if content:
                        artist_names = self._detect_artists_in_content(content)
                        if artist_names:
                            for artist_name in artist_names:
                                self.artist_tracker.update_artist_discovery(artist_name, "npr", 1)
                            scraped_items.append(content)

                except Exception as e:
                    logger.debug(f"Error scraping NPR article {url}: {e}")

            logger.info(f"📊 NPR Music: {len(scraped_items)} jazz articles found")
            return scraped_items

        except Exception as e:
            logger.error(f"Error in NPR Music discovery: {e}")
            return []

    async def _scrape_npr_episode(self, url: str) -> Optional[ScrapedContent]:
        """Scrape NPR episode/article"""
        return await self._scrape_npr_article(url)

    async def _scrape_npr_article(self, url: str) -> Optional[ScrapedContent]:
        """Scrape NPR article"""
        try:
            result = await self.fetcher.fetch_with_fallbacks(url)

            if not result.success or not result.content:
                return None

            # Extract content
            extraction_result = self.extractor.extract_content(
                html=result.content,
                url=url,
                source_name="NPR"
            )

            if extraction_result.success and extraction_result.content:
                return extraction_result.content

        except Exception as e:
            logger.debug(f"Error scraping NPR content {url}: {e}")

        return None

    def _extract_urls_from_rss(self, rss_content: str) -> List[str]:
        """Extract URLs from RSS XML"""
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(rss_content)

            urls = []
            for item in root.iter('item'):
                link_elem = item.find('link')
                if link_elem is not None and link_elem.text:
                    urls.append(link_elem.text.strip())

            return urls

        except Exception as e:
            logger.debug(f"RSS parsing error: {e}")
            return []

    def _detect_artists_in_content(self, content: ScrapedContent) -> List[str]:
        """Detect which jazz artists are mentioned in content"""
        text = (content.title + " " + content.content).lower()
        detected_artists = []

        for artist_name, pattern in self.artist_patterns.items():
            if pattern.search(text):
                detected_artists.append(artist_name)

        return detected_artists

    def _filter_jazz_content(self, content_items: List[ScrapedContent]) -> List[ScrapedContent]:
        """Filter content for jazz relevance"""
        jazz_items = []

        for item in content_items:
            # Check if any jazz artists are mentioned
            if self._detect_artists_in_content(item):
                jazz_items.append(item)
                continue

            # Check for jazz keywords
            text = (item.title + " " + item.content).lower()
            jazz_keywords = [
                'jazz', 'bebop', 'hard bop', 'blue note', 'fresh air',
                'terry gross', 'saxophone', 'trumpet', 'pianist'
            ]

            if any(keyword in text for keyword in jazz_keywords):
                jazz_items.append(item)

        return jazz_items

    def _deduplicate_content(self, content_items: List[ScrapedContent]) -> List[ScrapedContent]:
        """Remove duplicate content based on URL"""
        seen_urls = set()
        unique_items = []

        for item in content_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)

        return unique_items

class RealRollingStoneScraper:
    """
    Real Rolling Stone scraper using the comprehensive article scraper
    """

    def __init__(self, artist_tracker):
        self.artist_tracker = artist_tracker
        self.scraper = None

    async def discover_jazz_content(self, max_articles: int = 30) -> List[ScrapedContent]:
        """
        Discover jazz content from Rolling Stone using the article scraper
        """
        logger.info(f"🎸 Starting Rolling Stone jazz content discovery (max: {max_articles})")

        if RollingStoneScraper is None:
            logger.error("Rolling Stone scraper not available")
            return []

        try:
            # Initialize scraper with artist tracker
            self.scraper = RollingStoneScraper(self.artist_tracker)

            # Run the scraper
            batch = await self.scraper.scrape_articles(max_articles)

            # Extract content items
            scraped_items = batch.content_items if batch else []

            logger.info(f"✅ Rolling Stone discovery complete: {len(scraped_items)} jazz articles found")
            return scraped_items

        except Exception as e:
            logger.error(f"Rolling Stone scraper failed: {e}")
            return []

    def _create_sample_content(self, max_articles: int) -> List[ScrapedContent]:
        """Create sample Rolling Stone content"""
        from datetime import datetime
        sample_items = []

        for i in range(min(3, max_articles)):
            attribution = SourceAttribution(
                source="Rolling Stone",
                title=f"Sample Rolling Stone Article {i+1}: Jazz Legend Analysis",
                url=f"https://rollingstone.com/sample-jazz-article-{i+1}",
                author="Rolling Stone Writer",
                publication_date=datetime.utcnow().isoformat(),
                publication_type="magazine_article"
            )

            content = ScrapedContent(
                url=f"https://rollingstone.com/sample-jazz-article-{i+1}",
                title=f"Sample Rolling Stone Article {i+1}: Jazz Legend Analysis",
                content=f"""This is a sample Rolling Stone article {i+1} demonstrating jazz coverage.
                Rolling Stone's unique perspective on jazz history, artist profiles {i+1}, and
                music industry analysis. Article {i+1} covers legendary musicians, album reviews,
                and cultural impact analysis specific to sample {i+1}.""",
                content_type=ContentType.ARTICLE,
                source_attribution=attribution,
                confidence_score=0.7
            )

            sample_items.append(content)

        return sample_items


class RealBillboardScraper:
    """
    Real Billboard scraper using the comprehensive article scraper
    """

    def __init__(self, artist_tracker):
        self.artist_tracker = artist_tracker
        self.scraper = None

    async def discover_jazz_content(self, max_articles: int = 30) -> List[ScrapedContent]:
        """
        Discover jazz content from Billboard using the article scraper
        """
        logger.info(f"📊 Starting Billboard jazz content discovery (max: {max_articles})")

        if BillboardScraper is None:
            logger.error("Billboard scraper not available")
            return []

        try:
            # Initialize scraper with artist tracker
            self.scraper = BillboardScraper(self.artist_tracker)

            # Run the scraper
            batch = await self.scraper.scrape_articles(max_articles)

            # Extract content items
            scraped_items = batch.content_items if batch else []

            logger.info(f"✅ Billboard discovery complete: {len(scraped_items)} jazz articles found")
            return scraped_items

        except Exception as e:
            logger.error(f"Billboard scraper failed: {e}")
            return []

    def _create_sample_content(self, max_articles: int) -> List[ScrapedContent]:
        """Create sample Billboard content"""
        from datetime import datetime
        sample_items = []

        for i in range(min(3, max_articles)):
            attribution = SourceAttribution(
                source="Billboard",
                title=f"Sample Billboard Article {i+1}: Jazz Industry Analysis",
                url=f"https://billboard.com/sample-jazz-industry-{i+1}",
                author="Billboard Staff",
                publication_date=datetime.utcnow().isoformat(),
                publication_type="industry_magazine_article"
            )

            content = ScrapedContent(
                url=f"https://billboard.com/sample-jazz-industry-{i+1}",
                title=f"Sample Billboard Article {i+1}: Jazz Industry Analysis",
                content=f"""This is a sample Billboard article {i+1} showcasing jazz industry coverage.
                Billboard's focus on charts, sales data, and industry trends for jazz music {i+1}.
                Analysis {i+1} includes market performance, artist commercial success, and
                jazz's position in the music industry for sample {i+1}.""",
                content_type=ContentType.ARTICLE,
                source_attribution=attribution,
                confidence_score=0.7
            )

            sample_items.append(content)

        return sample_items
