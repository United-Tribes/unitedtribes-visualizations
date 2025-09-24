"""
Direct Search Fallback for Artist Discovery
Bypasses EnhancedFetcher issues by using direct HTTP requests for search URLs
"""

import asyncio
import aiohttp
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DirectSearchFallback:
    """
    Direct HTTP search implementation that bypasses EnhancedFetcher issues
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.search_patterns = {
            'pitchfork': 'https://pitchfork.com/search/?q={}',
            'rolling_stone': 'https://www.rollingstone.com/results/?q={}',
            'billboard': 'https://www.billboard.com/results/?q={}&size=n_10_n&sort-field=relevance&sort-direction=desc',
            'npr': 'https://www.npr.org/search/?query={}&page=1'
        }

    async def search_for_artist(self, source: str, artist_name: str) -> List[str]:
        """
        Search for an artist using direct HTTP and extract article URLs
        """
        if source not in self.search_patterns:
            logger.warning(f"Unsupported source: {source}")
            return []

        search_url = self.search_patterns[source].format(quote_plus(artist_name))
        logger.info(f"🔍 Direct search for {artist_name} on {source}: {search_url}")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }

                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"✅ Got {len(content)} characters from {source} search")

                        # Extract URLs based on source
                        urls = self._extract_urls_by_source(source, content)
                        logger.info(f"📊 Extracted {len(urls)} URLs for {artist_name} from {source}")
                        return urls

                    else:
                        logger.warning(f"Search failed for {artist_name} on {source}: HTTP {response.status}")
                        return []

        except Exception as e:
            logger.error(f"Direct search failed for {artist_name} on {source}: {e}")
            return []

    def _extract_urls_by_source(self, source: str, content: str) -> List[str]:
        """
        Extract article URLs from search results based on source-specific patterns
        """
        urls = []

        try:
            if source == 'pitchfork':
                urls = self._extract_pitchfork_urls(content)
            elif source == 'rolling_stone':
                urls = self._extract_rolling_stone_urls(content)
            elif source == 'billboard':
                urls = self._extract_billboard_urls(content)
            elif source == 'npr':
                urls = self._extract_npr_urls(content)

        except Exception as e:
            logger.error(f"URL extraction failed for {source}: {e}")

        return urls

    def _extract_pitchfork_urls(self, content: str) -> List[str]:
        """Extract Pitchfork article URLs"""
        urls = []

        # Method 1: Look for JSON data
        if '"url"' in content and 'pitchfork.com' in content:
            json_urls = re.findall(r'"url":\s*"(https://pitchfork\.com/[^"]+)"', content)
            for url in json_urls:
                if self._is_valid_pitchfork_url(url):
                    urls.append(url)

        # Method 2: Direct URL patterns
        url_patterns = [
            r'https://pitchfork\.com/reviews/[^"\s]+',
            r'https://pitchfork\.com/features/[^"\s]+',
            r'https://pitchfork\.com/news/[^"\s]+',
            r'/reviews/[^"\s]+',
            r'/features/[^"\s]+',
            r'/news/[^"\s]+'
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

        return list(dict.fromkeys(urls))  # Remove duplicates

    def _extract_rolling_stone_urls(self, content: str) -> List[str]:
        """Extract Rolling Stone article URLs"""
        urls = []

        # Look for Rolling Stone article patterns
        url_patterns = [
            r'https://www\.rollingstone\.com/music/[^"\s]+',
            r'https://www\.rollingstone\.com/culture/[^"\s]+',
            r'/music/[^"\s]+',
            r'/culture/[^"\s]+'
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match.startswith('/'):
                    full_url = "https://www.rollingstone.com" + match
                else:
                    full_url = match

                if self._is_valid_rolling_stone_url(full_url):
                    urls.append(full_url)

        return list(dict.fromkeys(urls))

    def _extract_billboard_urls(self, content: str) -> List[str]:
        """Extract Billboard article URLs"""
        urls = []

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

                if self._is_valid_billboard_url(full_url):
                    urls.append(full_url)

        return list(dict.fromkeys(urls))

    def _extract_npr_urls(self, content: str) -> List[str]:
        """Extract NPR article URLs"""
        urls = []

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

                if self._is_valid_npr_url(full_url):
                    urls.append(full_url)

        return list(dict.fromkeys(urls))

    def _is_valid_pitchfork_url(self, url: str) -> bool:
        """Validate Pitchfork URLs"""
        if not url.startswith('https://pitchfork.com'):
            return False

        valid_patterns = [
            r'/reviews/albums/[^/]+/?$',
            r'/reviews/tracks/[^/]+/?$',
            r'/features/[^/]+/?$',
            r'/news/[^/]+/?$',
            r'/thepitch/[^/]+/?$'
        ]

        invalid_patterns = ['/tag/', '/search', '/best/', '/lists/', '.json$', '.xml$']

        for pattern in invalid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        for pattern in valid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        return False

    def _is_valid_rolling_stone_url(self, url: str) -> bool:
        """Validate Rolling Stone URLs"""
        if 'rollingstone.com' not in url:
            return False

        valid_paths = ['/music/', '/culture/', '/news/']
        exclude_patterns = ['/tag/', '/author/', '/search/', '/newsletter']

        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False

        return any(path in url.lower() for path in valid_paths)

    def _is_valid_billboard_url(self, url: str) -> bool:
        """Validate Billboard URLs"""
        if 'billboard.com' not in url:
            return False

        valid_paths = ['/music/', '/pro/', '/culture/', '/news/']
        exclude_patterns = ['/tag/', '/author/', '/search/', '/shop/', '/events/', '/awards/']

        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False

        return any(path in url.lower() for path in valid_paths)

    def _is_valid_npr_url(self, url: str) -> bool:
        """Validate NPR URLs"""
        if 'npr.org' not in url:
            return False

        # NPR article patterns
        import re
        if re.search(r'/\d{4}/\d{2}/\d{2}/\d+/', url.lower()):
            return True

        if re.search(r'/sections/[^/]+/\d{4}/\d{2}/\d{2}/', url.lower()):
            return True

        music_sections = ['/sections/music', '/sections/jazz', '/sections/music-interviews']
        if any(section in url.lower() for section in music_sections):
            return True

        return False


async def test_direct_search():
    """
    Test the direct search fallback
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    fallback = DirectSearchFallback()

    test_artists = ["John Coltrane", "Miles Davis", "Patti Smith"]
    test_sources = ["pitchfork", "rolling_stone"]

    for source in test_sources:
        for artist in test_artists:
            print(f"\n🔍 Testing {source} search for {artist}:")
            urls = await fallback.search_for_artist(source, artist)
            print(f"Found {len(urls)} URLs:")
            for url in urls[:3]:  # Show first 3
                print(f"  - {url}")


if __name__ == "__main__":
    asyncio.run(test_direct_search())