"""
Enhanced HTTP Fetcher with MissionLocal paywall bypass techniques
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import time
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result from HTTP fetch operation"""
    success: bool
    content: Optional[str] = None
    status_code: Optional[int] = None
    url: str = ""
    final_url: str = ""  # After redirects
    method: str = "direct"  # direct, archive_ph, archive_org, cached
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EnhancedFetcher:
    """
    HTTP fetcher with multiple fallback strategies for content access
    Incorporates MissionLocal techniques for paywall circumvention
    """

    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit  # requests per second
        self.last_request_time = 0.0
        self.session = None

        # Headers for legitimate browsing behavior
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=30, connect=10),
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_with_fallbacks(self, url: str) -> FetchResult:
        """
        Fetch content using multiple fallback strategies
        Inspired by MissionLocal's archive.ph approach
        """
        strategies = [
            self._fetch_direct,
            self._fetch_via_archive_ph,
            self._fetch_via_archive_org,
            self._fetch_via_google_cache
        ]

        for strategy in strategies:
            try:
                result = await strategy(url)
                if result.success and result.content and len(result.content) > 500:
                    logger.info(f"Successfully fetched {url} via {result.method}")
                    return result
                else:
                    logger.debug(f"Strategy {strategy.__name__} failed for {url}")
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} error for {url}: {e}")

        # All strategies failed
        return FetchResult(
            success=False,
            url=url,
            error_message="All fetch strategies failed",
            method="none"
        )

    async def _fetch_direct(self, url: str) -> FetchResult:
        """Direct fetch (try first)"""
        await self._respect_rate_limit()

        try:
            async with self.session.get(url) as response:
                content = await response.text()

                return FetchResult(
                    success=response.status == 200,
                    content=content if response.status == 200 else None,
                    status_code=response.status,
                    url=url,
                    final_url=str(response.url),
                    method="direct",
                    metadata={"response_headers": dict(response.headers)}
                )

        except Exception as e:
            return FetchResult(
                success=False,
                url=url,
                error_message=str(e),
                method="direct"
            )

    async def _fetch_via_archive_ph(self, url: str) -> FetchResult:
        """
        Fetch via archive.ph (MissionLocal technique)
        Excellent for bypassing paywalls
        """
        await self._respect_rate_limit()

        try:
            # archive.ph strategy
            archive_url = f"https://archive.ph/newest/{url}"

            async with self.session.get(archive_url, allow_redirects=True) as response:
                content = await response.text()

                # Check if we got redirected to an archived version
                if response.status == 200 and 'archive.ph' in str(response.url) and str(response.url) != archive_url:
                    logger.info(f"Found archived version at archive.ph for {url}")
                    return FetchResult(
                        success=True,
                        content=content,
                        status_code=response.status,
                        url=url,
                        final_url=str(response.url),
                        method="archive_ph",
                        metadata={"archive_url": str(response.url)}
                    )

                return FetchResult(
                    success=False,
                    url=url,
                    error_message="Not found in archive.ph",
                    method="archive_ph"
                )

        except Exception as e:
            return FetchResult(
                success=False,
                url=url,
                error_message=f"Archive.ph error: {e}",
                method="archive_ph"
            )

    async def _fetch_via_archive_org(self, url: str) -> FetchResult:
        """Fetch via Internet Archive Wayback Machine"""
        await self._respect_rate_limit()

        try:
            # Try Wayback Machine
            wayback_url = f"https://web.archive.org/web/{url}"

            async with self.session.get(wayback_url) as response:
                if response.status == 200:
                    content = await response.text()

                    # Wayback Machine includes their navigation - try to extract original content
                    soup = BeautifulSoup(content, 'html.parser')

                    # Remove Wayback toolbar
                    for toolbar in soup.select('#wm-ipp-base, .wb-autocomplete-suggestions'):
                        toolbar.decompose()

                    cleaned_content = str(soup)

                    return FetchResult(
                        success=True,
                        content=cleaned_content,
                        status_code=response.status,
                        url=url,
                        final_url=str(response.url),
                        method="archive_org",
                        metadata={"wayback_url": str(response.url)}
                    )

                return FetchResult(
                    success=False,
                    url=url,
                    error_message="Not found in Archive.org",
                    method="archive_org"
                )

        except Exception as e:
            return FetchResult(
                success=False,
                url=url,
                error_message=f"Archive.org error: {e}",
                method="archive_org"
            )

    async def _fetch_via_google_cache(self, url: str) -> FetchResult:
        """Fetch via Google Cache"""
        await self._respect_rate_limit()

        try:
            # Google cache URL
            cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{quote_plus(url)}"

            async with self.session.get(cache_url) as response:
                if response.status == 200:
                    content = await response.text()

                    # Google cache includes their styling - extract the original content
                    soup = BeautifulSoup(content, 'html.parser')

                    # Remove Google cache styling
                    for style in soup.select('style'):
                        if 'cache:' in style.get_text():
                            style.decompose()

                    return FetchResult(
                        success=True,
                        content=str(soup),
                        status_code=response.status,
                        url=url,
                        final_url=str(response.url),
                        method="google_cache",
                        metadata={"cache_url": cache_url}
                    )

                return FetchResult(
                    success=False,
                    url=url,
                    error_message="Not found in Google cache",
                    method="google_cache"
                )

        except Exception as e:
            return FetchResult(
                success=False,
                url=url,
                error_message=f"Google cache error: {e}",
                method="google_cache"
            )

    async def _respect_rate_limit(self):
        """Implement rate limiting"""
        if self.rate_limit > 0:
            time_since_last = time.time() - self.last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self.last_request_time = time.time()

    async def batch_fetch(self, urls: List[str], max_concurrent: int = 5) -> List[FetchResult]:
        """Fetch multiple URLs with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url):
            async with semaphore:
                return await self.fetch_with_fallbacks(url)

        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        fetch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                fetch_results.append(FetchResult(
                    success=False,
                    url=urls[i],
                    error_message=str(result),
                    method="error"
                ))
            else:
                fetch_results.append(result)

        return fetch_results