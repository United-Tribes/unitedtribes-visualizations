# API Integration Guide

> **How to integrate the content pipeline with knowledge graph APIs and narrative generation systems**

## 🎯 Integration Overview

The content pipeline produces enhanced knowledge graphs that integrate with API systems to provide enriched narrative responses with music journalism citations.

## 📊 Output Format

### Knowledge Graph Structure

The pipeline outputs enhanced knowledge graphs in this format:

```json
{
  "relationships": [
    {
      "source_entity": "John Coltrane",
      "target_entity": "Pitchfork Article: The Essential Guide to John Coltrane...",
      "relationship_type": "featured_in",
      "confidence": 0.9,
      "evidence": "Featured in Pitchfork article: The Essential Guide to John Coltrane",
      "source_attribution": {
        "source": "pitchfork",
        "title": "The Essential Guide to John Coltrane",
        "url": "https://pitchfork.com/...",
        "author": "Music Writer",
        "publication_date": "2024-01-15",
        "processing_method": "scraped_content_extraction"
      },
      "metadata": {
        "content_type": "article",
        "themes": ["music", "journalism"],
        "enhancement_date": "2025-09-19T17:30:00",
        "source_file": "scraped-content/john_coltrane/thematic/pitchfork_...",
        "artist_mention_count": 15
      }
    }
  ],
  "metadata": {
    "total_relationships": 7278,
    "video_relationships": 785,
    "scraped_relationships": 1282,
    "book_relationships": 4426,
    "rebuild_timestamp": "2025-09-19T17:30:00",
    "scraped_content_included": true
  }
}
```

### Relationship Types Generated

**`featured_in`**: Artist featured in specific article
```json
{
  "source_entity": "Art Blakey",
  "target_entity": "Rolling Stone Article: Jazz Legends...",
  "relationship_type": "featured_in"
}
```

**`mentioned_with`**: Artists appearing in same content
```json
{
  "source_entity": "Art Blakey",
  "target_entity": "Miles Davis",
  "relationship_type": "mentioned_with",
  "evidence": "Both mentioned in Rolling Stone article: Jazz Legends of the 1960s"
}
```

## 🔗 API Enhancement Integration

### Narrative Generation Enhancement

**Enhanced Relationship Scoring** (`enhanced_query_processor.py`):

```python
def _score_relationship_relevance(self, relationship: Dict, search_terms: List[str], intent: CreativeQueryIntent) -> float:
    # Base scoring...
    score = 0.0

    # Article relationship boost - prioritize recent music journalism
    source_attr = relationship.get('source_attribution', {})
    if source_attr:
        source_name = source_attr.get('source', '').lower()
        processing_method = source_attr.get('processing_method', '').lower()

        # 50% boost for music publication sources
        if any(pub in source_name for pub in ['pitchfork', 'rolling stone', 'billboard', 'npr']):
            score *= 1.5

        # Additional boost for featured_in relationships (direct artist coverage)
        if rel_type == 'featured_in' and 'scraped_content' in processing_method:
            score *= 1.3

    return score
```

**Enhanced Narrative Prompts**:

```python
narrative_prompt = f"""
You are a knowledgeable information specialist helping users explore connections between artists.

## Guidelines:
4. **Prioritize Recent Coverage**: When available, highlight insights from music journalism
   (Pitchfork, Rolling Stone, Billboard, NPR) alongside historical sources

### Content Categories to Cover:
#### 5. Recent Critical Coverage
- Music journalism and reviews from Pitchfork, Rolling Stone, Billboard, NPR
- Contemporary perspectives and retrospective analysis
- Current cultural relevance and ongoing influence

Based on these relationships, provide comprehensive analysis. When citing music journalism
sources (Pitchfork, Rolling Stone, Billboard, NPR), highlight these as current perspectives
on the artist's legacy and influence.
"""
```

## 🚀 Deployment Integration

### Lambda Function Updates

**Minimal Package Deployment**:
```bash
cd ut_api_v2
zip broker_api_minimal.zip \
  enhanced_query_processor.py \
  lambda_function.py \
  enhanced_handler.py \
  s3_data_service.py \
  config.py \
  models.py \
  cache_service.py

aws lambda update-function-code \
  --function-name ut-v2-prod-broker_api \
  --zip-file fileb://broker_api_minimal.zip
```

**Required Environment Variables**:
```bash
S3_PROCESSED_BUCKET=ut-v2-prod-lake-east1
BEDROCK_TEXT_MODEL=anthropic.claude-3-haiku-20240307-v1:0
```

### Knowledge Graph Integration

**S3 Knowledge Graph Location**:
```
s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json
```

**API Loading Pattern**:
```python
def _get_knowledge_graph(self) -> Dict[str, Any]:
    """Get knowledge graph with caching"""
    if self._knowledge_graph is None or self._should_refresh_cache():
        response = self.s3.get_object(Bucket=self.bucket_name, Key=self.kg_key)
        self._knowledge_graph = json.loads(response['Body'].read().decode('utf-8'))
        logger.info(f"Loaded knowledge graph with {len(self._knowledge_graph.get('relationships', []))} relationships")
    return self._knowledge_graph
```

## 📋 Integration Checklist

### Pre-Integration Validation

- [ ] **Foundation Protection**: Verify Art Blakey maintains 4+ connections
- [ ] **Knowledge Graph Size**: Confirm total relationships increased
- [ ] **Content Quality**: Validate scraped relationships present
- [ ] **API Health**: Test API response time <2 seconds

### Integration Steps

1. **Deploy Enhanced Processor**:
   ```bash
   # Update Lambda with enhanced narrative generation
   ./deploy_enhanced_api.sh
   ```

2. **Validate Enhancement**:
   ```bash
   # Test narrative enhancement active
   curl -s -X POST "https://api-endpoint/prod/v2/broker" \
     -H "Content-Type: application/json" \
     -d '{"query": "tell me about John Coltrane", "domain": "music"}' | \
     jq '.narrative' | grep -i "pitchfork\|rolling stone\|billboard"
   ```

3. **Monitor Performance**:
   ```bash
   # Check API response times maintained
   time curl -s "https://api-endpoint/prod/health"
   ```

### Post-Integration Validation

- [ ] **Narrative Enhancement**: Music journalism citations appear
- [ ] **Source Attribution**: Publication names and URLs present
- [ ] **Performance**: API response time maintained
- [ ] **Foundation**: Critical artist connections preserved

## 🎯 Expected API Enhancements

### Narrative Response Changes

**Before Integration**:
```
Art Blakey was a renowned American jazz drummer and bandleader...
[Generic content from books and videos only]
```

**After Integration**:
```
Art Blakey was a renowned American jazz drummer and bandleader...

Recent Critical Coverage:
In a 2018 profile, Pitchfork described Blakey as "a towering figure in 20th-century music,
a drummer whose influence on jazz, R&B, and beyond is incalculable." [Source: Pitchfork]
Rolling Stone noted that Blakey's "fierce, propulsive playing...helped define the sound
of modern jazz drumming." [Source: Rolling Stone]
```

### Enhanced Query Results

**Artist Queries Now Include**:
- Contemporary critical perspectives
- Recent retrospective analysis
- Music journalism citations
- Publication-specific insights
- Current cultural relevance discussions

**Cross-Reference Improvements**:
- Articles mentioning multiple artists create rich connections
- Music publication perspectives complement academic sources
- Contemporary analysis enhances historical context

## 🔧 Troubleshooting Integration

### Common Issues

**Issue**: "No music journalism citations in narratives"
```bash
# Check if enhanced processor deployed
aws lambda get-function --function-name ut-v2-prod-broker_api --query 'Configuration.LastModified'

# Verify relationships exist in knowledge graph
aws s3 cp s3://bucket/enhanced-knowledge-graph/current/latest.json - | \
  jq '.relationships[] | select(.source_attribution.source | contains("pitchfork"))' | head -1
```

**Issue**: "API response time increased"
```bash
# Monitor performance after enhancement
time curl -s -X POST "https://api-endpoint/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Miles Davis", "domain": "music"}' > /dev/null

# Check Lambda function logs
aws logs filter-log-events --log-group-name /aws/lambda/ut-v2-prod-broker_api \
  --filter-pattern "Duration" | jq '.events[].message'
```

**Issue**: "Foundation protection violated"
```bash
# Immediate rollback
BACKUP=$(aws s3 ls s3://bucket/enhanced-knowledge-graph/backups/ | tail -1 | awk '{print $4}')
aws s3 cp s3://bucket/enhanced-knowledge-graph/backups/$BACKUP \
  s3://bucket/enhanced-knowledge-graph/current/latest.json

# Verify restoration
curl -s -X POST "https://api-endpoint/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count'
```

## 📊 Monitoring & Metrics

### Key Performance Indicators

**Response Quality**:
- Music journalism citation count per narrative
- Source diversity in responses
- Contemporary perspective inclusion rate

**System Performance**:
- API response time (target: <2 seconds)
- Knowledge graph load time
- Relationship scoring performance

**Content Integration**:
- Total relationships in knowledge graph
- Scraped content relationship count
- Cross-reference generation success rate

### Monitoring Commands

```bash
# Complete system validation
./scripts/validate.sh

# Performance monitoring
time curl -s "https://api-endpoint/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about John Coltrane", "domain": "music"}' | \
  jq '.narrative' | wc -c

# Content coverage analysis
aws s3 cp s3://bucket/enhanced-knowledge-graph/current/latest.json - | \
  jq '.metadata.scraped_relationships'
```

---

**Integration Philosophy**: Enhance without breaking, enrich without compromising, innovate while protecting the foundation.