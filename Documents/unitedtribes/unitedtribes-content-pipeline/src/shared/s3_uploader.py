"""
S3 Uploader for scraped content
Organizes content using [artist]/[thematic]/[scraped filename] pattern
Ensures no overwrites of existing content
"""

import boto3
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
from dataclasses import asdict

from models import ScrapedContent, ScrapingBatch

logger = logging.getLogger(__name__)


class S3ContentUploader:
    """
    Uploads scraped content to S3 with artist/thematic organization
    Prevents overwrites and maintains data integrity
    """

    def __init__(self, bucket_name: str = "ut-v2-prod-lake-east1"):
        self.bucket_name = bucket_name
        self.s3_client = None

        # Artist extraction patterns for organizing content
        self.artist_patterns = [
            # Artist mentioned in title
            r'^([^:]+?)(?:\s*[-:]\s*)',
            # "Artist Name" in quotes
            r'"([^"]+)"',
            # Artist review/interview patterns
            r'(?:review|interview):\s*([^,\n]+)',
            r'(?:with|featuring)\s+([^,\n]+)',
        ]

        # Thematic categorization
        self.thematic_categories = {
            'review': ['review', 'album review', 'music review', 'rating'],
            'interview': ['interview', 'q&a', 'talks about', 'conversation with'],
            'news': ['news', 'breaking', 'announces', 'released', 'signs'],
            'feature': ['feature', 'profile', 'story', 'deep dive'],
            'analysis': ['analysis', 'breakdown', 'explained', 'history of'],
            'podcast': ['podcast', 'episode', 'fresh air', 'sound opinions']
        }

    def _get_s3_client(self):
        """Initialize S3 client with proper error handling"""
        if not self.s3_client:
            try:
                self.s3_client = boto3.client('s3')
                # Test connectivity
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"✅ Connected to S3 bucket: {self.bucket_name}")
            except NoCredentialsError:
                logger.error("❌ AWS credentials not found")
                raise
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    logger.error(f"❌ S3 bucket {self.bucket_name} not found")
                else:
                    logger.error(f"❌ S3 connection error: {e}")
                raise
        return self.s3_client

    async def upload_batch(self, batch: ScrapingBatch) -> Dict[str, Any]:
        """
        Upload entire batch to S3 with proper organization

        Returns:
            Upload results with success/failure details
        """
        logger.info(f"📤 Uploading batch {batch.batch_id} to S3")

        s3_client = self._get_s3_client()

        upload_results = {
            "batch_id": batch.batch_id,
            "total_items": len(batch.content_items),
            "successful_uploads": 0,
            "failed_uploads": 0,
            "uploaded_keys": [],
            "errors": [],
            "manifest_key": None
        }

        # Upload individual content items
        for i, content_item in enumerate(batch.content_items):
            try:
                s3_key = await self._upload_content_item(content_item, s3_client)
                if s3_key:
                    upload_results["successful_uploads"] += 1
                    upload_results["uploaded_keys"].append(s3_key)
                    logger.info(f"✅ Uploaded item {i+1}/{len(batch.content_items)}: {s3_key}")
                else:
                    upload_results["failed_uploads"] += 1

            except Exception as e:
                logger.error(f"❌ Failed to upload item {i+1}: {e}")
                upload_results["failed_uploads"] += 1
                upload_results["errors"].append(f"Item {i+1}: {str(e)}")

        # Upload batch manifest
        try:
            manifest_key = await self._upload_batch_manifest(batch, upload_results, s3_client)
            upload_results["manifest_key"] = manifest_key
            logger.info(f"✅ Uploaded batch manifest: {manifest_key}")
        except Exception as e:
            logger.error(f"❌ Failed to upload batch manifest: {e}")
            upload_results["errors"].append(f"Manifest upload failed: {str(e)}")

        logger.info(f"📊 Batch upload completed: {upload_results['successful_uploads']}/{upload_results['total_items']} successful")
        return upload_results

    async def _upload_content_item(self, content: ScrapedContent, s3_client) -> Optional[str]:
        """Upload single content item with artist/thematic organization"""

        # Extract artist and thematic category
        artist_name = self._extract_artist_name(content)
        thematic_category = self._categorize_content(content)

        # Generate unique filename
        filename = self._generate_safe_filename(content)

        # Construct S3 key following [artist]/[thematic]/[filename] pattern
        s3_key = f"scraped-content/{artist_name}/{thematic_category}/{filename}"

        # Check if file already exists
        if await self._key_exists(s3_key, s3_client):
            # Generate unique key to avoid overwrite
            s3_key = await self._generate_unique_key(s3_key, s3_client)
            logger.info(f"🔄 File exists, using unique key: {s3_key}")

        # Prepare content for upload
        upload_data = content.to_v3_format()
        upload_data['s3_metadata'] = {
            'artist_extracted': artist_name,
            'thematic_category': thematic_category,
            'upload_timestamp': datetime.utcnow().isoformat(),
            'uploader_version': 'content_scraper_v3.0'
        }

        try:
            # Upload to S3
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(upload_data, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'artist': artist_name,
                    'category': thematic_category,
                    'source': content.source_attribution.source if content.source_attribution else 'unknown',
                    'content-type': content.content_type.value,
                    'upload-date': datetime.utcnow().strftime('%Y-%m-%d')
                }
            )

            # Update content object with final S3 key
            content.s3_key = s3_key

            return s3_key

        except Exception as e:
            logger.error(f"❌ S3 upload failed for {s3_key}: {e}")
            return None

    def _extract_artist_name(self, content: ScrapedContent) -> str:
        """Extract artist name for S3 organization"""
        # Try to extract from title first
        title = content.title.lower()

        # Remove common prefixes
        title = re.sub(r'^(review|interview|new music):\s*', '', title, flags=re.IGNORECASE)

        # Try extraction patterns
        for pattern in self.artist_patterns:
            match = re.search(pattern, content.title, re.IGNORECASE)
            if match:
                artist = match.group(1).strip()
                return self._sanitize_artist_name(artist)

        # Try extracting from content (first few sentences)
        content_start = content.content[:500].lower()

        # Look for "Artist's new album" or "Artist releases"
        artist_mention_patterns = [
            r"([a-z\s]+)'s\s+(?:new|latest|upcoming)\s+(?:album|single|ep)",
            r"([a-z\s]+)\s+(?:releases|announces|drops)\s+",
            r"(?:musician|artist|singer)\s+([a-z\s]+)\s+"
        ]

        for pattern in artist_mention_patterns:
            match = re.search(pattern, content_start)
            if match:
                artist = match.group(1).strip()
                if len(artist.split()) <= 3:  # Reasonable artist name length
                    return self._sanitize_artist_name(artist)

        # Fallback: use source name
        source = content.source_attribution.source if content.source_attribution else "unknown"
        return self._sanitize_artist_name(f"various_{source.lower()}")

    def _categorize_content(self, content: ScrapedContent) -> str:
        """Categorize content thematically"""
        text = (content.title + " " + content.content[:500]).lower()

        # Check against thematic patterns
        for category, patterns in self.thematic_categories.items():
            for pattern in patterns:
                if pattern in text:
                    return category

        # Use content type as fallback
        return content.content_type.value

    def _sanitize_artist_name(self, artist: str) -> str:
        """Sanitize artist name for S3 key usage"""
        # Convert to lowercase and replace spaces/special chars
        sanitized = re.sub(r'[^a-z0-9\s]', '', artist.lower())
        sanitized = re.sub(r'\s+', '_', sanitized.strip())

        # Limit length and remove trailing underscores
        sanitized = sanitized[:50].strip('_')

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown_artist"

        return sanitized

    def _generate_safe_filename(self, content: ScrapedContent) -> str:
        """Generate safe filename for S3"""
        # Use content hash and timestamp for uniqueness
        timestamp = content.scraped_at.strftime("%Y%m%d_%H%M")
        content_hash = content.content_hash[:8] if content.content_hash else "unknown"

        # Sanitize title for filename
        title_part = re.sub(r'[^a-zA-Z0-9\s]', '', content.title)
        title_part = re.sub(r'\s+', '_', title_part.strip())[:30]

        source = content.source_attribution.source.lower().replace(' ', '_') if content.source_attribution else "unknown"

        return f"{source}_{timestamp}_{content_hash}_{title_part}.json"

    async def _key_exists(self, s3_key: str, s3_client) -> bool:
        """Check if S3 key already exists"""
        try:
            s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    async def _generate_unique_key(self, base_key: str, s3_client) -> str:
        """Generate unique key to avoid overwrites"""
        base_name, extension = base_key.rsplit('.', 1)
        counter = 1

        while counter < 100:  # Prevent infinite loop
            unique_key = f"{base_name}_{counter:03d}.{extension}"
            if not await self._key_exists(unique_key, s3_client):
                return unique_key
            counter += 1

        # If still not unique, add timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{base_name}_{timestamp}.{extension}"

    async def _upload_batch_manifest(self, batch: ScrapingBatch, upload_results: Dict[str, Any], s3_client) -> str:
        """Upload batch processing manifest"""

        # Generate manifest content
        manifest_data = {
            **batch.to_manifest(),
            "upload_results": {
                "successful_uploads": upload_results["successful_uploads"],
                "failed_uploads": upload_results["failed_uploads"],
                "uploaded_s3_keys": upload_results["uploaded_keys"],
                "upload_errors": upload_results["errors"]
            },
            "s3_organization": {
                "bucket": self.bucket_name,
                "base_prefix": "scraped-content/",
                "organization_pattern": "[artist]/[thematic]/[filename]",
                "prevent_overwrites": True
            }
        }

        # Generate manifest S3 key
        date_str = batch.created_at.strftime("%Y/%m/%d")
        source_name = batch.source.value if batch.source else "unknown"
        manifest_key = f"manifests/scraped/{source_name}/{date_str}/batch_{batch.batch_id}.json"

        # Upload manifest
        s3_client.put_object(
            Bucket=self.bucket_name,
            Key=manifest_key,
            Body=json.dumps(manifest_data, indent=2, default=str),
            ContentType='application/json',
            Metadata={
                'batch-id': batch.batch_id,
                'source': source_name,
                'upload-date': datetime.utcnow().strftime('%Y-%m-%d'),
                'manifest-type': 'scraped-content-batch'
            }
        )

        return manifest_key

    async def list_existing_content(self, artist: str = None, thematic: str = None) -> List[str]:
        """List existing content to avoid duplicates"""
        s3_client = self._get_s3_client()

        # Build prefix for search
        prefix = "scraped-content/"
        if artist:
            prefix += f"{self._sanitize_artist_name(artist)}/"
            if thematic:
                prefix += f"{thematic}/"

        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            existing_keys = []
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        existing_keys.append(obj['Key'])

            return existing_keys

        except Exception as e:
            logger.error(f"❌ Failed to list existing content: {e}")
            return []

    def get_upload_statistics(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate upload statistics"""
        return {
            "total_processed": batch_results["total_items"],
            "successful_uploads": batch_results["successful_uploads"],
            "failed_uploads": batch_results["failed_uploads"],
            "success_rate": batch_results["successful_uploads"] / max(1, batch_results["total_items"]),
            "s3_keys_created": len(batch_results["uploaded_keys"]),
            "manifest_created": batch_results["manifest_key"] is not None,
            "bucket": self.bucket_name,
            "organization_pattern": "[artist]/[thematic]/[filename]"
        }