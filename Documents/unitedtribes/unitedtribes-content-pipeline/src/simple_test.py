#!/usr/bin/env python3
"""
Simple test of scraper components
Direct test without complex imports
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add paths
sys.path.append(str(Path(__file__).parent / "shared"))

# Test basic imports
try:
    from models import ScrapedContent, SourceAttribution, ContentType
    print("✅ Models import successful")
except Exception as e:
    print(f"❌ Models import failed: {e}")
    sys.exit(1)

try:
    from validator import ContentValidator
    print("✅ Validator import successful")
except Exception as e:
    print(f"❌ Validator import failed: {e}")
    sys.exit(1)

try:
    from fetcher import EnhancedFetcher
    print("✅ Fetcher import successful")
except Exception as e:
    print(f"❌ Fetcher import failed: {e}")
    sys.exit(1)

try:
    from s3_uploader import S3ContentUploader
    print("✅ S3 Uploader import successful")
except Exception as e:
    print(f"❌ S3 Uploader import failed: {e}")
    sys.exit(1)


async def test_basic_functionality():
    """Test basic scraper functionality"""
    print("\n🧪 Testing Basic Functionality")
    print("==============================")

    # Test 1: Create sample content
    print("1. Creating sample content...", end=" ")
    try:
        attribution = SourceAttribution(
            source="Test Source",
            title="Test Article",
            url="https://example.com/test",
            author="Test Author",
            publication_date="2024-01-15T10:00:00Z"
        )

        content = ScrapedContent(
            url="https://example.com/test",
            title="Test Article: Musical Analysis",
            content="""This is a comprehensive test article about music with sufficient content for validation.
            It discusses musical elements and provides detailed analysis of various aspects of contemporary music.
            The article explores themes of creativity, artistic expression, and the evolution of musical genres
            over time. It examines how different artists approach songwriting, production techniques, and the
            cultural impact of their work. The piece also delves into the relationship between technology and
            music creation, discussing how digital tools have transformed the recording process and opened new
            possibilities for artistic expression.""",
            content_type=ContentType.ARTICLE,
            source_attribution=attribution
        )

        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        return False

    # Test 2: Validate content
    print("2. Validating content...", end=" ")
    try:
        validator = ContentValidator()
        result = validator.validate_scraped_content(content)
        if result.passed:
            print(f"✅ (score: {result.score:.2f})")
        else:
            print(f"❌ Validation failed: {result.errors}")
            return False
    except Exception as e:
        print(f"❌ {e}")
        return False

    # Test 3: Test S3 key generation
    print("3. Testing S3 organization...", end=" ")
    try:
        uploader = S3ContentUploader()
        artist = uploader._extract_artist_name(content)
        thematic = uploader._categorize_content(content)
        filename = uploader._generate_safe_filename(content)

        print(f"✅")
        print(f"   Artist: {artist}")
        print(f"   Thematic: {thematic}")
        print(f"   Filename: {filename}")
        print(f"   S3 Key: scraped-content/{artist}/{thematic}/{filename}")

    except Exception as e:
        print(f"❌ {e}")
        return False

    # Test 4: Test fetcher (basic)
    print("4. Testing fetcher initialization...", end=" ")
    try:
        async with EnhancedFetcher(rate_limit=2.0) as fetcher:
            print("✅")
    except Exception as e:
        print(f"❌ {e}")
        return False

    return True


async def main():
    """Run simple tests"""
    print("🧪 Content Scraper Component Test")
    print("==================================")

    # Test imports
    print("✅ All imports successful")

    # Test basic functionality
    success = await test_basic_functionality()

    if success:
        print("\n🎉 All tests passed - components are working correctly!")
        print("\n💡 Next step: Deploy to Lambda for cloud execution")
        return True
    else:
        print("\n❌ Tests failed - check errors above")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)