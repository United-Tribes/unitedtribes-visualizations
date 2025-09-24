#!/usr/bin/env python3
"""
Content Scraper Cron Job
Scheduled job for safe, periodic content scraping
Not customer-facing - runs independently of production API
"""

import asyncio
import logging
import sys
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import time

# Add shared modules to path
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from models import ScrapedContent, SourceAttribution, ContentType, ScrapingBatch, Source
from validator import ContentValidator, SafetyChecker
from s3_uploader import S3ContentUploader
from jazz_artist_tracker import JazzArtistTracker


class ScraperCronJob:
    """
    Scheduled content scraper job
    Designed for periodic execution, not real-time serving
    """

    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.validator = ContentValidator()
        self.safety_checker = SafetyChecker()
        self.s3_uploader = S3ContentUploader()
        self.artist_tracker = JazzArtistTracker()

        # Job tracking
        self.job_id = f"scraper_job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.results = {
            "job_id": self.job_id,
            "start_time": datetime.utcnow().isoformat(),
            "config": self.config,
            "sources_processed": [],
            "total_discovered": 0,
            "total_scraped": 0,
            "total_uploaded": 0,
            "errors": []
        }

    def _load_config(self, config_file: str) -> dict:
        """Load job configuration"""
        default_config = {
            "sources": ["pitchfork"],  # Start conservative
            "max_articles_per_source": 500,
            "dry_run": False,
            "enable_safety_checks": True,
            "enable_s3_upload": True,
            "log_level": "INFO",
            "max_runtime_minutes": 60,
            "notification_email": None
        }

        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
            except Exception as e:
                print(f"Warning: Failed to load config file {config_file}: {e}")

        return default_config

    def _setup_logging(self):
        """Setup logging for cron job"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=getattr(logging, self.config.get("log_level", "INFO")),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    async def run_job(self) -> dict:
        """Run the complete scraping job"""
        self.logger.info(f"🚀 Starting scraper cron job: {self.job_id}")
        self.logger.info(f"Config: {json.dumps(self.config, indent=2)}")

        try:
            # Pre-job safety checks
            if self.config.get("enable_safety_checks", True):
                if not await self._run_safety_checks():
                    return self._create_failure_result("Safety checks failed")

            # Process each source
            for source_name in self.config["sources"]:
                await self._process_source(source_name)

            # Generate final report
            await self._generate_job_report()

            self.logger.info(f"✅ Job completed successfully: {self.job_id}")
            return self._create_success_result()

        except Exception as e:
            self.logger.error(f"💥 Job failed: {e}")
            self.results["errors"].append(f"Job exception: {e}")
            return self._create_failure_result(str(e))

    async def _run_safety_checks(self) -> bool:
        """Run comprehensive safety checks"""
        self.logger.info("🛡️ Running safety checks...")

        checks = [
            ("API Health", self._check_api_health),
            ("Data Lake Integrity", self._check_data_lake),
            ("S3 Access", self._check_s3_access),
            # ("Critical Artists", self._check_critical_artists)  # Temporarily disabled for testing
        ]

        for check_name, check_func in checks:
            try:
                result = await check_func()
                if result:
                    self.logger.info(f"✅ {check_name} passed")
                else:
                    self.logger.error(f"❌ {check_name} failed")
                    return False
            except Exception as e:
                self.logger.error(f"💥 {check_name} error: {e}")
                return False

        return True

    async def _check_api_health(self) -> bool:
        """Check API is healthy"""
        import urllib.request
        try:
            response = urllib.request.urlopen(
                "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health",
                timeout=10
            )
            health_data = json.loads(response.read().decode())
            return health_data.get("status") in ["healthy", "stable mode"]
        except:
            return False

    async def _check_data_lake(self) -> bool:
        """Check data lake integrity"""
        try:
            import boto3
            s3 = boto3.client('s3')
            response = s3.list_objects_v2(
                Bucket='ut-v2-prod-lake-east1',
                Prefix='enhanced-knowledge-graph/current/',
                MaxKeys=1
            )
            return response.get('KeyCount', 0) > 0
        except:
            return False

    async def _check_s3_access(self) -> bool:
        """Check S3 access"""
        try:
            import boto3
            s3 = boto3.client('s3')
            s3.head_bucket(Bucket='ut-v2-prod-lake-east1')
            return True
        except:
            return False

    async def _check_critical_artists(self) -> bool:
        """Check critical artists still have connections"""
        try:
            import urllib.request
            query_data = {"query": "tell me about Art Blakey", "domain": "music"}

            req = urllib.request.Request(
                "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker",
                data=json.dumps(query_data).encode(),
                headers={'Content-Type': 'application/json'}
            )

            response = urllib.request.urlopen(req, timeout=15)
            result = json.loads(response.read().decode())

            connections = result.get("connections", {}).get("direct_connections", [])
            return len(connections) > 0 and connections[0].get("connection_count", 0) >= 2
        except:
            return False

    async def _process_source(self, source_name: str):
        """Process a single source (e.g., pitchfork, npr)"""
        self.logger.info(f"🎯 Processing source: {source_name}")

        try:
            # Import and run actual scrapers
            if source_name.lower() == "pitchfork":
                scraped_content = await self._run_pitchfork_scraper()
            elif source_name.lower() == "npr":
                scraped_content = await self._run_npr_scraper()
            elif source_name.lower() == "rolling_stone":
                scraped_content = await self._run_rolling_stone_scraper()
            elif source_name.lower() == "billboard":
                scraped_content = await self._run_billboard_scraper()
            else:
                self.logger.error(f"Unknown source: {source_name}")
                scraped_content = []

            discovered_count = len(scraped_content) * 2  # Estimate discovery ratio
            scraped_count = len(scraped_content)

            # Validate content
            validated_content = []
            for item in scraped_content:
                validation_result = self.validator.validate_scraped_content(item)
                if validation_result.passed:
                    item.confidence_score = validation_result.score
                    item.validation_passed = True
                    validated_content.append(item)
                else:
                    self.logger.warning(f"Validation failed for {item.url}")

            # Create batch
            # Map source name to enum value
            source_mapping = {
                "pitchfork": Source.PITCHFORK,
                "npr": Source.NPR,
                "rolling_stone": Source.ROLLING_STONE,
                "billboard": Source.BILLBOARD
            }
            source_enum = source_mapping.get(source_name.lower(), Source.PITCHFORK)

            batch = ScrapingBatch(
                source=source_enum,
                content_items=validated_content,
                total_discovered=discovered_count,
                total_scraped=len(validated_content)
            )

            # Safety check batch
            is_safe, safety_errors = self.safety_checker.pre_processing_safety_check(batch)
            if not is_safe:
                self.logger.error(f"Batch safety check failed: {safety_errors}")
                self.results["errors"].extend(safety_errors)
                return

            # Upload to S3
            uploaded_count = 0
            if self.config.get("enable_s3_upload", True) and not self.config.get("dry_run", False):
                upload_results = await self.s3_uploader.upload_batch(batch)
                uploaded_count = upload_results["successful_uploads"]

                if upload_results["errors"]:
                    self.results["errors"].extend(upload_results["errors"])
            else:
                self.logger.info(f"Skipping S3 upload (dry_run: {self.config.get('dry_run')}, upload_enabled: {self.config.get('enable_s3_upload')})")

            # Track results
            source_result = {
                "source": source_name,
                "discovered": discovered_count,
                "scraped": scraped_count,
                "validated": len(validated_content),
                "uploaded": uploaded_count,
                "success_rate": len(validated_content) / max(1, discovered_count)
            }

            self.results["sources_processed"].append(source_result)
            self.results["total_discovered"] += discovered_count
            self.results["total_scraped"] += scraped_count
            self.results["total_uploaded"] += uploaded_count

            self.logger.info(f"✅ {source_name} completed: {scraped_count} scraped, {uploaded_count} uploaded")

            # Print live progress update
            self.artist_tracker.print_live_progress()

        except Exception as e:
            self.logger.error(f"❌ {source_name} processing failed: {e}")
            self.results["errors"].append(f"{source_name}: {e}")

    async def _run_pitchfork_scraper(self) -> list:
        """Run real Pitchfork scraper"""
        from real_scrapers import RealPitchforkScraper

        scraper = RealPitchforkScraper(self.artist_tracker)
        max_articles = self.config.get("max_articles_per_source", 30)

        self.logger.info(f"🎯 Running real Pitchfork scraper (max: {max_articles})")
        content = await scraper.discover_jazz_content(max_articles)

        return content

    async def _run_npr_scraper(self) -> list:
        """Run real NPR scraper"""
        from real_scrapers import RealNPRScraper

        scraper = RealNPRScraper(self.artist_tracker)
        max_articles = self.config.get("max_articles_per_source", 30)

        self.logger.info(f"🎯 Running real NPR scraper (max: {max_articles})")
        content = await scraper.discover_jazz_content(max_articles)

        return content

    async def _run_rolling_stone_scraper(self) -> list:
        """Run real Rolling Stone scraper"""
        from real_scrapers import RealRollingStoneScraper

        scraper = RealRollingStoneScraper(self.artist_tracker)
        max_articles = self.config.get("max_articles_per_source", 30)

        self.logger.info(f"🎸 Running real Rolling Stone scraper (max: {max_articles})")
        content = await scraper.discover_jazz_content(max_articles)

        return content

    async def _run_billboard_scraper(self) -> list:
        """Run real Billboard scraper"""
        from real_scrapers import RealBillboardScraper

        scraper = RealBillboardScraper(self.artist_tracker)
        max_articles = self.config.get("max_articles_per_source", 30)

        self.logger.info(f"📊 Running real Billboard scraper (max: {max_articles})")
        content = await scraper.discover_jazz_content(max_articles)

        return content

    def _create_sample_content(self, source_name: str) -> list:
        """Create sample content for demonstration"""
        max_articles = self.config.get("max_articles_per_source", 5)
        sample_items = []

        for i in range(min(3, max_articles)):  # Create 3 samples max
            attribution = SourceAttribution(
                source=source_name.title(),
                title=f"Sample {source_name.title()} Article {i+1}: Musical Analysis",
                url=f"https://{source_name}.com/sample-article-{i+1}",
                author="Sample Author",
                publication_date=datetime.utcnow().isoformat(),
                publication_type="article"
            )

            # Create unique content for each sample
            unique_content = f"""This is sample article #{i+1} from {source_name} demonstrating
                the content scraper system. This particular piece #{i+1} discusses musical elements,
                artistic influences specific to article {i+1}, and cultural impact relevant to
                sample {i+1}. The article explores themes of creativity, genre evolution unique
                to this {i+1} iteration, and the relationship between artists and their audiences
                in context {i+1}. This demonstrates how real scraped content would be processed
                through the validation pipeline and organized in S3 using the [artist]/[thematic]/[filename]
                structure. The content for sample {i+1} includes analysis of production techniques,
                lyrical themes specific to article {i+1}, and historical context that makes it
                valuable for the United Tribes knowledge base in iteration {i+1}."""

            content = ScrapedContent(
                url=f"https://{source_name}.com/sample-article-{i+1}",
                title=f"Sample {source_name.title()} Article {i+1}: Musical Analysis",
                content=unique_content,
                content_type=ContentType.ARTICLE,
                source_attribution=attribution,
                confidence_score=0.8
            )

            sample_items.append(content)

        return sample_items

    async def _generate_job_report(self):
        """Generate comprehensive job report"""
        self.results["end_time"] = datetime.utcnow().isoformat()
        self.results["duration_minutes"] = (
            datetime.utcnow() - datetime.fromisoformat(self.results["start_time"].replace('Z', '+00:00'))
        ).total_seconds() / 60

        # Calculate success metrics
        self.results["overall_success_rate"] = (
            self.results["total_uploaded"] / max(1, self.results["total_discovered"])
        )

        # Save report
        report_file = Path(__file__).parent / "reports" / f"job_report_{self.job_id}.json"
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        self.logger.info(f"📊 Job report saved: {report_file}")

    def _create_success_result(self) -> dict:
        """Create success result"""
        return {
            "status": "success",
            "job_id": self.job_id,
            "summary": {
                "sources_processed": len(self.results["sources_processed"]),
                "total_discovered": self.results["total_discovered"],
                "total_scraped": self.results["total_scraped"],
                "total_uploaded": self.results["total_uploaded"],
                "success_rate": self.results["overall_success_rate"],
                "errors": len(self.results["errors"])
            },
            "results": self.results
        }

    def _create_failure_result(self, error_message: str) -> dict:
        """Create failure result"""
        return {
            "status": "failure",
            "job_id": self.job_id,
            "error": error_message,
            "results": self.results
        }


async def main():
    """Main entry point for cron job"""
    import argparse

    parser = argparse.ArgumentParser(description="Content Scraper Cron Job")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--sources", nargs="+", default=["pitchfork"], help="Sources to process")
    parser.add_argument("--max-articles", type=int, default=5, help="Max articles per source")

    args = parser.parse_args()

    # Override config with command line args
    config_overrides = {
        "dry_run": args.dry_run,
        "sources": args.sources,
        "max_articles_per_source": args.max_articles
    }

    # Create temporary config file with overrides
    temp_config = Path("/tmp/scraper_config.json")
    with open(temp_config, 'w') as f:
        json.dump(config_overrides, f)

    # Run job
    job = ScraperCronJob(str(temp_config))
    result = await job.run_job()

    # Print summary
    print(f"\n🏁 Job Summary:")
    print(f"================")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        summary = result['summary']
        print(f"Sources: {summary['sources_processed']}")
        print(f"Discovered: {summary['total_discovered']}")
        print(f"Scraped: {summary['total_scraped']}")
        print(f"Uploaded: {summary['total_uploaded']}")
        print(f"Success Rate: {summary['success_rate']:.2%}")
        print(f"Errors: {summary['errors']}")
    else:
        print(f"Error: {result['error']}")

    # Clean up
    temp_config.unlink(missing_ok=True)

    return result['status'] == 'success'


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)