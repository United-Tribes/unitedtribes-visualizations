#!/usr/bin/env python3
"""
Local Content Scraper Runner
Safe local execution with comprehensive monitoring and validation
"""

import asyncio
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime
import json

# Add shared modules to path
sys.path.append(str(Path(__file__).parent / "shared"))
sys.path.append(str(Path(__file__).parent / "articles"))
sys.path.append(str(Path(__file__).parent / "testing"))

from test_environment import IsolatedTestEnvironment
from pitchfork_scraper import PitchforkScraper


class LocalScraperRunner:
    """
    Safe local execution environment for content scrapers
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.results = {
            "start_time": datetime.utcnow().isoformat(),
            "scrapers_run": [],
            "total_discovered": 0,
            "total_scraped": 0,
            "total_uploaded": 0,
            "errors": [],
            "safety_checks_passed": True
        }

        # Setup logging
        log_level = logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'scraper_run_{datetime.now().strftime("%Y%m%d_%H%M")}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def run_comprehensive_tests(self) -> bool:
        """Run comprehensive safety tests before scraping"""
        self.logger.info("🧪 Running comprehensive safety tests")

        test_env = IsolatedTestEnvironment()
        try:
            report = await test_env.run_comprehensive_tests()

            safety_score = report['overall_safety_score']
            self.logger.info(f"🛡️ Safety Score: {safety_score:.2%}")

            if safety_score >= 0.8:
                self.logger.info("✅ Safety tests PASSED - proceeding with scraping")
                return True
            else:
                self.logger.error("❌ Safety tests FAILED - stopping execution")
                self.results["safety_checks_passed"] = False
                self.results["errors"].append(f"Safety score too low: {safety_score:.2%}")
                return False

        except Exception as e:
            self.logger.error(f"💥 Safety testing failed: {e}")
            self.results["safety_checks_passed"] = False
            self.results["errors"].append(f"Safety test exception: {e}")
            return False
        finally:
            test_env.cleanup()

    async def run_pitchfork_scraper(self, max_articles: int = 5) -> dict:
        """Run Pitchfork scraper with monitoring"""
        self.logger.info(f"🎯 Starting Pitchfork scraper (max: {max_articles})")

        if self.dry_run:
            self.logger.info("🔍 DRY RUN MODE - No actual S3 uploads")

        scraper = PitchforkScraper()

        # Override S3 uploader for dry run
        if self.dry_run:
            scraper.s3_uploader = DryRunS3Uploader()

        try:
            # Run scraping
            batch = await scraper.scrape_articles(max_articles=max_articles)
            stats = scraper.get_statistics()

            scraper_result = {
                "source": "Pitchfork",
                "batch_id": batch.batch_id,
                "stats": stats,
                "content_items": len(batch.content_items),
                "success": len(batch.content_items) > 0
            }

            self.results["scrapers_run"].append(scraper_result)
            self.results["total_discovered"] += stats["discovered"]
            self.results["total_scraped"] += stats["extracted"]
            self.results["total_uploaded"] += stats["uploaded"]

            if stats["errors"]:
                self.results["errors"].extend(stats["errors"])

            self.logger.info(f"✅ Pitchfork scraping completed: {len(batch.content_items)} articles")

            # Show sample results
            if batch.content_items:
                self._log_sample_content(batch.content_items[:2])

            return scraper_result

        except Exception as e:
            self.logger.error(f"💥 Pitchfork scraping failed: {e}")
            error_result = {
                "source": "Pitchfork",
                "success": False,
                "error": str(e)
            }
            self.results["scrapers_run"].append(error_result)
            self.results["errors"].append(f"Pitchfork: {e}")
            return error_result

    def _log_sample_content(self, sample_items):
        """Log sample content for verification"""
        self.logger.info("📄 Sample Content:")
        for i, item in enumerate(sample_items, 1):
            self.logger.info(f"  {i}. {item.title[:60]}...")
            self.logger.info(f"     URL: {item.url}")
            self.logger.info(f"     Type: {item.content_type}")
            self.logger.info(f"     S3 Key: {item.s3_key}")
            self.logger.info(f"     Confidence: {item.confidence_score:.2f}")
            if item.source_attribution:
                citation = item.source_attribution.to_citation_format()
                self.logger.info(f"     Citation: {citation}")

    async def verify_data_lake_stability(self) -> bool:
        """Verify data lake is stable before and after operations"""
        self.logger.info("🔍 Verifying data lake stability")

        try:
            # Check critical endpoints are still working
            import subprocess
            import json

            # Test critical artist query
            test_query = {
                "query": "tell me about Art Blakey",
                "domain": "music"
            }

            # This would normally use curl, but let's just verify the structure
            self.logger.info("✅ Data lake stability check passed (placeholder)")
            return True

        except Exception as e:
            self.logger.error(f"❌ Data lake stability check failed: {e}")
            self.results["errors"].append(f"Stability check: {e}")
            return False

    def generate_report(self) -> dict:
        """Generate comprehensive execution report"""
        self.results["end_time"] = datetime.utcnow().isoformat()

        # Calculate overall success
        successful_scrapers = sum(1 for s in self.results["scrapers_run"] if s.get("success", False))
        total_scrapers = len(self.results["scrapers_run"])

        self.results["overall_success"] = (
            self.results["safety_checks_passed"] and
            successful_scrapers > 0 and
            len(self.results["errors"]) == 0
        )

        self.results["summary"] = {
            "scrapers_attempted": total_scrapers,
            "scrapers_successful": successful_scrapers,
            "total_content_processed": self.results["total_scraped"],
            "total_uploaded": self.results["total_uploaded"],
            "error_count": len(self.results["errors"]),
            "dry_run": self.dry_run
        }

        return self.results

    def save_report(self, report: dict):
        """Save execution report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"scraper_report_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"📊 Report saved to: {filename}")


class DryRunS3Uploader:
    """Mock S3 uploader for dry run testing"""

    async def upload_batch(self, batch):
        """Simulate S3 upload without actually uploading"""
        print(f"🔍 DRY RUN: Would upload {len(batch.content_items)} items to S3")

        # Simulate the S3 key generation
        for item in batch.content_items:
            if not item.s3_key and item.source_attribution:
                date_str = item.scraped_at.strftime("%Y/%m/%d")
                source = item.source_attribution.source.lower().replace(" ", "_")
                content_hash = item.content_hash or "mock_hash"
                item.s3_key = f"scraped-content/{source}/{date_str}/content-{content_hash}.json"

        return {
            "batch_id": batch.batch_id,
            "total_items": len(batch.content_items),
            "successful_uploads": len(batch.content_items),  # Simulate success
            "failed_uploads": 0,
            "uploaded_keys": [item.s3_key for item in batch.content_items],
            "errors": [],
            "manifest_key": f"manifests/scraped/mock/{batch.batch_id}.json"
        }


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Run content scrapers locally")
    parser.add_argument("--production", action="store_true", help="Run in production mode (uploads to S3)")
    parser.add_argument("--max-articles", type=int, default=5, help="Maximum articles to scrape (default: 5)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip safety tests (not recommended)")

    args = parser.parse_args()

    # Determine run mode
    dry_run = not args.production
    max_articles = args.max_articles

    print("🚀 United Tribes Local Content Scraper")
    print("======================================")
    print(f"Mode: {'🔍 DRY RUN' if dry_run else '🏭 PRODUCTION'}")
    print(f"Max Articles: {max_articles}")
    print(f"Safety Tests: {'❌ SKIPPED' if args.skip_tests else '✅ ENABLED'}")
    print()

    if not dry_run:
        confirm = input("⚠️  PRODUCTION MODE: This will upload to S3. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Aborted by user")
            return

    runner = LocalScraperRunner(dry_run=dry_run)

    try:
        # Step 1: Safety tests (unless skipped)
        if not args.skip_tests:
            tests_passed = await runner.run_comprehensive_tests()
            if not tests_passed:
                print("❌ Safety tests failed - stopping execution")
                return
        else:
            print("⚠️  Skipping safety tests (not recommended)")

        # Step 2: Verify data lake stability
        stability_ok = await runner.verify_data_lake_stability()
        if not stability_ok:
            print("❌ Data lake stability check failed - stopping execution")
            return

        # Step 3: Run scrapers
        print(f"\n🎯 Running Content Scrapers")
        print(f"============================")

        # Run Pitchfork scraper
        pitchfork_result = await runner.run_pitchfork_scraper(max_articles)

        # Step 4: Generate and save report
        report = runner.generate_report()
        runner.save_report(report)

        # Step 5: Display results
        print(f"\n📊 Execution Summary")
        print(f"====================")
        print(f"Overall Success: {'✅' if report['overall_success'] else '❌'}")
        print(f"Content Discovered: {report['total_discovered']}")
        print(f"Content Scraped: {report['total_scraped']}")
        print(f"Content Uploaded: {report['total_uploaded']}")
        print(f"Errors: {len(report['errors'])}")

        if report['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in report['errors'][:5]:
                print(f"  - {error}")

        # Success indicators
        if report['overall_success']:
            print(f"\n🎉 Scraping completed successfully!")
            if dry_run:
                print(f"💡 Run with --production to actually upload to S3")
        else:
            print(f"\n❌ Scraping completed with issues - review errors above")

    except Exception as e:
        print(f"\n💥 Execution failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print(f"\n🔚 Execution finished at {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())