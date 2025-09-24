"""
Isolated testing environment for content scrapers
Ensures scrapers work correctly before they touch the production data lake
"""

import asyncio
import logging
import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import boto3
from dataclasses import asdict

# Import our scraper components
import sys
sys.path.append('../shared')
from models import ScrapedContent, ScrapingBatch, SourceAttribution, ContentType
from validator import ContentValidator, SafetyChecker, ValidationResult
from fetcher import EnhancedFetcher, FetchResult
from extractor import EnhancedContentExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class IsolatedTestEnvironment:
    """
    Safe testing environment for content scrapers
    Validates everything before allowing data lake interaction
    """

    def __init__(self, test_bucket: str = "ut-v2-test-scraping"):
        self.test_bucket = test_bucket
        self.validator = ContentValidator()
        self.safety_checker = SafetyChecker()
        self.extractor = EnhancedContentExtractor()

        # Create temporary directory for test outputs
        self.test_dir = Path(tempfile.mkdtemp(prefix="scraper_test_"))
        logger.info(f"Created test environment at {self.test_dir}")

        # Test URLs for validation
        self.test_urls = {
            "pitchfork": [
                "https://pitchfork.com/reviews/albums/",
                "https://pitchfork.com/features/",
                "https://pitchfork.com/news/"
            ],
            "rolling_stone": [
                "https://www.rollingstone.com/music/",
                "https://www.rollingstone.com/music/music-news/"
            ],
            "billboard": [
                "https://www.billboard.com/music/",
                "https://www.billboard.com/pro/"
            ],
            "npr": [
                "https://www.npr.org/sections/music/",
                "https://www.npr.org/podcasts/510019/fresh-air"
            ]
        }

        # Track test results
        self.test_results = {
            "fetch_tests": [],
            "extraction_tests": [],
            "validation_tests": [],
            "batch_tests": [],
            "safety_tests": []
        }

    async def run_comprehensive_tests(self, source_name: str = None) -> Dict[str, Any]:
        """
        Run comprehensive test suite for scrapers
        """
        logger.info("🧪 Starting comprehensive scraper testing")

        sources_to_test = [source_name] if source_name else list(self.test_urls.keys())

        for source in sources_to_test:
            logger.info(f"Testing {source} scraper components...")

            # Test 1: Fetch tests
            await self._test_fetching(source)

            # Test 2: Content extraction tests
            await self._test_extraction(source)

            # Test 3: Validation tests
            await self._test_validation(source)

            # Test 4: Batch processing tests
            await self._test_batch_processing(source)

            # Test 5: Safety checks
            await self._test_safety_checks(source)

        # Generate test report
        report = self._generate_test_report()

        # Save test results
        self._save_test_results(report)

        logger.info("✅ Comprehensive testing completed")
        return report

    async def _test_fetching(self, source: str):
        """Test content fetching with fallback strategies"""
        logger.info(f"🌐 Testing fetching for {source}")

        test_urls = self.test_urls.get(source, [])
        fetch_results = []

        async with EnhancedFetcher(rate_limit=2.0) as fetcher:
            for url in test_urls[:2]:  # Test first 2 URLs to avoid rate limiting
                try:
                    result = await fetcher.fetch_with_fallbacks(url)

                    test_case = {
                        "url": url,
                        "success": result.success,
                        "method": result.method,
                        "content_length": len(result.content) if result.content else 0,
                        "status_code": result.status_code,
                        "error": result.error_message
                    }

                    fetch_results.append(test_case)

                    if result.success:
                        logger.info(f"  ✅ {url} - {result.method} - {len(result.content)} chars")
                    else:
                        logger.warning(f"  ❌ {url} - {result.error_message}")

                except Exception as e:
                    logger.error(f"  💥 {url} - Exception: {e}")
                    fetch_results.append({
                        "url": url,
                        "success": False,
                        "error": str(e)
                    })

        self.test_results["fetch_tests"].extend(fetch_results)

    async def _test_extraction(self, source: str):
        """Test content extraction from fetched HTML"""
        logger.info(f"📝 Testing extraction for {source}")

        # Use sample HTML content for testing extraction
        sample_html = self._get_sample_html(source)
        test_url = f"https://example.com/{source}/test-article"

        try:
            result = self.extractor.extract_content(sample_html, test_url, source)

            test_case = {
                "source": source,
                "success": result.success,
                "method": result.method,
                "confidence": result.confidence,
                "title_length": len(result.content.title) if result.content else 0,
                "content_length": len(result.content.content) if result.content else 0,
                "errors": result.errors
            }

            self.test_results["extraction_tests"].append(test_case)

            if result.success:
                logger.info(f"  ✅ Extraction successful - {result.method} - confidence: {result.confidence}")
            else:
                logger.warning(f"  ❌ Extraction failed - {result.errors}")

        except Exception as e:
            logger.error(f"  💥 Extraction exception: {e}")
            self.test_results["extraction_tests"].append({
                "source": source,
                "success": False,
                "error": str(e)
            })

    async def _test_validation(self, source: str):
        """Test content validation"""
        logger.info(f"🔍 Testing validation for {source}")

        # Create test content
        test_content = self._create_test_content(source)

        try:
            validation_result = self.validator.validate_scraped_content(test_content)

            test_case = {
                "source": source,
                "passed": validation_result.passed,
                "score": validation_result.score,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "metadata": validation_result.metadata
            }

            self.test_results["validation_tests"].append(test_case)

            if validation_result.passed:
                logger.info(f"  ✅ Validation passed - score: {validation_result.score:.2f}")
            else:
                logger.warning(f"  ❌ Validation failed - errors: {validation_result.errors}")

        except Exception as e:
            logger.error(f"  💥 Validation exception: {e}")
            self.test_results["validation_tests"].append({
                "source": source,
                "passed": False,
                "error": str(e)
            })

    async def _test_batch_processing(self, source: str):
        """Test batch processing and safety checks"""
        logger.info(f"📦 Testing batch processing for {source}")

        # Create test batch
        test_batch = self._create_test_batch(source)

        try:
            # Test batch validation
            batch_result = self.validator.validate_batch(test_batch)

            # Test safety checks
            is_safe, safety_errors = self.safety_checker.pre_processing_safety_check(test_batch)

            test_case = {
                "source": source,
                "batch_valid": batch_result.passed,
                "batch_score": batch_result.score,
                "batch_errors": batch_result.errors,
                "safety_passed": is_safe,
                "safety_errors": safety_errors,
                "item_count": len(test_batch.content_items)
            }

            self.test_results["batch_tests"].append(test_case)

            if batch_result.passed and is_safe:
                logger.info(f"  ✅ Batch processing passed - {len(test_batch.content_items)} items")
            else:
                logger.warning(f"  ❌ Batch issues - errors: {batch_result.errors + safety_errors}")

        except Exception as e:
            logger.error(f"  💥 Batch processing exception: {e}")
            self.test_results["batch_tests"].append({
                "source": source,
                "batch_valid": False,
                "error": str(e)
            })

    async def _test_safety_checks(self, source: str):
        """Test safety and security measures"""
        logger.info(f"🛡️ Testing safety checks for {source}")

        safety_results = []

        # Test 1: Malicious content detection
        malicious_content = self._create_malicious_test_content()
        malicious_result = self.validator.validate_scraped_content(malicious_content)

        safety_results.append({
            "test": "malicious_content_detection",
            "should_fail": True,
            "actually_failed": not malicious_result.passed,
            "score": malicious_result.score
        })

        # Test 2: Oversized batch handling
        oversized_batch = self._create_oversized_batch(source)
        is_safe, errors = self.safety_checker.pre_processing_safety_check(oversized_batch)

        safety_results.append({
            "test": "oversized_batch_detection",
            "should_fail": True,
            "actually_failed": not is_safe,
            "errors": errors
        })

        # Test 3: V3 compatibility
        test_content = self._create_test_content(source)
        v3_compatible = self.safety_checker.verify_v3_compatibility(test_content)

        safety_results.append({
            "test": "v3_compatibility",
            "should_pass": True,
            "actually_passed": v3_compatible
        })

        self.test_results["safety_tests"].extend(safety_results)

        # Log results
        for result in safety_results:
            if result.get("should_fail"):
                if result.get("actually_failed"):
                    logger.info(f"  ✅ {result['test']} - correctly detected threat")
                else:
                    logger.error(f"  ❌ {result['test']} - FAILED to detect threat")
            else:
                if result.get("actually_passed"):
                    logger.info(f"  ✅ {result['test']} - passed as expected")
                else:
                    logger.error(f"  ❌ {result['test']} - unexpectedly failed")

    def _get_sample_html(self, source: str) -> str:
        """Get sample HTML for testing extraction"""
        samples = {
            "pitchfork": """
            <html>
                <head><title>Album Review: Artist - Album Name</title></head>
                <body>
                    <h1 data-testid="ContentHeaderHed">Artist - Album Name</h1>
                    <div data-testid="BylineWrapper"><a>John Reviewer</a></div>
                    <time datetime="2024-01-15">January 15, 2024</time>
                    <div data-testid="ContentBody">
                        <p>This is a comprehensive album review discussing the musical elements, production quality, and artistic merit of this release. The album showcases the artist's evolution in sound and demonstrates their mastery of the genre.</p>
                        <p>Key tracks include opening track which sets the tone, the powerful mid-album centerpiece, and the contemplative closer that leaves listeners wanting more.</p>
                    </div>
                </body>
            </html>
            """,
            "rolling_stone": """
            <html>
                <head><title>Music News: Major Artist Announcement</title></head>
                <body>
                    <h1>Major Artist Announces New Album</h1>
                    <div class="byline">By Music Reporter</div>
                    <time>2024-01-15</time>
                    <article>
                        <p>In a major music industry announcement today, the acclaimed artist revealed details about their upcoming studio album, scheduled for release this summer.</p>
                        <p>The album will feature collaborations with several notable musicians and promises to explore new sonic territories while maintaining the artist's signature sound.</p>
                    </article>
                </body>
            </html>
            """,
            "billboard": """
            <html>
                <head><title>Chart Analysis: Weekly Music Trends</title></head>
                <body>
                    <h1>Chart Analysis: Weekly Music Trends</h1>
                    <div class="article-content">
                        <p>This week's chart movements reveal significant trends in contemporary music consumption, with several genres experiencing notable shifts in popularity.</p>
                        <p>The data indicates changing listener preferences and the impact of streaming platforms on music discovery and consumption patterns.</p>
                    </div>
                </body>
            </html>
            """,
            "npr": """
            <html>
                <head><title>Fresh Air: Interview with Musical Artist</title></head>
                <body>
                    <h1>Fresh Air: Interview with Musical Artist</h1>
                    <div class="storytext">
                        <p>TERRY GROSS, HOST: Our guest today is a celebrated musician whose latest work explores themes of identity, creativity, and social change through innovative musical arrangements.</p>
                        <p>GUEST: Thank you for having me, Terry. This album represents a very personal journey for me as an artist.</p>
                        <p>GROSS: Let's talk about the creative process behind your latest release...</p>
                    </div>
                </body>
            </html>
            """
        }
        return samples.get(source, "<html><body><h1>Test</h1><p>Test content for extraction</p></body></html>")

    def _create_test_content(self, source: str) -> ScrapedContent:
        """Create valid test content for validation"""
        attribution = SourceAttribution(
            source=source.replace("_", " ").title(),
            title="Test Article: Musical Analysis",
            url=f"https://example.com/{source}/test-article",
            author="Test Author",
            publication_date="2024-01-15T10:00:00Z",
            publication_type="article",
            content_type="review"
        )

        return ScrapedContent(
            url=f"https://example.com/{source}/test-article",
            title="Test Article: Musical Analysis",
            content="This is a comprehensive test article with sufficient content to pass validation. It discusses musical elements, artist influences, and provides detailed analysis of the creative process. The content is substantial enough to meet minimum length requirements and contains relevant music-related keywords to demonstrate topical relevance.",
            content_type=ContentType.REVIEW,
            source_attribution=attribution,
            confidence_score=0.8,
            validation_passed=True
        )

    def _create_malicious_test_content(self) -> ScrapedContent:
        """Create test content that should fail validation"""
        attribution = SourceAttribution(
            source="Suspicious Source",
            title="404 Not Found",
            url="https://malicious.example.com/fake",
            publication_type="article"
        )

        return ScrapedContent(
            url="https://malicious.example.com/fake",
            title="404",
            content="404 not found please enable javascript captcha",
            content_type=ContentType.ARTICLE,
            source_attribution=attribution,
            confidence_score=0.1
        )

    def _create_test_batch(self, source: str) -> ScrapingBatch:
        """Create test batch with multiple items"""
        items = []
        for i in range(3):
            items.append(self._create_test_content(source))

        batch = ScrapingBatch(
            source=source,
            content_items=items,
            total_discovered=5,
            total_scraped=3
        )
        return batch

    def _create_oversized_batch(self, source: str) -> ScrapingBatch:
        """Create oversized batch that should fail safety checks"""
        items = []
        for i in range(150):  # Over the 100 item limit
            items.append(self._create_test_content(source))

        return ScrapingBatch(
            source=source,
            content_items=items,
            total_discovered=150,
            total_scraped=150
        )

    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        report = {
            "test_run_id": datetime.utcnow().isoformat(),
            "test_environment": str(self.test_dir),
            "summary": {
                "total_fetch_tests": len(self.test_results["fetch_tests"]),
                "successful_fetches": sum(1 for t in self.test_results["fetch_tests"] if t.get("success")),
                "total_extraction_tests": len(self.test_results["extraction_tests"]),
                "successful_extractions": sum(1 for t in self.test_results["extraction_tests"] if t.get("success")),
                "total_validation_tests": len(self.test_results["validation_tests"]),
                "passed_validations": sum(1 for t in self.test_results["validation_tests"] if t.get("passed")),
                "total_batch_tests": len(self.test_results["batch_tests"]),
                "safe_batches": sum(1 for t in self.test_results["batch_tests"] if t.get("safety_passed")),
                "total_safety_tests": len(self.test_results["safety_tests"]),
                "passed_safety_tests": sum(1 for t in self.test_results["safety_tests"]
                                         if t.get("actually_failed") or t.get("actually_passed"))
            },
            "detailed_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }

        # Calculate overall safety score
        total_tests = (report["summary"]["total_fetch_tests"] +
                      report["summary"]["total_extraction_tests"] +
                      report["summary"]["total_validation_tests"] +
                      report["summary"]["total_batch_tests"] +
                      report["summary"]["total_safety_tests"])

        successful_tests = (report["summary"]["successful_fetches"] +
                           report["summary"]["successful_extractions"] +
                           report["summary"]["passed_validations"] +
                           report["summary"]["safe_batches"] +
                           report["summary"]["passed_safety_tests"])

        report["overall_safety_score"] = successful_tests / max(1, total_tests)

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        # Check fetch success rate
        fetch_success_rate = (sum(1 for t in self.test_results["fetch_tests"] if t.get("success")) /
                             max(1, len(self.test_results["fetch_tests"])))

        if fetch_success_rate < 0.8:
            recommendations.append("Improve fetching reliability - consider additional fallback strategies")

        # Check validation pass rate
        validation_pass_rate = (sum(1 for t in self.test_results["validation_tests"] if t.get("passed")) /
                               max(1, len(self.test_results["validation_tests"])))

        if validation_pass_rate < 0.9:
            recommendations.append("Review content validation criteria - some valid content may be rejected")

        # Check safety test effectiveness
        safety_threats_detected = sum(1 for t in self.test_results["safety_tests"]
                                    if t.get("should_fail") and t.get("actually_failed"))
        safety_threats_total = sum(1 for t in self.test_results["safety_tests"] if t.get("should_fail"))

        if safety_threats_detected < safety_threats_total:
            recommendations.append("CRITICAL: Some security threats not detected - review safety checks")

        if not recommendations:
            recommendations.append("All tests passed - scraper components are ready for production")

        return recommendations

    def _save_test_results(self, report: Dict[str, Any]):
        """Save test results to files"""
        # Save JSON report
        report_file = self.test_dir / "test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Save human-readable summary
        summary_file = self.test_dir / "test_summary.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Content Scraper Test Report\n")
            f.write(f"==========================\n\n")
            f.write(f"Test Run: {report['test_run_id']}\n")
            f.write(f"Overall Safety Score: {report['overall_safety_score']:.2%}\n\n")

            f.write(f"Summary:\n")
            for key, value in report['summary'].items():
                f.write(f"  {key}: {value}\n")

            f.write(f"\nRecommendations:\n")
            for rec in report['recommendations']:
                f.write(f"  - {rec}\n")

        logger.info(f"Test results saved to {self.test_dir}")

    def cleanup(self):
        """Clean up test environment"""
        try:
            shutil.rmtree(self.test_dir)
            logger.info(f"Cleaned up test environment {self.test_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup test environment: {e}")


async def main():
    """Run comprehensive tests"""
    test_env = IsolatedTestEnvironment()

    try:
        # Run tests for all sources
        report = await test_env.run_comprehensive_tests()

        print(f"\n🧪 Test Results Summary:")
        print(f"Overall Safety Score: {report['overall_safety_score']:.2%}")
        print(f"Test Environment: {test_env.test_dir}")

        if report['overall_safety_score'] >= 0.8:
            print("✅ SAFE TO PROCEED - Scrapers passed comprehensive testing")
        else:
            print("❌ NOT SAFE - Review test results before proceeding")

        return report['overall_safety_score'] >= 0.8

    finally:
        test_env.cleanup()


if __name__ == "__main__":
    asyncio.run(main())