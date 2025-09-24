"""
Jazz Artist Progress Tracker
Tracks content discovery progress for all 25 jazz artists
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ArtistProgress:
    """Track progress for individual artist"""
    name: str
    priority: str  # "high", "medium", "low"
    category: str  # "primary", "masters", "extended"

    # Discovery stats
    discovered_urls: int = 0
    scraped_articles: int = 0
    uploaded_articles: int = 0

    # Content breakdown
    content_by_source: Dict[str, int] = field(default_factory=dict)
    content_types_found: List[str] = field(default_factory=list)

    # Quality metrics
    avg_relevance_score: float = 0.0
    best_article_title: str = ""
    best_article_url: str = ""

    # Status tracking
    status: str = "pending"  # "pending", "in_progress", "completed", "no_content"
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    errors: List[str] = field(default_factory=list)


class JazzArtistTracker:
    """
    Tracks content discovery progress for all 25 jazz artists
    Provides real-time updates during harvest
    """

    def __init__(self):
        self.artists = self._initialize_artists()
        self.session_id = f"harvest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.session_stats = {
            "start_time": datetime.utcnow().isoformat(),
            "total_artists": len(self.artists),
            "completed_artists": 0,
            "total_content_found": 0,
            "sources_processed": [],
            "errors": []
        }

    def _initialize_artists(self) -> Dict[str, ArtistProgress]:
        """Initialize all 25 jazz artists for tracking"""

        # Primary Blue Note Legends (5)
        primary_artists = [
            "John Coltrane", "Lee Morgan", "Art Blakey",
            "Horace Silver", "Charlie Parker"
        ]

        # Blue Note Masters (14)
        masters_artists = [
            "Grant Green", "Dexter Gordon", "Kenny Drew", "Paul Chambers",
            "Philly Joe Jones", "Herbie Hancock", "Freddie Hubbard",
            "Joe Henderson", "Donald Byrd", "Wayne Shorter", "Thelonious Monk",
            "Duke Ellington", "Dizzy Gillespie", "Joe Pass"
        ]

        # Extended Network (6)
        extended_artists = [
            "Miles Davis", "Bill Evans", "Cannonball Adderley",
            "Bill Charlap", "John Scofield", "Pat Metheny"
        ]

        artists = {}

        # Initialize primary artists (high priority)
        for name in primary_artists:
            artists[name] = ArtistProgress(
                name=name,
                priority="high",
                category="primary"
            )

        # Initialize masters (medium priority)
        for name in masters_artists:
            artists[name] = ArtistProgress(
                name=name,
                priority="medium",
                category="masters"
            )

        # Initialize extended network (varies)
        for name in extended_artists:
            priority = "high" if name == "Miles Davis" else "low"
            artists[name] = ArtistProgress(
                name=name,
                priority=priority,
                category="extended"
            )

        return artists

    def start_artist_processing(self, artist_name: str):
        """Mark artist as in progress"""
        if artist_name in self.artists:
            self.artists[artist_name].status = "in_progress"
            self.artists[artist_name].last_updated = datetime.utcnow().isoformat()
            logger.info(f"🎯 Started processing: {artist_name}")

    def update_artist_discovery(self, artist_name: str, source: str, urls_found: int):
        """Update discovery stats for artist"""
        if artist_name in self.artists:
            artist = self.artists[artist_name]
            artist.discovered_urls += urls_found
            if source not in artist.content_by_source:
                artist.content_by_source[source] = 0
            artist.content_by_source[source] += urls_found
            artist.last_updated = datetime.utcnow().isoformat()

            logger.info(f"📊 {artist_name}: Found {urls_found} URLs from {source}")

    def update_artist_content(self, artist_name: str, source: str,
                            scraped: int, uploaded: int, content_type: str,
                            best_article: Dict[str, str] = None):
        """Update content stats for artist"""
        if artist_name in self.artists:
            artist = self.artists[artist_name]
            artist.scraped_articles += scraped
            artist.uploaded_articles += uploaded

            if content_type not in artist.content_types_found:
                artist.content_types_found.append(content_type)

            if best_article:
                artist.best_article_title = best_article.get("title", "")
                artist.best_article_url = best_article.get("url", "")

            artist.last_updated = datetime.utcnow().isoformat()

            logger.info(f"📝 {artist_name}: {scraped} scraped, {uploaded} uploaded from {source}")

    def complete_artist_processing(self, artist_name: str, success: bool = True):
        """Mark artist processing as complete"""
        if artist_name in self.artists:
            artist = self.artists[artist_name]

            if success and artist.scraped_articles > 0:
                artist.status = "completed"
                self.session_stats["completed_artists"] += 1
                self.session_stats["total_content_found"] += artist.scraped_articles
                logger.info(f"✅ {artist_name}: Completed successfully ({artist.scraped_articles} articles)")
            elif success and artist.scraped_articles == 0:
                artist.status = "no_content"
                logger.info(f"⚪ {artist_name}: No content found")
            else:
                artist.status = "failed"
                logger.warning(f"❌ {artist_name}: Processing failed")

            artist.last_updated = datetime.utcnow().isoformat()

    def add_error(self, artist_name: str, error: str):
        """Add error for specific artist"""
        if artist_name in self.artists:
            self.artists[artist_name].errors.append(error)
            self.session_stats["errors"].append(f"{artist_name}: {error}")

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get current progress summary"""
        completed = sum(1 for a in self.artists.values() if a.status == "completed")
        in_progress = sum(1 for a in self.artists.values() if a.status == "in_progress")
        no_content = sum(1 for a in self.artists.values() if a.status == "no_content")
        failed = sum(1 for a in self.artists.values() if a.status == "failed")

        return {
            "session_id": self.session_id,
            "total_artists": len(self.artists),
            "completed": completed,
            "in_progress": in_progress,
            "no_content": no_content,
            "failed": failed,
            "pending": len(self.artists) - completed - in_progress - no_content - failed,
            "total_content_found": sum(a.scraped_articles for a in self.artists.values()),
            "progress_percentage": (completed + no_content) / len(self.artists) * 100
        }

    def print_live_progress(self):
        """Print live progress update"""
        summary = self.get_progress_summary()

        print(f"\n🎵 Jazz Artist Harvest Progress")
        print(f"===============================")
        print(f"Session: {self.session_id}")
        print(f"Progress: {summary['progress_percentage']:.1f}% ({summary['completed'] + summary['no_content']}/{summary['total_artists']})")
        print(f"✅ Completed: {summary['completed']}")
        print(f"🔄 In Progress: {summary['in_progress']}")
        print(f"⚪ No Content: {summary['no_content']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"📝 Total Content: {summary['total_content_found']} articles")

        # Show recent activity
        recent_artists = sorted(
            [a for a in self.artists.values() if a.status in ["completed", "no_content"]],
            key=lambda x: x.last_updated,
            reverse=True
        )[:5]

        if recent_artists:
            print(f"\n🕐 Recent Activity:")
            for artist in recent_artists:
                status_icon = "✅" if artist.status == "completed" else "⚪"
                print(f"  {status_icon} {artist.name}: {artist.scraped_articles} articles")

    def get_artist_details(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for specific artist"""
        if artist_name not in self.artists:
            return None

        artist = self.artists[artist_name]
        return {
            "name": artist.name,
            "priority": artist.priority,
            "category": artist.category,
            "status": artist.status,
            "discovered_urls": artist.discovered_urls,
            "scraped_articles": artist.scraped_articles,
            "uploaded_articles": artist.uploaded_articles,
            "content_by_source": artist.content_by_source,
            "content_types_found": artist.content_types_found,
            "best_article": {
                "title": artist.best_article_title,
                "url": artist.best_article_url
            } if artist.best_article_title else None,
            "last_updated": artist.last_updated,
            "errors": artist.errors
        }

    def save_progress_report(self, filepath: Optional[str] = None):
        """Save detailed progress report"""
        if not filepath:
            reports_dir = Path(__file__).parent / "reports"
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / f"jazz_harvest_{self.session_id}.json"

        report = {
            "session_info": {
                **self.session_stats,
                "end_time": datetime.utcnow().isoformat()
            },
            "summary": self.get_progress_summary(),
            "artist_details": {
                name: self.get_artist_details(name)
                for name in self.artists.keys()
            }
        }

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"📊 Progress report saved: {filepath}")
        return filepath