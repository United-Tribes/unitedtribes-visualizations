#!/usr/bin/env python3
"""
Safety Checklist for Content Scraper Deployment
Validates system stability before running scrapers
"""

import asyncio
import subprocess
import json
import sys
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SafetyChecker:
    """Pre-deployment safety validation"""

    def __init__(self):
        self.checks = []
        self.failed_checks = []

    async def run_all_checks(self) -> bool:
        """Run comprehensive safety checklist"""
        print("🛡️ Content Scraper Safety Checklist")
        print("====================================")
        print()

        checks = [
            ("Data Lake Integrity", self.check_data_lake_integrity),
            ("API Endpoints", self.check_api_endpoints),
            ("S3 Bucket Access", self.check_s3_access),
            ("AWS Credentials", self.check_aws_credentials),
            ("Dependencies", self.check_dependencies),
            ("Critical Artists", self.check_critical_artists),
            ("Knowledge Graph", self.check_knowledge_graph)
        ]

        all_passed = True

        for check_name, check_func in checks:
            print(f"🔍 Checking {check_name}...", end=" ")
            try:
                result = await check_func()
                if result:
                    print("✅")
                    self.checks.append((check_name, True, None))
                else:
                    print("❌")
                    self.checks.append((check_name, False, "Check failed"))
                    self.failed_checks.append(check_name)
                    all_passed = False
            except Exception as e:
                print(f"💥 {e}")
                self.checks.append((check_name, False, str(e)))
                self.failed_checks.append(check_name)
                all_passed = False

        print()
        if all_passed:
            print("✅ ALL SAFETY CHECKS PASSED - Safe to proceed with scraping")
        else:
            print("❌ SAFETY CHECKS FAILED - Do not proceed")
            print(f"Failed checks: {', '.join(self.failed_checks)}")

        return all_passed

    async def check_data_lake_integrity(self) -> bool:
        """Check data lake structure is intact"""
        try:
            # Check if enhanced knowledge graph exists
            result = subprocess.run([
                "aws", "s3", "ls",
                "s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/"
            ], capture_output=True, text=True)

            return result.returncode == 0 and "latest.json" in result.stdout
        except Exception:
            return False

    async def check_api_endpoints(self) -> bool:
        """Check critical API endpoints are working"""
        try:
            # Check health endpoint
            result = subprocess.run([
                "curl", "-s", "-f",
                "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health"
            ], capture_output=True, text=True)

            if result.returncode != 0:
                return False

            health_data = json.loads(result.stdout)
            return health_data.get("status") in ["healthy", "stable mode"]
        except Exception:
            return False

    async def check_s3_access(self) -> bool:
        """Check S3 bucket access"""
        try:
            result = subprocess.run([
                "aws", "s3", "ls", "s3://ut-v2-prod-lake-east1/"
            ], capture_output=True, text=True)

            return result.returncode == 0
        except Exception:
            return False

    async def check_aws_credentials(self) -> bool:
        """Check AWS credentials are configured"""
        try:
            result = subprocess.run([
                "aws", "sts", "get-caller-identity"
            ], capture_output=True, text=True)

            return result.returncode == 0
        except Exception:
            return False

    async def check_dependencies(self) -> bool:
        """Check required Python dependencies"""
        required_packages = [
            'boto3', 'aiohttp', 'beautifulsoup4', 'dateutil', 'ulid'
        ]

        for package in required_packages:
            try:
                # Handle package name mappings
                import_name = package.replace('-', '_')
                if package == 'beautifulsoup4':
                    import_name = 'bs4'
                elif package == 'dateutil':
                    import_name = 'dateutil'

                __import__(import_name)
            except ImportError as e:
                logger.error(f"Missing dependency: {package} (import: {import_name}) - {e}")
                return False
        return True

    async def check_critical_artists(self) -> bool:
        """Check critical artists still have proper connections"""
        critical_artists = ["Art Blakey", "Miles Davis", "Bob Dylan", "Patti Smith"]

        for artist in critical_artists:
            try:
                # Test query for each critical artist
                query_data = {
                    "query": f"tell me about {artist}",
                    "domain": "music"
                }

                result = subprocess.run([
                    "curl", "-s", "-X", "POST",
                    "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(query_data)
                ], capture_output=True, text=True)

                if result.returncode != 0:
                    return False

                response = json.loads(result.stdout)
                connections = response.get("connections", {}).get("direct_connections", [])

                if not connections or connections[0].get("connection_count", 0) < 2:
                    logger.error(f"Critical artist {artist} has insufficient connections")
                    return False

            except Exception as e:
                logger.error(f"Failed to check {artist}: {e}")
                return False

        return True

    async def check_knowledge_graph(self) -> bool:
        """Check knowledge graph has expected relationship count"""
        try:
            # Download and check knowledge graph
            result = subprocess.run([
                "aws", "s3", "cp",
                "s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json",
                "/tmp/kg_check.json"
            ], capture_output=True, text=True)

            if result.returncode != 0:
                return False

            with open("/tmp/kg_check.json", 'r') as f:
                kg_data = json.load(f)

            total_relationships = kg_data.get("metadata", {}).get("total_relationships", 0)

            # Should have 4,426+ relationships based on CLAUDE.md
            return total_relationships >= 4400

        except Exception:
            return False

    def get_report(self) -> dict:
        """Get safety check report"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_checks": len(self.checks),
            "passed_checks": len([c for c in self.checks if c[1]]),
            "failed_checks": len(self.failed_checks),
            "failed_check_names": self.failed_checks,
            "all_passed": len(self.failed_checks) == 0,
            "detailed_results": self.checks
        }


async def main():
    """Run safety checklist"""
    logging.basicConfig(level=logging.INFO)

    checker = SafetyChecker()

    print(f"Starting safety checklist at {datetime.now()}")
    print("=" * 50)

    all_passed = await checker.run_all_checks()

    # Generate report
    report = checker.get_report()

    print(f"\n📊 Safety Check Summary:")
    print(f"========================")
    print(f"Total Checks: {report['total_checks']}")
    print(f"Passed: {report['passed_checks']}")
    print(f"Failed: {report['failed_checks']}")
    print(f"Overall: {'✅ PASS' if report['all_passed'] else '❌ FAIL'}")

    if not all_passed:
        print(f"\n⚠️  CRITICAL: The following checks failed:")
        for failed_check in report['failed_check_names']:
            print(f"  - {failed_check}")
        print(f"\n🚨 DO NOT PROCEED with scraper deployment until all checks pass!")
        sys.exit(1)
    else:
        print(f"\n🎉 All safety checks passed - system is ready for scraper deployment")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())