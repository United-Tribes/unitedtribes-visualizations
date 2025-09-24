"""
Prototype Scraper Job with Patti Smith Caching
Modified version of scraper_job.py that uses cached content for rapid prototyping
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import shared components
import sys
sys.path.append(str(Path(__file__).parent.parent / "shared"))
sys.path.append(str(Path(__file__).parent.parent / "articles"))

from models import Source, ScrapedContent, ScrapingBatch
from s3_uploader import S3ContentUploader
from jazz_artist_tracker import JazzArtistTracker
from patti_smith_cache import PattiSmithCache

logger = logging.getLogger(__name__)


class PrototypeScraperJob:
    """
    Prototype scraper job that uses cached Patti Smith content to test the full pipeline
    without relying on potentially broken EnhancedFetcher
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.job_id = f"prototype_job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = datetime.utcnow()
        self.sources_processed = []
        self.total_discovered = 0
        self.total_scraped = 0
        self.total_uploaded = 0
        self.errors = []

        # Initialize components
        self.artist_tracker = JazzArtistTracker()
        self.s3_uploader = S3ContentUploader()
        self.patti_cache = PattiSmithCache()

        # Job configuration
        self.sources = config.get('sources', ['pitchfork'])
        self.max_articles_per_source = config.get('max_articles_per_source', 5)
        self.dry_run = config.get('dry_run', False)
        self.enable_s3_upload = config.get('enable_s3_upload', True)

        logger.info(f"🧪 Initialized prototype job {self.job_id}")
        logger.info(f"📋 Config: sources={self.sources}, max_articles={self.max_articles_per_source}")

    async def run_prototype_harvest(self) -> Dict[str, Any]:
        """
        Run the prototype harvest using cached Patti Smith content
        """
        logger.info("🚀 Starting prototype content harvest with cached data...")

        try:
            # Create comprehensive artist cache
            artist_cache = await self.patti_cache.create_sample_artist_cache("Patti Smith")

            # Process each requested source
            for source_name in self.sources:
                try:
                    logger.info(f"🎯 Processing {source_name} with cached content...")

                    # Get cached content for this source
                    source_content = artist_cache.get(source_name.lower(), [])

                    if not source_content:
                        logger.warning(f"No cached content available for {source_name}")
                        self.errors.append(f"No cached content for {source_name}")
                        continue

                    # Limit to requested number of articles
                    limited_content = source_content[:self.max_articles_per_source]

                    # Track discovery
                    self.total_discovered += len(limited_content)

                    # Update artist tracker
                    # Note: JazzArtistTracker is mainly for final reporting,
                    # so we'll track manually in this prototype

                    # Create content batch
                    batch = ScrapingBatch(
                        source=Source.PITCHFORK,  # Default for prototyping
                        content_items=limited_content,
                        batch_metadata={
                            "processing_method": "cached_prototype",
                            "original_source": source_name,
                            "artist": "Patti Smith",
                            "cache_timestamp": datetime.utcnow().isoformat()
                        }
                    )

                    # Upload to S3 if enabled
                    if self.enable_s3_upload and not self.dry_run:
                        logger.info(f"📤 Uploading {len(limited_content)} cached items to S3...")
                        upload_results = await self.s3_uploader.upload_batch(batch)

                        if upload_results:
                            self.total_uploaded += len(upload_results)
                            logger.info(f"✅ Uploaded {len(upload_results)} items for {source_name}")
                        else:
                            self.errors.append(f"S3 upload failed for {source_name}")
                    else:
                        # Simulate upload for dry run
                        self.total_uploaded += len(limited_content)
                        logger.info(f"🔄 Dry run: Would upload {len(limited_content)} items for {source_name}")

                    self.total_scraped += len(limited_content)
                    self.sources_processed.append(source_name)

                    logger.info(f"✅ Completed {source_name}: {len(limited_content)} articles processed")

                except Exception as e:
                    error_msg = f"Error processing {source_name}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)

            # Generate final report
            return self._generate_report()

        except Exception as e:
            error_msg = f"Prototype harvest failed: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """
        Generate job completion report
        """
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds() / 60

        # Calculate success rate
        success_rate = 0.0
        if self.total_discovered > 0:
            success_rate = self.total_uploaded / self.total_discovered

        report = {
            "job_id": self.job_id,
            "start_time": self.start_time.isoformat(),
            "config": {
                "sources": self.sources,
                "max_articles_per_source": self.max_articles_per_source,
                "dry_run": self.dry_run,
                "enable_s3_upload": self.enable_s3_upload,
                "prototype_mode": True
            },
            "sources_processed": self.sources_processed,
            "total_discovered": self.total_discovered,
            "total_scraped": self.total_scraped,
            "total_uploaded": self.total_uploaded,
            "errors": self.errors,
            "end_time": end_time.isoformat(),
            "duration_minutes": duration,
            "overall_success_rate": success_rate,
            "artist_tracking": {
                "Patti Smith": {
                    "sources_processed": self.sources_processed,
                    "total_articles": self.total_scraped
                }
            }
        }

        # Save report
        self._save_report(report)

        return report

    def _save_report(self, report: Dict[str, Any]):
        """
        Save job report to reports directory
        """
        try:
            reports_dir = Path(__file__).parent / "reports"
            reports_dir.mkdir(exist_ok=True)

            report_file = reports_dir / f"prototype_report_{self.job_id}.json"

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"📊 Report saved: {report_file}")

        except Exception as e:
            logger.error(f"Failed to save report: {e}")


async def main():
    """
    Test the prototype scraper job
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Test configuration
    config = {
        "sources": ["pitchfork", "rolling_stone", "billboard", "npr"],
        "max_articles_per_source": 3,
        "dry_run": False,
        "enable_s3_upload": True
    }

    job = PrototypeScraperJob(config)

    try:
        logger.info("🧪 Running prototype scraper job test...")
        report = await job.run_prototype_harvest()

        print(f"\n🎯 Prototype Job Results:")
        print(f"=========================")
        print(f"Job ID: {report['job_id']}")
        print(f"Sources Processed: {report['sources_processed']}")
        print(f"Discovered: {report['total_discovered']}")
        print(f"Scraped: {report['total_scraped']}")
        print(f"Uploaded: {report['total_uploaded']}")
        print(f"Success Rate: {report['overall_success_rate']:.2%}")
        print(f"Duration: {report['duration_minutes']:.2f} minutes")

        if report['errors']:
            print(f"\nErrors encountered:")
            for error in report['errors']:
                print(f"  - {error}")

        # Show artist tracking results
        artist_summary = report.get('artist_tracking', {})
        if artist_summary:
            print(f"\n📊 Artist Discovery Summary:")
            for artist, data in artist_summary.items():
                print(f"  {artist}: {data}")

    except Exception as e:
        logger.error(f"Prototype job test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())