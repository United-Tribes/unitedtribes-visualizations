#!/usr/bin/env python3
"""
Canonical knowledge graph builder from all content sources
Builds enhanced knowledge graph from videos, books, and scraped content
(Previously named emergency_rebuild - this is actually our production KG builder)
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmergencyKnowledgeGraphRebuilder:
    def __init__(self, bucket_name: str = 'ut-v2-prod-lake-east1'):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name
        self.video_prefix = 'video_analysis/'
        self.books_prefix = 'enhanced-knowledge-graph/'
        self.scraped_content_prefix = 'scraped-content/'

    def list_all_video_files(self) -> List[str]:
        """List all video analysis JSON files"""
        logger.info(f"Scanning {self.video_prefix} for video analysis files...")

        paginator = self.s3.get_paginator('list_objects_v2')
        video_files = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.video_prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith('.json') and 'video_' in key:
                        video_files.append(key)

        logger.info(f"Found {len(video_files)} video analysis files")
        return video_files

    def extract_relationships_from_video(self, video_key: str) -> List[Dict[str, Any]]:
        """Extract relationships from a video analysis file"""
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=video_key)
            video_data = json.loads(response['Body'].read())

            relationships = []

            # Extract people relationships
            if 'entities' in video_data and 'people' in video_data['entities']:
                people = video_data['entities']['people']
                source_info = video_data.get('source_info', {})
                artist = source_info.get('artist', 'Unknown Artist')

                for person in people:
                    if isinstance(person, dict) and 'name' in person:
                        relationship = {
                            'source_entity': artist,
                            'target_entity': person['name'],
                            'relationship_type': 'mentioned_with',
                            'confidence': person.get('confidence', 0.8),
                            'evidence': f"Mentioned together in video analysis: {source_info.get('title', video_key)}",
                            'source_attribution': {
                                'source': source_info.get('source', 'Video Analysis'),
                                'title': source_info.get('title', ''),
                                'youtube_url': source_info.get('youtube_url', ''),
                                'processing_method': 'video_analysis_extraction'
                            },
                            'metadata': {
                                'content_type': 'video',
                                'themes': ['music', 'collaboration'],
                                'enhancement_date': datetime.now().isoformat(),
                                'source_file': video_key
                            }
                        }
                        relationships.append(relationship)

            return relationships

        except Exception as e:
            logger.error(f"Error processing {video_key}: {e}")
            return []

    def list_all_scraped_files(self) -> List[str]:
        """List all scraped content JSON files"""
        logger.info(f"Scanning {self.scraped_content_prefix} for scraped content files...")

        paginator = self.s3.get_paginator('list_objects_v2')
        scraped_files = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.scraped_content_prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith('.json'):
                        scraped_files.append(key)

        logger.info(f"Found {len(scraped_files)} scraped content files")
        return scraped_files

    def extract_relationships_from_scraped_content(self, scraped_key: str) -> List[Dict[str, Any]]:
        """Extract relationships from a scraped content file"""
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=scraped_key)
            content_data = json.loads(response['Body'].read())

            relationships = []

            # Extract basic article info
            title = content_data.get('title', '')
            content_text = content_data.get('content', '')
            source_attr = content_data.get('source_attribution', {})
            source_name = source_attr.get('source', 'Unknown Source')

            # Jazz artists to detect (from our 25 target artists)
            jazz_artists = [
                'John Coltrane', 'Lee Morgan', 'Art Blakey', 'Horace Silver', 'Charlie Parker',
                'Grant Green', 'Dexter Gordon', 'Kenny Drew', 'Paul Chambers', 'Philly Joe Jones',
                'Herbie Hancock', 'Freddie Hubbard', 'Joe Henderson', 'Donald Byrd', 'Wayne Shorter',
                'Thelonious Monk', 'Duke Ellington', 'Dizzy Gillespie', 'Joe Pass',
                'Miles Davis', 'Bill Evans', 'Cannonball Adderley', 'Bill Charlap', 'John Scofield', 'Pat Metheny'
            ]

            # Detect artist mentions in content
            text_to_search = (title + ' ' + content_text).lower()
            detected_artists = []

            for artist in jazz_artists:
                if artist.lower() in text_to_search:
                    detected_artists.append(artist)

            # Create relationships for detected artists
            for artist in detected_artists:
                # Artist -> Article relationship
                relationship = {
                    'source_entity': artist,
                    'target_entity': f"{source_name} Article: {title[:50]}...",
                    'relationship_type': 'featured_in',
                    'confidence': 0.9,
                    'evidence': f"Featured in {source_name} article: {title}",
                    'source_attribution': {
                        'source': source_name,
                        'title': title,
                        'url': source_attr.get('url', ''),
                        'author': source_attr.get('author', ''),
                        'publication_date': source_attr.get('publication_date', ''),
                        'processing_method': 'scraped_content_extraction'
                    },
                    'metadata': {
                        'content_type': 'article',
                        'themes': ['music', 'journalism'],
                        'enhancement_date': datetime.now().isoformat(),
                        'source_file': scraped_key,
                        'artist_mention_count': text_to_search.count(artist.lower())
                    }
                }
                relationships.append(relationship)

                # If multiple artists detected, create cross-relationships
                for other_artist in detected_artists:
                    if other_artist != artist:
                        cross_relationship = {
                            'source_entity': artist,
                            'target_entity': other_artist,
                            'relationship_type': 'mentioned_with',
                            'confidence': 0.8,
                            'evidence': f"Both mentioned in {source_name} article: {title}",
                            'source_attribution': {
                                'source': source_name,
                                'title': title,
                                'url': source_attr.get('url', ''),
                                'processing_method': 'scraped_content_cross_reference'
                            },
                            'metadata': {
                                'content_type': 'article',
                                'themes': ['music', 'collaboration'],
                                'enhancement_date': datetime.now().isoformat(),
                                'source_file': scraped_key
                            }
                        }
                        relationships.append(cross_relationship)

            return relationships

        except Exception as e:
            logger.error(f"Error processing scraped content {scraped_key}: {e}")
            return []

    def load_existing_books_data(self) -> Dict[str, Any]:
        """Load existing books data from current enhanced knowledge graph"""
        try:
            kg_key = 'enhanced-knowledge-graph/current/latest.json'
            response = self.s3.get_object(Bucket=self.bucket, Key=kg_key)
            existing_kg = json.loads(response['Body'].read())
            logger.info(f"Loaded existing knowledge graph with {len(existing_kg.get('relationships', []))} relationships")
            return existing_kg
        except Exception as e:
            logger.warning(f"Could not load existing knowledge graph: {e}")
            return {'relationships': [], 'metadata': {'source_files': []}}

    def rebuild_enhanced_knowledge_graph(self, include_scraped_content: bool = False):
        """Rebuild the complete enhanced knowledge graph"""
        logger.info("🚀 Starting canonical knowledge graph rebuild...")

        # Load existing book relationships
        enhanced_kg = self.load_existing_books_data()
        existing_relationships = enhanced_kg.get('relationships', [])

        # Get all video files
        video_files = self.list_all_video_files()

        # Extract relationships from all videos
        video_relationships = []
        artist_stats = defaultdict(int)

        for i, video_key in enumerate(video_files):
            if i % 10 == 0:
                logger.info(f"Processing video {i+1}/{len(video_files)}: {video_key}")

            relationships = self.extract_relationships_from_video(video_key)
            video_relationships.extend(relationships)

            # Track artist coverage
            for rel in relationships:
                artist_stats[rel['source_entity']] += 1

        logger.info(f"Extracted {len(video_relationships)} relationships from {len(video_files)} videos")
        logger.info(f"Coverage: {len(artist_stats)} artists with video analysis")

        # Process scraped content if requested
        scraped_relationships = []
        scraped_stats = defaultdict(int)
        if include_scraped_content:
            logger.info("🎵 Processing scraped content...")
            scraped_files = self.list_all_scraped_files()

            for i, scraped_key in enumerate(scraped_files):
                if i % 10 == 0:
                    logger.info(f"Processing scraped content {i+1}/{len(scraped_files)}: {scraped_key}")

                relationships = self.extract_relationships_from_scraped_content(scraped_key)
                scraped_relationships.extend(relationships)

                # Track artist coverage from scraped content
                for rel in relationships:
                    scraped_stats[rel['source_entity']] += 1

            logger.info(f"Extracted {len(scraped_relationships)} relationships from {len(scraped_files)} scraped articles")
            logger.info(f"Scraped content coverage: {len(scraped_stats)} artists with article mentions")

        # Show top artists by relationship count
        combined_stats = defaultdict(int)
        for artist, count in artist_stats.items():
            combined_stats[artist] += count
        for artist, count in scraped_stats.items():
            combined_stats[artist] += count

        top_artists = sorted(combined_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        logger.info("Top artists by total relationship count:")
        for artist, count in top_artists:
            video_count = artist_stats.get(artist, 0)
            scraped_count = scraped_stats.get(artist, 0)
            logger.info(f"  {artist}: {count} total ({video_count} video, {scraped_count} articles)")

        # Combine all relationships
        all_relationships = existing_relationships + video_relationships + scraped_relationships

        # Create enhanced knowledge graph
        timestamp = datetime.now().isoformat()
        enhanced_graph = {
            'relationships': all_relationships,
            'artists_data': {},  # Keep existing structure
            'entities': {},      # Keep existing structure
            'metadata': {
                'total_relationships': len(all_relationships),
                'video_relationships': len(video_relationships),
                'scraped_relationships': len(scraped_relationships),
                'book_relationships': len(existing_relationships),
                'rebuild_timestamp': timestamp,
                'rebuild_method': 'canonical_multi_source_aggregation',
                'video_files_processed': len(video_files),
                'scraped_files_processed': len(scraped_files) if include_scraped_content else 0,
                'artists_with_video_data': len(artist_stats),
                'artists_with_scraped_data': len(scraped_stats),
                'scraped_content_included': include_scraped_content,
                'source_files': enhanced_kg.get('metadata', {}).get('source_files', []) + [
                    {'key': f'canonical_rebuild_{timestamp}', 'type': 'canonical_rebuild', 'includes_scraped': include_scraped_content}
                ]
            }
        }

        # Upload the rebuilt knowledge graph
        output_key = f'enhanced-knowledge-graph/current/latest.json'
        backup_key = f'enhanced-knowledge-graph/backups/rebuild_{timestamp.replace(":", "-")}.json'

        # Create backup
        self.s3.put_object(
            Bucket=self.bucket,
            Key=backup_key,
            Body=json.dumps(enhanced_graph, indent=2),
            ContentType='application/json'
        )

        # Update current
        self.s3.put_object(
            Bucket=self.bucket,
            Key=output_key,
            Body=json.dumps(enhanced_graph, indent=2),
            ContentType='application/json'
        )

        logger.info(f"✅ Canonical knowledge graph rebuilt successfully!")
        logger.info(f"📊 Total relationships: {len(all_relationships)}")
        logger.info(f"📹 Video relationships: {len(video_relationships)}")
        if include_scraped_content:
            logger.info(f"📰 Scraped content relationships: {len(scraped_relationships)}")
        logger.info(f"📚 Book relationships: {len(existing_relationships)}")
        logger.info(f"🎵 Artists with content: {len(combined_stats)}")
        logger.info(f"💾 Saved to: s3://{self.bucket}/{output_key}")
        logger.info(f"🔄 Backup saved to: s3://{self.bucket}/{backup_key}")

        return enhanced_graph

if __name__ == '__main__':
    import sys

    # Check for command line argument to include scraped content
    include_scraped = '--include-scraped-content' in sys.argv

    rebuilder = EmergencyKnowledgeGraphRebuilder()
    result = rebuilder.rebuild_enhanced_knowledge_graph(include_scraped_content=include_scraped)

    print(f"\n🎉 CANONICAL KNOWLEDGE GRAPH REBUILD COMPLETE!")
    print(f"Enhanced knowledge graph built with {result['metadata']['total_relationships']} total relationships")
    print(f"Video relationships: {result['metadata']['video_relationships']}")
    if include_scraped:
        print(f"Scraped content relationships: {result['metadata']['scraped_relationships']}")
    print(f"Book relationships: {result['metadata']['book_relationships']}")
    print(f"Artists with video data: {result['metadata']['artists_with_video_data']}")
    if include_scraped:
        print(f"Artists with scraped data: {result['metadata']['artists_with_scraped_data']}")