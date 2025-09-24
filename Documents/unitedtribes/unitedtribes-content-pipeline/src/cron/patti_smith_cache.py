"""
Patti Smith Data Caching for Prototyping
Uses existing S3 content to simulate real scraper results without relying on EnhancedFetcher
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Import shared components
import sys
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from models import ScrapedContent, SourceAttribution, ContentType

logger = logging.getLogger(__name__)


class PattiSmithCache:
    """
    Cache manager for Patti Smith content to enable prototyping without EnhancedFetcher
    """

    def __init__(self):
        self.s3_bucket = "ut-v2-prod-lake-east1"
        self.cached_content = {}

        # Known Patti Smith content in S3
        self.patti_smith_s3_keys = [
            "video_analysis/dua_lipa/video_dua_lipa_in_conversation_with_patti_smith_author_o.json",
            "video_analysis/how_patti_smith/video_how_patti_smith_saved_rock_n_roll.json",
            "video_analysis/just_kids_by/video_just_kids_by_patti_smith_changed_my_life.json",
            "video_analysis/lessons_from_rick/video_lessons_from_rick_rubin_and_patti_smith_from_apath.json",
            "video_analysis/lou_reed/video_lou_reed_patti_smith_on_lou_reed_and_rock_and_roll_american.json"
        ]

    async def load_patti_smith_content(self) -> List[ScrapedContent]:
        """
        Load existing Patti Smith content from S3 and convert to ScrapedContent format
        """
        logger.info("🎸 Loading cached Patti Smith content for prototyping...")

        scraped_items = []

        for s3_key in self.patti_smith_s3_keys:
            try:
                # Download content from S3
                import boto3
                s3_client = boto3.client('s3')

                logger.info(f"📥 Loading {s3_key}")
                response = s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
                content_data = json.loads(response['Body'].read().decode('utf-8'))

                # Convert to ScrapedContent format
                scraped_item = self._convert_video_analysis_to_scraped_content(content_data, s3_key)
                if scraped_item:
                    scraped_items.append(scraped_item)
                    logger.info(f"✅ Converted {scraped_item.title[:60]}...")

            except Exception as e:
                logger.error(f"Failed to load {s3_key}: {e}")

        logger.info(f"🎯 Loaded {len(scraped_items)} Patti Smith content items for prototyping")
        return scraped_items

    def _convert_video_analysis_to_scraped_content(self, content_data: Dict[str, Any], s3_key: str) -> Optional[ScrapedContent]:
        """
        Convert video analysis JSON to ScrapedContent format for consistency with scrapers
        """
        try:
            source_info = content_data.get('source_info', {})
            title = source_info.get('title', 'Unknown Title')

            # Extract main content from temporal segments
            segments = content_data.get('temporal_segments', [])
            content_text = ""

            # Skip metadata segments and extract actual content
            for segment in segments:
                segment_content = segment.get('content', '')
                timestamp = segment.get('timestamp', '')

                # Skip metadata segments
                if any(skip in segment_content.lower() for skip in [
                    'transcript for:', 'channel:', 'video id:', 'type:', 'whisper model:', 'extracted:'
                ]):
                    continue

                # Skip separator lines
                if '====' in segment_content:
                    continue

                # Add substantial content
                if len(segment_content.strip()) > 10:
                    content_text += f"[{timestamp}] {segment_content}\n"

            # Create source attribution
            attribution = SourceAttribution(
                source="Video Analysis Cache",
                title=title,
                url=f"s3://{self.s3_bucket}/{s3_key}",
                author=source_info.get('channel', 'Unknown'),
                publication_date=source_info.get('extraction_date', datetime.utcnow().isoformat()),
                publication_type="video_documentary"
            )

            # Determine content type
            content_type = ContentType.ARTICLE  # Default for video content
            if 'interview' in title.lower() or 'conversation' in title.lower():
                content_type = ContentType.INTERVIEW

            # Create ScrapedContent object
            scraped_content = ScrapedContent(
                url=f"s3://{self.s3_bucket}/{s3_key}",
                title=title,
                content=content_text,
                content_type=content_type,
                source_attribution=attribution,
                confidence_score=0.9  # High confidence for existing curated content
            )

            # Set S3 key for organization
            scraped_content.s3_key = f"patti_smith/cached_video/{Path(s3_key).stem}.json"

            return scraped_content

        except Exception as e:
            logger.error(f"Error converting video analysis to ScrapedContent: {e}")
            return None

    async def simulate_source_scraping(self, source_name: str, max_articles: int = 5) -> List[ScrapedContent]:
        """
        Simulate scraping by returning cached Patti Smith content tagged with the source
        """
        logger.info(f"🎭 Simulating {source_name} scraping with cached Patti Smith content...")

        # Load all cached content
        all_content = await self.load_patti_smith_content()

        # Modify source attribution to simulate different sources
        simulated_content = []

        for i, content in enumerate(all_content[:max_articles]):
            # Create a copy with modified source attribution
            simulated_item = ScrapedContent(
                url=f"https://simulated-{source_name.lower()}.com/patti-smith-article-{i+1}",
                title=f"[{source_name} Simulation] {content.title}",
                content=content.content,
                content_type=content.content_type,
                source_attribution=SourceAttribution(
                    source=source_name,
                    title=f"[{source_name} Simulation] {content.title}",
                    url=f"https://simulated-{source_name.lower()}.com/patti-smith-article-{i+1}",
                    author=f"{source_name} Simulation",
                    publication_date=datetime.utcnow().isoformat(),
                    publication_type="simulated_article"
                ),
                confidence_score=0.8  # Slightly lower for simulation
            )

            # Set appropriate S3 key
            simulated_item.s3_key = f"patti_smith/{source_name.lower()}_simulation/simulated_article_{i+1}.json"

            simulated_content.append(simulated_item)

        logger.info(f"🎯 Generated {len(simulated_content)} simulated {source_name} articles")
        return simulated_content

    async def create_sample_artist_cache(self, artist_name: str = "Patti Smith") -> Dict[str, List[ScrapedContent]]:
        """
        Create a comprehensive cache for one artist across all sources for prototyping
        """
        logger.info(f"🎨 Creating comprehensive cache for {artist_name}...")

        artist_cache = {}
        sources = ["Pitchfork", "Rolling Stone", "Billboard", "NPR"]

        for source in sources:
            source_content = await self.simulate_source_scraping(source, max_articles=3)
            artist_cache[source.lower()] = source_content

        total_articles = sum(len(content) for content in artist_cache.values())
        logger.info(f"✅ Created cache with {total_articles} articles across {len(sources)} sources")

        return artist_cache


async def main():
    """
    Test the Patti Smith caching system
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    cache = PattiSmithCache()

    try:
        # Test loading direct content
        logger.info("Testing direct content loading...")
        direct_content = await cache.load_patti_smith_content()
        print(f"\n📊 Direct Content Results:")
        print(f"==============================")
        print(f"Loaded: {len(direct_content)} articles")

        if direct_content:
            sample = direct_content[0]
            print(f"Sample Title: {sample.title[:80]}...")
            print(f"Content Length: {len(sample.content)} characters")
            print(f"S3 Key: {sample.s3_key}")
            print(f"Source: {sample.source_attribution.source}")

        # Test simulation for all sources
        logger.info("\nTesting source simulation...")
        artist_cache = await cache.create_sample_artist_cache()

        print(f"\n🎭 Simulation Results:")
        print(f"======================")
        for source, content_list in artist_cache.items():
            print(f"{source.title()}: {len(content_list)} articles")
            if content_list:
                print(f"  Sample: {content_list[0].title[:60]}...")

    except Exception as e:
        logger.error(f"Cache test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())