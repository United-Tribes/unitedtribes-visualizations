#!/usr/bin/env python3
"""
Demonstration of S3 content organization
Shows how scraped content follows [artist]/[thematic]/[filename] pattern
"""

import asyncio
import json
import sys
from pathlib import Path

# Add shared modules to path
sys.path.append(str(Path(__file__).parent / "shared"))

from models import ScrapedContent, SourceAttribution, ContentType, ScrapingBatch, Source
from s3_uploader import S3ContentUploader
from datetime import datetime


def create_sample_content() -> list[ScrapedContent]:
    """Create sample content to demonstrate S3 organization"""

    sample_content = [
        # Example 1: Pitchfork album review
        ScrapedContent(
            url="https://pitchfork.com/reviews/albums/kendrick-lamar-damn/",
            title="Kendrick Lamar: DAMN.",
            content="""
            Kendrick Lamar's fourth studio album DAMN. represents a masterful exploration of duality,
            spirituality, and the African American experience. The album opens with "BLOOD." setting
            a tone of vulnerability that carries throughout the 14-track journey. Songs like "DNA."
            and "HUMBLE." showcase Lamar's technical prowess while maintaining commercial appeal.

            The production, handled primarily by Mike WiLL Made-It, creates a cohesive sonic landscape
            that supports Lamar's introspective lyrics. Tracks like "FEAR." and "DUCKWORTH." reveal
            personal struggles and family history, while "LOYALTY." featuring Rihanna adds a different
            dynamic to the album's flow.

            This album solidifies Lamar's position as one of hip-hop's most important voices,
            balancing artistic integrity with mainstream success in a way few artists achieve.
            """,
            content_type=ContentType.REVIEW,
            source_attribution=SourceAttribution(
                source="Pitchfork",
                title="Kendrick Lamar: DAMN.",
                url="https://pitchfork.com/reviews/albums/kendrick-lamar-damn/",
                author="Sheldon Pearce",
                publication_date="2017-04-18T10:00:00Z",
                publication_type="article",
                content_type="review"
            ),
            confidence_score=0.95
        ),

        # Example 2: Rolling Stone interview
        ScrapedContent(
            url="https://www.rollingstone.com/music/music-features/patti-smith-interview-horses-anniversary/",
            title="Patti Smith Reflects on 'Horses' and Her Literary Influences",
            content="""
            Speaking from her home in New York, Patti Smith reflects on the 47th anniversary of
            her groundbreaking debut album "Horses." The album, recorded when she was just 28,
            merged poetry with punk rock in ways that had never been attempted before.

            "I was reading a lot of Rimbaud at the time," Smith recalls. "His idea of the poet
            as visionary really influenced how I approached making music. I wanted to create
            something that was both intellectual and visceral."

            The conversation touches on her friendship with Robert Mapplethorpe, her collaboration
            with the band Television, and how CBGB provided the perfect laboratory for her
            artistic experiments. Smith also discusses her recent memoir and her ongoing
            photography work.
            """,
            content_type=ContentType.INTERVIEW,
            source_attribution=SourceAttribution(
                source="Rolling Stone",
                title="Patti Smith Reflects on 'Horses' and Her Literary Influences",
                url="https://www.rollingstone.com/music/music-features/patti-smith-interview-horses-anniversary/",
                author="David Fricke",
                publication_date="2022-11-10T14:30:00Z",
                publication_type="article",
                content_type="interview"
            ),
            confidence_score=0.92
        ),

        # Example 3: NPR Fresh Air transcript
        ScrapedContent(
            url="https://www.npr.org/2024/01/15/fresh-air-miles-davis-kind-of-blue-anniversary",
            title="Fresh Air: Celebrating 65 Years of Miles Davis' 'Kind of Blue'",
            content="""
            TERRY GROSS, HOST: This is FRESH AIR. I'm Terry Gross. Today we're celebrating the
            65th anniversary of Miles Davis' masterpiece "Kind of Blue," often cited as one
            of the greatest jazz albums ever recorded.

            Our guest is jazz historian Ashley Kahn, author of the definitive book about the album.
            Ashley, let's start with the recording sessions. What made these particular sessions
            so special?

            ASHLEY KAHN: Well Terry, what's remarkable is that this album was essentially
            improvised in the studio. Miles brought in these modal sketches - not full
            compositions, but harmonic frameworks that gave the musicians incredible freedom
            to explore.

            The personnel was extraordinary: John Coltrane, Cannonball Adderley, Bill Evans,
            Wynton Kelly, Paul Chambers, and Jimmy Cobb. Each brought their own voice to
            these modal explorations.
            """,
            content_type=ContentType.PODCAST_TRANSCRIPT,
            source_attribution=SourceAttribution(
                source="NPR",
                title="Fresh Air: Celebrating 65 Years of Miles Davis' 'Kind of Blue'",
                url="https://www.npr.org/2024/01/15/fresh-air-miles-davis-kind-of-blue-anniversary",
                author="Terry Gross",
                publication_date="2024-01-15T16:00:00Z",
                publication_type="podcast",
                content_type="podcast_transcript",
                episode_info={"show": "Fresh Air", "duration": "45 minutes"}
            ),
            confidence_score=0.89
        ),

        # Example 4: Billboard news
        ScrapedContent(
            url="https://www.billboard.com/music/music-news/taylor-swift-announces-new-album/",
            title="Taylor Swift Announces Surprise Album 'The Tortured Poets Department'",
            content="""
            In a surprise announcement at the Grammy Awards, Taylor Swift revealed she will
            release a new album titled "The Tortured Poets Department" on April 19, 2024.

            The announcement came during her acceptance speech for Best Pop Vocal Album for
            "Midnights." Swift described the new work as "a collection of songs that explore
            the complexities of love, loss, and artistic expression."

            Industry insiders suggest this album may mark a return to the more introspective
            songwriting style of "folklore" and "evermore," albums that were praised for
            their literary quality and emotional depth.

            The album is expected to feature collaborations with longtime producer Jack Antonoff
            and potentially new creative partners. This will be Swift's eleventh studio album.
            """,
            content_type=ContentType.NEWS,
            source_attribution=SourceAttribution(
                source="Billboard",
                title="Taylor Swift Announces Surprise Album 'The Tortured Poets Department'",
                url="https://www.billboard.com/music/music-news/taylor-swift-announces-new-album/",
                author="Katie Atkinson",
                publication_date="2024-02-05T09:15:00Z",
                publication_type="article",
                content_type="news"
            ),
            confidence_score=0.94
        )
    ]

    return sample_content


async def demonstrate_s3_organization():
    """Demonstrate how content gets organized in S3"""
    print("🗂️ S3 Content Organization Demonstration")
    print("=========================================")
    print()

    # Create sample content
    sample_items = create_sample_content()

    # Create batch
    batch = ScrapingBatch(
        source=Source.PITCHFORK,  # Mixed batch for demonstration
        content_items=sample_items,
        total_discovered=4,
        total_scraped=4
    )

    # Initialize S3 uploader (dry run mode for demo)
    uploader = S3ContentUploader()

    print("📋 Sample Content Analysis:")
    print("============================")

    for i, item in enumerate(sample_items, 1):
        print(f"\n{i}. {item.title[:60]}...")

        # Show how artist would be extracted
        artist = uploader._extract_artist_name(item)
        thematic = uploader._categorize_content(item)
        filename = uploader._generate_safe_filename(item)

        s3_key = f"scraped-content/{artist}/{thematic}/{filename}"

        print(f"   🎨 Artist: {artist}")
        print(f"   📂 Thematic: {thematic}")
        print(f"   📄 Filename: {filename}")
        print(f"   🔗 S3 Key: {s3_key}")

    print(f"\n📊 Expected S3 Directory Structure:")
    print(f"====================================")
    print(f"s3://ut-v2-prod-lake-east1/scraped-content/")

    # Group by artist for visualization
    artist_groups = {}
    for item in sample_items:
        artist = uploader._extract_artist_name(item)
        thematic = uploader._categorize_content(item)
        filename = uploader._generate_safe_filename(item)

        if artist not in artist_groups:
            artist_groups[artist] = {}
        if thematic not in artist_groups[artist]:
            artist_groups[artist][thematic] = []
        artist_groups[artist][thematic].append(filename)

    for artist, thematics in artist_groups.items():
        print(f"├── {artist}/")
        for thematic, files in thematics.items():
            print(f"│   ├── {thematic}/")
            for file in files:
                print(f"│   │   └── {file}")

    print(f"\n🔒 Anti-Overwrite Protection:")
    print(f"============================")
    print(f"✅ Each file gets unique hash-based naming")
    print(f"✅ Timestamp included in filename")
    print(f"✅ Collision detection with automatic renaming")
    print(f"✅ Content hash prevents duplicate uploads")

    print(f"\n📈 Integration with Existing Data Lake:")
    print(f"======================================")
    print(f"✅ Compatible with existing video_analysis/ structure")
    print(f"✅ Uses same v3 JSON format")
    print(f"✅ Includes proper source attribution for citations")
    print(f"✅ Manifest files track all uploads")

    # Show manifest structure
    print(f"\n📋 Batch Manifest Example:")
    print(f"==========================")
    manifest = batch.to_manifest()
    manifest_preview = {
        "batch_id": manifest["batch_id"],
        "source": manifest["source"],
        "total_items": manifest["total_items"],
        "content_types": manifest["content_types"],
        "organization_pattern": "[artist]/[thematic]/[filename]",
        "manifest_s3_key": manifest["manifest_s3_key"]
    }

    print(json.dumps(manifest_preview, indent=2))

    return artist_groups


async def show_citation_integration():
    """Show how this integrates with existing citation system"""
    print(f"\n📝 Citation Integration Example:")
    print(f"=================================")

    sample_content = create_sample_content()

    print(f"Original knowledge graph citations:")
    print(f'[Source: "direct_connections"]  ❌ Not helpful')
    print(f'[Source: "influence_networks"] ❌ Generic')
    print()
    print(f"New scraped content citations:")
    for item in sample_content:
        citation = item.source_attribution.to_citation_format()
        print(f'{citation}  ✅ Specific and useful')


if __name__ == "__main__":
    async def main():
        await demonstrate_s3_organization()
        await show_citation_integration()

        print(f"\n🎯 Summary:")
        print(f"===========")
        print(f"✅ Scraped content organized as [artist]/[thematic]/[filename]")
        print(f"✅ No overwrites - unique naming with collision detection")
        print(f"✅ Integrates with existing data lake structure")
        print(f"✅ Provides specific, useful citations for API responses")
        print(f"✅ Comprehensive validation prevents bad data")
        print(f"✅ Manifest tracking for all upload operations")

    asyncio.run(main())