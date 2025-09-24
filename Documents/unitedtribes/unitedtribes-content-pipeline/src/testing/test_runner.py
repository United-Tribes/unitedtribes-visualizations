#!/usr/bin/env python3
"""
Test runner for content scrapers
Validates scrapers before production deployment
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add shared modules to path
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from test_environment import IsolatedTestEnvironment


async def run_tests(source: str = None, verbose: bool = False) -> bool:
    """
    Run scraper tests with optional source filtering

    Args:
        source: Specific source to test (e.g., 'pitchfork')
        verbose: Enable verbose output

    Returns:
        True if all tests pass and system is safe for production
    """
    print("🧪 United Tribes Content Scraper Testing")
    print("========================================")

    if source:
        print(f"Testing source: {source}")
    else:
        print("Testing all sources")

    test_env = IsolatedTestEnvironment()

    try:
        # Run comprehensive tests
        report = await test_env.run_comprehensive_tests(source)

        # Display results
        print(f"\n📊 Test Results:")
        print(f"================")
        print(f"Overall Safety Score: {report['overall_safety_score']:.2%}")

        summary = report['summary']
        print(f"\nFetch Tests: {summary['successful_fetches']}/{summary['total_fetch_tests']} passed")
        print(f"Extraction Tests: {summary['successful_extractions']}/{summary['total_extraction_tests']} passed")
        print(f"Validation Tests: {summary['passed_validations']}/{summary['total_validation_tests']} passed")
        print(f"Batch Tests: {summary['safe_batches']}/{summary['total_batch_tests']} safe")
        print(f"Safety Tests: {summary['passed_safety_tests']}/{summary['total_safety_tests']} passed")

        print(f"\n📋 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")

        # Determine if safe for production
        is_safe = report['overall_safety_score'] >= 0.8

        if is_safe:
            print(f"\n✅ PASS: Scrapers are SAFE for production deployment")
        else:
            print(f"\n❌ FAIL: Scrapers are NOT SAFE - review issues before proceeding")

        if verbose:
            print(f"\nDetailed results saved to: {test_env.test_dir}")

        return is_safe

    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return False

    finally:
        test_env.cleanup()


def main():
    """Command line interface for test runner"""
    parser = argparse.ArgumentParser(description="Test content scrapers before production")
    parser.add_argument("--source", help="Test specific source (pitchfork, rolling_stone, billboard, npr)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Run tests
    success = asyncio.run(run_tests(args.source, args.verbose))

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()