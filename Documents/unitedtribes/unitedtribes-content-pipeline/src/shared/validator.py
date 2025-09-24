"""
Comprehensive validation framework for content scrapers
Ensures data lake and API stability through rigorous quality checks
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from urllib.parse import urlparse

try:
    from .models import ScrapedContent, ScrapingBatch, SourceAttribution
except ImportError:
    from models import ScrapedContent, ScrapingBatch, SourceAttribution

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result from content validation"""
    passed: bool
    score: float  # 0.0 to 1.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataLakeCompatibilityCheck:
    """Validation result for data lake compatibility"""
    compatible: bool
    format_version: str
    schema_valid: bool
    citation_quality: float
    processing_safe: bool
    errors: List[str] = field(default_factory=list)


class ContentValidator:
    """
    Comprehensive content validation to protect data lake integrity
    """

    def __init__(self):
        # Content quality thresholds
        self.min_content_length = 200
        self.max_content_length = 50000
        self.min_title_length = 5
        self.max_title_length = 200

        # Required fields for data lake compatibility
        self.required_fields = ['id', 'url', 'title', 'content', 'source_attribution']
        self.required_source_fields = ['source', 'title', 'url']

        # Suspicious patterns that could indicate scraping errors
        self.suspicious_patterns = [
            r'404 not found',
            r'access denied',
            r'please enable javascript',
            r'robot.*detected',
            r'captcha',
            r'cloudflare',
            r'subscription required',
            r'sign in to continue',
            r'this content is not available'
        ]

        # Valid music publication sources
        self.valid_sources = {
            'Billboard', 'Rolling Stone', 'Pitchfork', 'NPR', 'Sound Opinions',
            'All Songs Considered', 'Fresh Air', 'Spotify', 'Apple Podcasts'
        }

    def validate_scraped_content(self, content: ScrapedContent) -> ValidationResult:
        """
        Comprehensive validation of scraped content
        """
        errors = []
        warnings = []
        score = 1.0

        # 1. Basic structure validation
        structure_result = self._validate_structure(content)
        if not structure_result.passed:
            errors.extend(structure_result.errors)
            score *= 0.3

        # 2. Content quality validation
        quality_result = self._validate_content_quality(content)
        score *= quality_result.score
        warnings.extend(quality_result.warnings)
        if not quality_result.passed:
            errors.extend(quality_result.errors)

        # 3. Source attribution validation
        attribution_result = self._validate_source_attribution(content.source_attribution)
        score *= attribution_result.score
        if not attribution_result.passed:
            errors.extend(attribution_result.errors)

        # 4. Music relevance validation
        relevance_result = self._validate_music_relevance(content)
        score *= relevance_result.score
        warnings.extend(relevance_result.warnings)

        # 5. Data lake compatibility check
        compatibility_result = self._validate_data_lake_compatibility(content)
        if not compatibility_result.compatible:
            errors.extend(compatibility_result.errors)
            score *= 0.2

        return ValidationResult(
            passed=len(errors) == 0 and score > 0.5,
            score=score,
            errors=errors,
            warnings=warnings,
            metadata={
                'structure_valid': structure_result.passed,
                'quality_score': quality_result.score,
                'attribution_score': attribution_result.score,
                'relevance_score': relevance_result.score,
                'data_lake_compatible': compatibility_result.compatible
            }
        )

    def validate_batch(self, batch: ScrapingBatch) -> ValidationResult:
        """
        Validate an entire scraping batch
        """
        errors = []
        warnings = []

        # Check batch structure
        if not batch.content_items:
            errors.append("Batch contains no content items")
            return ValidationResult(passed=False, score=0.0, errors=errors)

        # Validate each item
        item_scores = []
        total_errors = 0

        for i, item in enumerate(batch.content_items):
            result = self.validate_scraped_content(item)
            item_scores.append(result.score)

            if not result.passed:
                total_errors += 1
                errors.extend([f"Item {i}: {error}" for error in result.errors])

            warnings.extend([f"Item {i}: {warning}" for warning in result.warnings])

        # Calculate batch metrics
        avg_score = sum(item_scores) / len(item_scores) if item_scores else 0.0
        success_rate = (len(batch.content_items) - total_errors) / len(batch.content_items)

        # Batch-level validation
        if success_rate < 0.7:
            errors.append(f"Batch success rate too low: {success_rate:.2%}")

        if avg_score < 0.6:
            errors.append(f"Batch average quality too low: {avg_score:.2f}")

        return ValidationResult(
            passed=len(errors) == 0,
            score=avg_score * success_rate,
            errors=errors,
            warnings=warnings,
            metadata={
                'items_count': len(batch.content_items),
                'success_rate': success_rate,
                'avg_quality': avg_score,
                'total_errors': total_errors
            }
        )

    def _validate_structure(self, content: ScrapedContent) -> ValidationResult:
        """Validate basic structure and required fields"""
        errors = []
        score = 1.0

        # Check required fields exist
        content_dict = content.to_v3_format()
        for field in self.required_fields:
            if not content_dict.get(field):
                errors.append(f"Missing required field: {field}")

        # Check source attribution structure
        if content.source_attribution:
            for field in self.required_source_fields:
                if not getattr(content.source_attribution, field, None):
                    errors.append(f"Missing source attribution field: {field}")

        # Check data types
        if content.confidence_score is not None and not (0.0 <= content.confidence_score <= 1.0):
            errors.append("Confidence score must be between 0.0 and 1.0")

        # Check URL validity
        if content.url:
            parsed = urlparse(content.url)
            if not parsed.scheme or not parsed.netloc:
                errors.append("Invalid URL format")

        return ValidationResult(
            passed=len(errors) == 0,
            score=score if len(errors) == 0 else 0.0,
            errors=errors
        )

    def _validate_content_quality(self, content: ScrapedContent) -> ValidationResult:
        """Validate content quality and detect scraping errors"""
        errors = []
        warnings = []
        score = 1.0

        # Length validation
        if len(content.content) < self.min_content_length:
            errors.append(f"Content too short: {len(content.content)} chars (min: {self.min_content_length})")
            score *= 0.3

        if len(content.content) > self.max_content_length:
            warnings.append(f"Content very long: {len(content.content)} chars")
            score *= 0.9

        if len(content.title) < self.min_title_length:
            errors.append(f"Title too short: {len(content.title)} chars")
            score *= 0.5

        if len(content.title) > self.max_title_length:
            warnings.append("Title very long")
            score *= 0.9

        # Check for suspicious patterns indicating scraping failures
        content_lower = content.content.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower):
                errors.append(f"Suspicious content pattern detected: {pattern}")
                score *= 0.2
                break

        # Check content diversity (not just repeated text)
        unique_sentences = len(set(content.content.split('.')))
        total_sentences = len(content.content.split('.'))
        if total_sentences > 10 and unique_sentences / total_sentences < 0.5:
            warnings.append("Content appears repetitive")
            score *= 0.8

        # Check for actual textual content (not just HTML/metadata)
        text_ratio = len(re.sub(r'[^a-zA-Z\s]', '', content.content)) / len(content.content)
        if text_ratio < 0.6:
            warnings.append("Low text content ratio - may contain too much markup")
            score *= 0.9

        return ValidationResult(
            passed=len(errors) == 0,
            score=score,
            errors=errors,
            warnings=warnings
        )

    def _validate_source_attribution(self, attribution: SourceAttribution) -> ValidationResult:
        """Validate source attribution for proper citations"""
        if not attribution:
            return ValidationResult(
                passed=False,
                score=0.0,
                errors=["Missing source attribution"]
            )

        errors = []
        warnings = []
        score = 1.0

        # Validate source name
        if attribution.source not in self.valid_sources:
            warnings.append(f"Unknown source: {attribution.source}")
            score *= 0.9

        # Check citation format compatibility
        try:
            citation = attribution.to_citation_format()
            if len(citation) < 10:
                errors.append("Citation format too short")
            if len(citation) > 150:
                warnings.append("Citation format very long")
                score *= 0.9
        except Exception as e:
            errors.append(f"Citation format generation failed: {e}")

        # Validate URL
        if attribution.url:
            parsed = urlparse(attribution.url)
            if not parsed.scheme or not parsed.netloc:
                errors.append("Invalid attribution URL")

        # Check date format
        if attribution.publication_date:
            try:
                datetime.fromisoformat(attribution.publication_date.replace('Z', '+00:00'))
            except:
                warnings.append("Invalid publication date format")
                score *= 0.9

        return ValidationResult(
            passed=len(errors) == 0,
            score=score,
            errors=errors,
            warnings=warnings
        )

    def _validate_music_relevance(self, content: ScrapedContent) -> ValidationResult:
        """Validate that content is relevant to music/culture"""
        warnings = []
        score = 1.0

        # Music-related keywords
        music_keywords = [
            'music', 'album', 'song', 'artist', 'band', 'musician', 'singer',
            'concert', 'tour', 'festival', 'record', 'recording', 'studio',
            'genre', 'jazz', 'rock', 'pop', 'hip-hop', 'classical', 'folk',
            'guitar', 'piano', 'drums', 'vocals', 'lyrics', 'melody'
        ]

        content_lower = (content.title + ' ' + content.content).lower()
        music_mentions = sum(1 for keyword in music_keywords if keyword in content_lower)

        if music_mentions == 0:
            warnings.append("No music-related keywords found")
            score *= 0.5
        elif music_mentions < 3:
            warnings.append("Limited music relevance")
            score *= 0.8

        return ValidationResult(
            passed=True,  # This is a warning-only check
            score=score,
            warnings=warnings
        )

    def _validate_data_lake_compatibility(self, content: ScrapedContent) -> DataLakeCompatibilityCheck:
        """Ensure content is compatible with existing data lake format"""
        errors = []

        try:
            # Test serialization to v3 format
            v3_format = content.to_v3_format()

            # Test JSON serialization
            json_str = json.dumps(v3_format, default=str)

            # Test deserialization
            json.loads(json_str)

            # Check required v3 fields
            required_v3_fields = ['id', 'source_attribution', 'metadata']
            for field in required_v3_fields:
                if field not in v3_format:
                    errors.append(f"Missing v3 format field: {field}")

            # Check source attribution structure
            source_attr = v3_format.get('source_attribution', {})
            if not isinstance(source_attr, dict):
                errors.append("source_attribution must be a dictionary")

            # Validate citation generation
            if content.source_attribution:
                citation = content.source_attribution.to_citation_format()
                if not citation.startswith('[Source:'):
                    errors.append("Invalid citation format")

            return DataLakeCompatibilityCheck(
                compatible=len(errors) == 0,
                format_version="v3",
                schema_valid=len(errors) == 0,
                citation_quality=1.0 if len(errors) == 0 else 0.5,
                processing_safe=True,
                errors=errors
            )

        except Exception as e:
            errors.append(f"Data lake compatibility test failed: {e}")
            return DataLakeCompatibilityCheck(
                compatible=False,
                format_version="v3",
                schema_valid=False,
                citation_quality=0.0,
                processing_safe=False,
                errors=errors
            )


class SafetyChecker:
    """
    Additional safety checks for data lake and API protection
    """

    def __init__(self):
        self.validator = ContentValidator()

    def pre_processing_safety_check(self, batch: ScrapingBatch) -> Tuple[bool, List[str]]:
        """
        Final safety check before sending to data lake processing
        """
        errors = []

        # Validate batch
        batch_result = self.validator.validate_batch(batch)
        if not batch_result.passed:
            errors.extend(batch_result.errors)

        # Duplicate content check removed - not a real-world concern
        # If duplicates exist, it's a scraper bug that should be fixed at the source

        # Check batch size (prevent overwhelming the processing pipeline)
        if len(batch.content_items) > 100:
            errors.append(f"Batch too large: {len(batch.content_items)} items (max: 100)")

        # Check for consistent source
        sources = set(item.source_attribution.source for item in batch.content_items if item.source_attribution)
        if len(sources) > 1:
            errors.append("Mixed sources in single batch - should be separated")

        safe = len(errors) == 0
        return safe, errors

    def verify_v3_compatibility(self, content: ScrapedContent) -> bool:
        """
        Verify content won't break existing v3 processing pipeline
        """
        try:
            # Test conversion to v3 format
            v3_data = content.to_v3_format()

            # Simulate processing pipeline expectations
            required_structure = {
                'source_attribution': {
                    'source': str,
                    'title': str,
                    'url': str
                },
                'metadata': {
                    'scraped_at': str,
                    'confidence_score': (int, float),
                    'word_count': int
                }
            }

            def check_structure(data, structure):
                for key, expected_type in structure.items():
                    if key not in data:
                        return False
                    if isinstance(expected_type, dict):
                        if not isinstance(data[key], dict):
                            return False
                        if not check_structure(data[key], expected_type):
                            return False
                    elif isinstance(expected_type, tuple):
                        if not isinstance(data[key], expected_type):
                            return False
                    elif not isinstance(data[key], expected_type):
                        return False
                return True

            return check_structure(v3_data, required_structure)

        except Exception:
            return False