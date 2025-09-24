# Content Pipeline Architecture

> **Technical implementation details for the United Tribes content scraping and processing system**

## 🏗️ System Overview

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────┐
│ Music           │    │ Content          │    │ Knowledge       │    │ Enhanced     │
│ Publications    │───▶│ Scrapers         │───▶│ Graph Builder   │───▶│ Narratives   │
│                 │    │                  │    │                 │    │              │
│ • Pitchfork     │    │ • harvest CLI    │    │ • Relationship  │    │ • API        │
│ • Rolling Stone │    │ • Direct Search  │    │   Extraction    │    │   Integration│
│ • Billboard     │    │ • Artist         │    │ • Foundation    │    │ • Citation   │
│ • NPR           │    │   Targeting      │    │   Protection    │    │   Enhancement│
└─────────────────┘    └──────────────────┘    └─────────────────┘    └──────────────┘
         │                        │                        │                     │
         ▼                        ▼                        ▼                     ▼
   [Web Scraping]         [Content Processing]      [Graph Integration]    [User Experience]
```

## 📦 Component Architecture

### 1. Content Scrapers (`src/`)

**Core Components:**
```
src/
├── harvest                          # Main CLI tool
├── articles/
│   ├── base_scraper.py             # Core scraping logic
│   ├── direct_search_fallback.py   # EnhancedFetcher bypass
│   ├── pitchfork_scraper.py        # Pitchfork-specific logic
│   ├── rolling_stone_scraper.py    # Rolling Stone-specific logic
│   ├── billboard_scraper.py        # Billboard-specific logic
│   └── npr_scraper.py              # NPR-specific logic
├── shared/
│   ├── validator.py                # Content validation
│   ├── s3_uploader.py              # AWS S3 integration
│   └── extractor.py                # Content extraction
└── podcasts/                       # Future expansion
```

**Key Patterns:**
- **Artist Targeting**: Searches specifically for 25 target jazz artists
- **Direct Search Fallback**: Bypasses EnhancedFetcher regressions with direct HTTP
- **Content Validation**: Ensures data quality before upload
- **Batch Processing**: Handles large content volumes efficiently

### 2. Knowledge Graph Builder (`src/knowledge_graph_builder.py`)

**Core Functions:**
```python
class KnowledgeGraphBuilder:
    def list_all_scraped_files() -> List[str]:
        """Discover all scraped content for processing"""

    def extract_relationships_from_scraped_content(scraped_key: str) -> List[Dict]:
        """Convert articles into structured relationships"""

    def rebuild_enhanced_knowledge_graph(include_scraped_content: bool):
        """Atomic update of complete knowledge graph"""
```

**Relationship Types:**
- **`featured_in`**: Artist featured in specific article
- **`mentioned_with`**: Artists appearing in same content
- **Cross-references**: Same artist across multiple sources

**Foundation Protection:**
- Automatic backup creation before changes
- Relationship count validation (must increase)
- Critical artist connection preservation
- Atomic operations with rollback capability

### 3. Enhancement Scripts (`scripts/`)

**Validation System:**
```bash
scripts/validate.sh
├── Foundation Protection Check
├── Knowledge Graph Size Validation
├── Narrative Enhancement Verification
├── API Performance Testing
└── Content Coverage Analysis
```

**Emergency Procedures:**
```bash
scripts/emergency_rollback.sh
├── Immediate backup restoration
├── Foundation integrity verification
└── System health confirmation
```

## 🔄 Data Flow

### Content Processing Pipeline

```
1. Content Discovery
   ├── Search music publications for target artists
   ├── Extract article URLs using direct HTTP fallback
   └── Validate content format and quality

2. Content Extraction
   ├── Download full article content
   ├── Extract metadata (title, author, date, source)
   └── Structure content in standard v3 format

3. Relationship Generation
   ├── Detect target jazz artists in content
   ├── Create "featured_in" relationships (artist → article)
   ├── Generate "mentioned_with" cross-references
   └── Add source attribution and confidence scores

4. Knowledge Graph Integration
   ├── Load existing relationships (videos + books)
   ├── Merge new article relationships
   ├── Validate foundation integrity maintained
   └── Deploy atomically with backup creation
```

### S3 Storage Structure

```
s3://ut-v2-prod-lake-east1/
├── scraped-content/
│   ├── {artist}/
│   │   └── thematic/
│   │       └── {source}_{timestamp}_{hash}_{title}.json
│   └── various{source}/
│       └── {type}/
│           └── {source}_{timestamp}_*.json
├── enhanced-knowledge-graph/
│   ├── current/
│   │   └── latest.json                    # 7,278+ relationships
│   └── backups/
│       └── pre_*_{timestamp}.json         # Automatic backups
└── video_analysis/                        # Existing content
    └── {artist}/
        └── video_*.json
```

## 🛡️ Foundation Protection Architecture

### Protection Mechanisms

```python
class FoundationGuardian:
    def capture_baseline() -> FoundationBaseline:
        """Record current state before changes"""

    def validate_preservation(baseline) -> bool:
        """Ensure foundation integrity maintained"""

    def emergency_rollback(baseline):
        """Immediate restoration to baseline state"""
```

**Critical Validation Points:**
1. **Pre-Flight**: Capture baseline metrics
2. **Processing**: Monitor relationship counts
3. **Post-Integration**: Validate foundation preserved
4. **Emergency**: Immediate rollback if validation fails

**Protected Metrics:**
- Art Blakey connections: ≥4 (baseline)
- Total relationships: Always increasing
- API response time: <2 seconds
- Critical artist connectivity: Maintained

## 🚀 Deployment Architecture

### Local Execution Environment

**Operational Context:**
- **Local cronjobs**: Scheduled content harvesting
- **Batch processing**: Large content volumes
- **AWS integration**: S3 storage and Lambda deployment
- **Foundation protection**: Never compromise existing data

**Integration Points:**
```
Content Pipeline → AWS S3 → Lambda Functions → Production API
       ↓              ↓            ↓              ↓
  [Local Execution] [Storage]  [Processing]  [User Facing]
  [Cronjob Context] [Reliable] [Real-time]   [Query Response]
```

### Narrative Enhancement Integration

**API Enhancement Flow:**
```python
# In ut_api_v2/enhanced_query_processor.py
def _score_relationship_relevance():
    # 50% boost for music journalism sources
    if any(pub in source_name for pub in ['pitchfork', 'rolling stone', 'billboard', 'npr']):
        score *= 1.5

    # Additional boost for featured_in relationships
    if rel_type == 'featured_in' and 'scraped_content' in processing_method:
        score *= 1.3
```

**Narrative Prompt Enhancement:**
- Added "Recent Critical Coverage" section
- Music journalism prioritization
- Contemporary perspective integration
- Publication attribution in citations

## 📊 Performance Characteristics

### Processing Performance

**Content Scraping:**
- Pitchfork: 96 articles in ~5 minutes
- Rolling Stone: 18 articles in ~2 minutes
- Billboard: 15 articles in ~2 minutes
- NPR: Variable (source dependent)

**Knowledge Graph Processing:**
- 326 articles → 1,282 relationships in ~4 minutes
- Complete rebuild (videos + articles + books): ~7 minutes
- S3 upload: <30 seconds for enhanced knowledge graph

**Quality Metrics:**
- Artist detection accuracy: >95%
- Relationship confidence scores: 0.8-0.9
- Source attribution completeness: 100%
- Foundation protection success: 100%

### Scalability Considerations

**Current Limits:**
- Content volume: Designed for hundreds of articles per run
- Artist targeting: 25 jazz artists (expandable)
- Source diversity: 4 major publications (expandable)
- Processing time: Linear scaling with content volume

**Optimization Opportunities:**
- Parallel processing for multiple sources
- Incremental updates vs full rebuilds
- Content deduplication across sources
- Enhanced caching for repeated operations

## 🔧 Technical Decisions

### Key Architectural Choices

**1. Direct HTTP over EnhancedFetcher**
- **Decision**: Implement direct search fallback
- **Rationale**: EnhancedFetcher regression blocking search functionality
- **Implementation**: `articles/direct_search_fallback.py`

**2. Separate Repository Structure**
- **Decision**: Extract from data lake monolith
- **Rationale**: Different operational contexts (cronjobs vs real-time API)
- **Benefits**: Clear separation of concerns, independent deployment

**3. Foundation Protection First**
- **Decision**: Comprehensive validation before any changes
- **Rationale**: Data integrity more important than feature velocity
- **Implementation**: Automatic backup, validation, rollback procedures

**4. Music Journalism Integration**
- **Decision**: Enhanced scoring and narrative prompts
- **Rationale**: Contemporary perspectives add user value
- **Implementation**: 50% scoring boost, dedicated narrative sections

### Design Patterns

**Atomic Operations:**
- All-or-nothing knowledge graph updates
- Automatic backup creation before changes
- Comprehensive validation before deployment

**Extensible Architecture:**
- Source-specific scrapers with common interfaces
- Pluggable content validation and processing
- Modular relationship extraction patterns

**Foundation Protection:**
- Never compromise existing data integrity
- Comprehensive pre-flight and post-flight validation
- Immediate rollback capability for any failures

---

**Design Philosophy**: Stability over features, data integrity over convenience, comprehensive documentation over clever code.