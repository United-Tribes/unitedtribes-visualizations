"""
NPR Podcast Scraper
Specialized for Fresh Air and music-related NPR content
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re
from bs4 import BeautifulSoup

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "shared"))
sys.path.append(str(Path(__file__).parent.parent / "articles"))

from base_scraper import BaseArticleScraper, ScraperConfig, DiscoveryResult
from models import ScrapedContent, SourceAttribution, ContentType
from fetcher import EnhancedFetcher

logger = logging.getLogger(__name__)


class NPRScraper(BaseArticleScraper):
    """
    NPR podcast and transcript scraper
    Focuses on Fresh Air, All Songs Considered, and music interviews
    """

    def __init__(self):
        config = ScraperConfig(
            source_name="NPR",
            base_url="https://www.npr.org",
            rate_limit=0.5,  # More conservative for NPR
            max_articles_per_run=20,
            content_discovery_urls=[
                "https://www.npr.org/podcasts/510019/fresh-air",
                "https://www.npr.org/podcasts/510019/fresh-air/archive",
                "https://www.npr.org/sections/music/",
                "https://feeds.npr.org/510019/podcast.xml"
            ],
            custom_selectors={
                "title": "h1.storytitle, h1.transcript-title, .episode-title h1",
                "content": ".storytext, .transcript-content, .episode-transcript",
                "author": ".byline a, .host-name",
                "date": "time[datetime], .dateblock time",
                "episode_info": ".episode-meta, .program-meta",
                "audio_link": "audio source, .audio-module-tools a"
            },
            archive_bypass_enabled=True,
            validation_required=True
        )
        super().__init__(config)

    async def discover_content_urls(self) -> DiscoveryResult:
        """
        Discover NPR podcast content URLs
        """
        logger.info("📻 Discovering NPR podcast content")

        all_urls = []
        discovery_methods = []

        # Strategy 1: Fresh Air RSS feed
        try:
            fresh_air_urls = await self._discover_fresh_air_episodes()
            all_urls.extend(fresh_air_urls)
            discovery_methods.append(f"fresh_air_rss:{len(fresh_air_urls)}")
            logger.info(f"🎙️ Fresh Air discovery: {len(fresh_air_urls)} episodes")
        except Exception as e:
            logger.warning(f"Fresh Air discovery failed: {e}")

        # Strategy 2: Music section pages
        try:
            music_urls = await self._discover_music_content()
            all_urls.extend(music_urls)
            discovery_methods.append(f"music_section:{len(music_urls)}")
            logger.info(f"🎵 Music section discovery: {len(music_urls)} articles")
        except Exception as e:
            logger.warning(f"Music section discovery failed: {e}")

        # Remove duplicates and filter for music relevance
        unique_urls = []
        seen = set()
        for url in all_urls:
            if url not in seen and self._is_music_relevant_url(url):
                unique_urls.append(url)
                seen.add(url)

        return DiscoveryResult(
            urls=unique_urls,
            method=",".join(discovery_methods),
            confidence=0.8 if len(unique_urls) > 5 else 0.5,
            metadata={
                "total_discovered": len(unique_urls),
                "methods_used": discovery_methods,
                "source": "npr"
            }
        )

    async def _discover_fresh_air_episodes(self) -> List[str]:
        """Discover Fresh Air episodes from RSS"""
        from xml.etree import ElementTree as ET

        episode_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            # Fresh Air podcast RSS feed
            rss_url = "https://feeds.npr.org/510019/podcast.xml"

            try:
                result = await fetcher.fetch_with_fallbacks(rss_url)
                if result.success and result.content:
                    root = ET.fromstring(result.content)

                    for item in root.iter('item'):
                        # Get episode URL
                        link_elem = item.find('link')
                        if link_elem is not None and link_elem.text:
                            episode_url = link_elem.text.strip()

                            # Get episode title to check for music relevance
                            title_elem = item.find('title')
                            title = title_elem.text if title_elem is not None else ""

                            if self._is_music_episode(title):
                                episode_urls.append(episode_url)

            except Exception as e:
                logger.debug(f"Fresh Air RSS parsing failed: {e}")

        return episode_urls[:15]  # Limit to recent episodes

    async def _discover_music_content(self) -> List[str]:
        """Discover music-related content from NPR music section"""
        music_urls = []

        async with EnhancedFetcher(rate_limit=self.config.rate_limit) as fetcher:
            music_section_url = "https://www.npr.org/sections/music/"

            try:
                result = await fetcher.fetch_with_fallbacks(music_section_url)
                if result.success and result.content:
                    soup = BeautifulSoup(result.content, 'html.parser')

                    # Find article links in music section
                    article_links = soup.find_all('a', href=True)
                    for link in article_links:
                        href = link.get('href')
                        if href and self._is_npr_article_url(href):
                            full_url = urljoin(self.config.base_url, href)
                            music_urls.append(full_url)

            except Exception as e:
                logger.debug(f"Music section discovery failed: {e}")

        return music_urls

    def _is_music_episode(self, title: str) -> bool:
        """Check if episode title indicates music content"""
        music_keywords = [
            'music', 'musician', 'singer', 'band', 'album', 'song',
            'concert', 'tour', 'jazz', 'rock', 'pop', 'classical',
            'composer', 'artist', 'performance', 'recording'
        ]

        title_lower = title.lower()
        return any(keyword in title_lower for keyword in music_keywords)

    def _is_music_relevant_url(self, url: str) -> bool:
        """Check if URL is likely to contain music content"""
        if '/sections/music/' in url:
            return True

        # Fresh Air episodes about music
        if '/fresh-air/' in url or '/510019/' in url:
            return True

        return False

    def _is_npr_article_url(self, url: str) -> bool:
        """Check if URL is a valid NPR article"""
        # NPR article URLs typically have this pattern
        npr_patterns = [
            r'/\d{4}/\d{2}/\d{2}/\d+/',  # Date-based URLs
            r'/sections/music/',
            r'/podcasts/510019/',  # Fresh Air
        ]

        return any(re.search(pattern, url) for pattern in npr_patterns)

    async def enhance_extracted_content(
        self,
        content: ScrapedContent,
        fetch_result,
        extraction_result
    ) -> ScrapedContent:
        """
        Enhance content with NPR-specific metadata
        """
        soup = BeautifulSoup(fetch_result.content, 'html.parser')

        # Determine if this is a podcast transcript
        is_transcript = self._is_transcript_content(soup, content.content)

        if is_transcript:
            content.content_type = ContentType.PODCAST_TRANSCRIPT
            content.source_attribution.publication_type = "podcast"

            # Extract episode metadata
            episode_info = self._extract_episode_info(soup)
            if episode_info:
                content.source_attribution.episode_info = episode_info

        # Extract host information
        host = self._extract_host_info(soup)
        if host:
            content.source_attribution.author = host

        # Set source
        content.source_attribution.source = "NPR"

        # If it's Fresh Air, be more specific
        if 'fresh-air' in content.url or 'Fresh Air' in content.title:
            content.source_attribution.source = "NPR Fresh Air"

        return content

    def _is_transcript_content(self, soup, content_text: str) -> bool:
        """Determine if content is a podcast transcript"""
        # Look for transcript indicators
        transcript_indicators = [
            'HOST:', 'GROSS:', 'TERRY GROSS',
            '(SOUNDBITE OF', 'UNIDENTIFIED PERSON',
            'transcript', 'INTERVIEW'
        ]

        content_upper = content_text.upper()

        # Check for multiple transcript indicators
        indicator_count = sum(1 for indicator in transcript_indicators
                            if indicator in content_upper)

        return indicator_count >= 2

    def _extract_episode_info(self, soup) -> Optional[Dict[str, Any]]:
        """Extract podcast episode information"""
        episode_info = {}

        # Look for episode metadata
        meta_section = soup.select_one('.episode-meta, .program-meta, .podcast-meta')
        if meta_section:
            meta_text = meta_section.get_text()

            # Extract duration if present
            duration_match = re.search(r'(\d+)\s*(?:minutes?|mins?)', meta_text, re.IGNORECASE)
            if duration_match:
                episode_info['duration_minutes'] = int(duration_match.group(1))

        # Look for show name
        if 'fresh-air' in soup.get_text().lower():
            episode_info['show'] = 'Fresh Air'
            episode_info['host'] = 'Terry Gross'

        # Look for audio links
        audio_link = soup.select_one('audio source, .audio-module-tools a')
        if audio_link:
            audio_url = audio_link.get('src') or audio_link.get('href')
            if audio_url:
                episode_info['audio_url'] = audio_url

        return episode_info if episode_info else None

    def _extract_host_info(self, soup) -> Optional[str]:
        """Extract podcast host information"""
        # Look for host in byline
        byline = soup.select_one('.byline a, .host-name')
        if byline:
            return byline.get_text(strip=True)

        # Check for Terry Gross specifically
        if 'TERRY GROSS' in soup.get_text().upper():
            return 'Terry Gross'

        return None


async def main():
    """Test NPR scraper"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    scraper = NPRScraper()

    try:
        batch = await scraper.scrape_articles(max_articles=3)

        print(f"\n📻 NPR Scraping Results:")
        print(f"========================")

        stats = scraper.get_statistics()
        print(f"Discovered: {stats['discovered']}")
        print(f"Scraped: {stats['extracted']}")
        print(f"Success Rate: {stats['end_to_end_success']:.2%}")

        if batch.content_items:
            print(f"\nSample episode:")
            item = batch.content_items[0]
            print(f"  Title: {item.title}")
            print(f"  Type: {item.content_type}")
            print(f"  Source: {item.source_attribution.source}")

            if item.source_attribution.episode_info:
                print(f"  Episode Info: {item.source_attribution.episode_info}")

    except Exception as e:
        print(f"❌ NPR scraper test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())