"""
Enhanced Content Extractor with multi-fallback strategies
Combines MissionLocal techniques with sophisticated content parsing
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse
from datetime import datetime
import dateutil.parser

try:
    from .models import ScrapedContent, SourceAttribution, ContentType
except ImportError:
    from models import ScrapedContent, SourceAttribution, ContentType

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from content extraction"""
    success: bool
    content: Optional[ScrapedContent] = None
    confidence: float = 0.0
    method: str = "unknown"
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class EnhancedContentExtractor:
    """
    Multi-strategy content extractor inspired by MissionLocal techniques
    """

    def __init__(self):
        # Content selectors organized by priority and specificity
        self.content_selectors = [
            # High specificity - article content
            'article[role="main"]', 'main article', '[itemprop="articleBody"]',
            '.article-content', '.story-content', '.post-content', '.entry-content',
            '.article-body', '.story-body', '.post-body',

            # Medium specificity - common patterns
            'article', 'main', '.content', '#content',
            '.article', '.story', '.post',

            # Music publication specific
            '.review-content', '.review-body', '.interview-content',
            '.feature-content', '.news-content',

            # Podcast specific
            '.transcript', '.episode-transcript', '.storytext', '.story-text',

            # Generic fallbacks
            '[role="main"]', '.main-content', '#main-content'
        ]

        # Title selectors
        self.title_selectors = [
            'h1[itemprop="headline"]', 'h1.headline', 'h1.title',
            'h1.article-title', 'h1.story-title', 'h1.post-title',
            'h1.entry-title', 'h1.review-title',
            'h1', 'title'
        ]

        # Author selectors
        self.author_selectors = [
            '[itemprop="author"]', '[rel="author"]', '.author-name',
            '.byline', '.byline-author', '.article-author', '.story-author',
            '.post-author', '.entry-author', '.writer', '.by-author'
        ]

        # Date selectors
        self.date_selectors = [
            'time[datetime]', '[itemprop="datePublished"]', '[itemprop="dateCreated"]',
            '.publish-date', '.publication-date', '.article-date', '.story-date',
            '.post-date', '.entry-date', '.date', '.timestamp'
        ]

        # Content type indicators
        self.content_type_patterns = {
            ContentType.REVIEW: ['review', 'album review', 'music review', 'rating'],
            ContentType.INTERVIEW: ['interview', 'q&a', 'talks about', 'conversation with'],
            ContentType.NEWS: ['news', 'breaking', 'announces', 'released'],
            ContentType.PODCAST_TRANSCRIPT: ['transcript', 'fresh air', 'npr']
        }

    def extract_content(self, html: str, url: str, source_name: str) -> ExtractionResult:
        """
        Extract content using multi-fallback strategy
        """
        if not html or len(html) < 100:
            return ExtractionResult(
                success=False,
                errors=["HTML content too short or empty"]
            )

        soup = BeautifulSoup(html, 'html.parser')

        # Try multiple extraction strategies
        strategies = [
            self._extract_structured_data,
            self._extract_semantic_content,
            self._extract_generic_content,
            self._extract_fallback_content
        ]

        best_result = None
        best_confidence = 0.0

        for strategy in strategies:
            try:
                result = strategy(soup, url, source_name)
                if result.success and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence

                # If we get a high-confidence result, use it
                if result.confidence > 0.8:
                    break

            except Exception as e:
                logger.debug(f"Extraction strategy {strategy.__name__} failed: {e}")

        return best_result or ExtractionResult(
            success=False,
            errors=["All extraction strategies failed"]
        )

    def _extract_structured_data(self, soup: BeautifulSoup, url: str, source_name: str) -> ExtractionResult:
        """Extract using structured data (JSON-LD, microdata)"""
        content_data = {}

        # Try JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') in ['Article', 'NewsArticle', 'Review']:
                    content_data.update({
                        'title': data.get('headline', data.get('name')),
                        'content': data.get('articleBody', data.get('text')),
                        'author': self._extract_author_from_json_ld(data.get('author')),
                        'date': data.get('datePublished', data.get('dateCreated'))
                    })
                    break
            except:
                continue

        # Try microdata
        if not content_data.get('title'):
            title_elem = soup.find(attrs={'itemprop': 'headline'})
            if title_elem:
                content_data['title'] = title_elem.get_text(strip=True)

        if not content_data.get('content'):
            content_elem = soup.find(attrs={'itemprop': 'articleBody'})
            if content_elem:
                content_data['content'] = self._clean_content_text(content_elem)

        # Validate extraction
        if content_data.get('title') and content_data.get('content'):
            content = self._build_scraped_content(content_data, url, source_name)
            return ExtractionResult(
                success=True,
                content=content,
                confidence=0.9,
                method="structured_data"
            )

        return ExtractionResult(success=False, method="structured_data")

    def _extract_semantic_content(self, soup: BeautifulSoup, url: str, source_name: str) -> ExtractionResult:
        """Extract using semantic HTML elements"""
        content_data = {}

        # Extract title
        content_data['title'] = self._extract_by_selectors(soup, self.title_selectors)

        # Extract content
        content_data['content'] = self._extract_by_selectors(soup, self.content_selectors, extract_text=True)

        # Extract metadata
        content_data['author'] = self._extract_by_selectors(soup, self.author_selectors)
        content_data['date'] = self._extract_date(soup)

        # Validate
        if content_data.get('title') and content_data.get('content') and len(content_data['content']) > 200:
            content = self._build_scraped_content(content_data, url, source_name)
            return ExtractionResult(
                success=True,
                content=content,
                confidence=0.8,
                method="semantic"
            )

        return ExtractionResult(success=False, method="semantic")

    def _extract_generic_content(self, soup: BeautifulSoup, url: str, source_name: str) -> ExtractionResult:
        """Generic extraction using common patterns"""
        content_data = {}

        # Title - try h1 tags
        h1_tags = soup.find_all('h1')
        if h1_tags:
            content_data['title'] = h1_tags[0].get_text(strip=True)

        # Content - try article-like containers
        article_content = None
        for selector in ['article', 'main', '.content', '#content']:
            elements = soup.select(selector)
            for elem in elements:
                text = self._clean_content_text(elem)
                if len(text) > 500:  # Substantial content
                    article_content = text
                    break
            if article_content:
                break

        content_data['content'] = article_content

        # Validate
        if content_data.get('title') and content_data.get('content'):
            content = self._build_scraped_content(content_data, url, source_name)
            return ExtractionResult(
                success=True,
                content=content,
                confidence=0.6,
                method="generic"
            )

        return ExtractionResult(success=False, method="generic")

    def _extract_fallback_content(self, soup: BeautifulSoup, url: str, source_name: str) -> ExtractionResult:
        """Last resort - extract any substantial text"""
        # Remove navigation, ads, etc.
        for unwanted in soup.select('nav, footer, aside, .ad, .advertisement, .sidebar'):
            unwanted.decompose()

        # Get page title
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else urlparse(url).path

        # Get body text
        body = soup.find('body')
        if body:
            body_text = self._clean_content_text(body)
            if len(body_text) > 300:
                content_data = {
                    'title': title_text,
                    'content': body_text
                }

                content = self._build_scraped_content(content_data, url, source_name)
                return ExtractionResult(
                    success=True,
                    content=content,
                    confidence=0.3,
                    method="fallback"
                )

        return ExtractionResult(success=False, method="fallback")

    def _extract_by_selectors(self, soup: BeautifulSoup, selectors: List[str], extract_text: bool = False) -> Optional[str]:
        """Extract content using CSS selectors"""
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                if extract_text:
                    text = self._clean_content_text(elem)
                    if len(text) > 50:  # Minimum content length
                        return text
                else:
                    text = elem.get_text(strip=True)
                    if text:
                        return text
        return None

    def _clean_content_text(self, element) -> str:
        """Clean and normalize text content"""
        if not element:
            return ""

        # Remove unwanted elements
        for unwanted in element.select('script, style, nav, footer, aside, .ad, .advertisement, .social-share'):
            unwanted.decompose()

        # Get text with preserved spacing
        text = element.get_text(separator=' ', strip=True)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return text.strip()

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date"""
        for selector in self.date_selectors:
            elements = soup.select(selector)
            for elem in elements:
                # Try datetime attribute first
                date_str = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                if date_str:
                    try:
                        # Parse and normalize date
                        parsed_date = dateutil.parser.parse(date_str)
                        return parsed_date.isoformat()
                    except:
                        continue
        return None

    def _extract_author_from_json_ld(self, author_data) -> Optional[str]:
        """Extract author from JSON-LD data"""
        if isinstance(author_data, dict):
            return author_data.get('name')
        elif isinstance(author_data, list) and author_data:
            first_author = author_data[0]
            if isinstance(first_author, dict):
                return first_author.get('name')
        elif isinstance(author_data, str):
            return author_data
        return None

    def _detect_content_type(self, title: str, content: str, url: str) -> ContentType:
        """Detect content type based on title, content, and URL"""
        title_lower = title.lower() if title else ""
        content_lower = content.lower() if content else ""
        url_lower = url.lower()

        # Check patterns
        for content_type, patterns in self.content_type_patterns.items():
            for pattern in patterns:
                if pattern in title_lower or pattern in url_lower or pattern in content_lower[:500]:
                    return content_type

        # Default to article
        return ContentType.ARTICLE

    def _build_scraped_content(self, content_data: Dict[str, Any], url: str, source_name: str) -> ScrapedContent:
        """Build ScrapedContent object from extracted data"""
        title = content_data.get('title', '')
        content_text = content_data.get('content', '')

        # Create source attribution
        source_attribution = SourceAttribution(
            source=source_name,
            title=title,
            url=url,
            author=content_data.get('author'),
            publication_date=content_data.get('date'),
            publication_type="article",  # Will be refined by content type detection
            content_type=None  # Will be set below
        )

        # Detect content type
        content_type = self._detect_content_type(title, content_text, url)
        source_attribution.content_type = content_type.value

        # Adjust publication type based on content type
        if content_type == ContentType.PODCAST_TRANSCRIPT:
            source_attribution.publication_type = "podcast"

        return ScrapedContent(
            url=url,
            title=title,
            content=content_text,
            content_type=content_type,
            source_attribution=source_attribution,
            confidence_score=0.8,  # Will be adjusted by calling code
            validation_passed=len(content_text) > 200 and len(title) > 5
        )