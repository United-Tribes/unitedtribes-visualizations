# Safe Content Integration Plan

> **Critical Mission**: Flow 129+ scraped articles into production data lake WITHOUT destabilizing the existing knowledge graph (4,426 relationships) or API.

## 🛡️ Current Production State (Baseline)

**Data Lake Foundation**:
- Art Blakey connections: **4** (baseline)
- Knowledge graph: `enhanced-knowledge-graph/current/latest.json` (Sept 17, 7.8MB)
- S3 structure: Working and stable

**Scraped Content Ready**:
- ✅ **129+ articles** in `s3://ut-v2-prod-lake-east1/scraped-content/`
- ✅ **Proper v3 format**: All validation passed
- ✅ **Well-structured**: Artist/thematic categorization working
- ✅ **Quality content**: Jazz artist mentions detected

## 🎯 Integration Strategy: Staged & Reversible

### Phase 1: Content Processing Enhancement (SAFE)

**Goal**: Create a content processor that can handle scraped articles WITHOUT breaking existing video processing.

**Approach**: Extend `emergency_rebuild_knowledge_graph.py` to include scraped content:

```python
# NEW FUNCTION: Process scraped content alongside video content
def extract_relationships_from_scraped_content(self, scraped_key: str) -> List[Dict[str, Any]]:
    """Extract relationships from scraped articles (same format as video processing)"""

def list_all_scraped_files(self) -> List[str]:
    """List scraped content files for processing"""

def rebuild_enhanced_knowledge_graph_with_content(self):
    """SAFE: Rebuild KG including both video AND scraped content"""
```

**Why Safe**:
- Uses existing, proven architecture
- Same relationship extraction patterns as video content
- Maintains backward compatibility
- Can be rolled back instantly

### Phase 2: Test Integration (DRY RUN)

**Commands**:
```bash
# 1. Backup current state
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/pre_scraped_content_$(date +%Y%m%d_%H%M%S).json

# 2. Test rebuild with scraped content (LOCAL ONLY)
cd /Users/shanandelp/Documents/unitedtribes/v3-data-lake-and-api
python3 scripts/emergency_rebuild_knowledge_graph.py --include-scraped-content --dry-run --output /tmp/test_kg_with_scraped.json

# 3. Validate test results
jq '.metadata.total_relationships' /tmp/test_kg_with_scraped.json
# Should be > 4,426 (current baseline)

# 4. Test API compatibility
curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count'
# Should remain 4+ (not decreased)
```

### Phase 3: Production Integration (CONTROLLED)

**Only proceed if Phase 2 succeeds completely**

```bash
# 1. Deploy enhanced knowledge graph with scraped content
python3 scripts/emergency_rebuild_knowledge_graph.py --include-scraped-content --deploy

# 2. Immediate validation
curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count'

# 3. Test multiple critical artists
for artist in "Art Blakey" "Miles Davis" "John Coltrane" "Herbie Hancock"; do
  echo "Testing: $artist"
  count=$(curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"tell me about $artist\", \"domain\": \"music\"}" | \
    jq '.connections.direct_connections[0].connection_count // 0')
  if [ "$count" -lt 4 ]; then
    echo "❌ CRITICAL: $artist has only $count connections - ROLLBACK REQUIRED"
    # Immediate rollback procedure
  fi
  echo "✅ $artist: $count connections"
done
```

## 🔄 Emergency Rollback Plan

**If ANY validation fails**:

```bash
# 1. Immediate restore from backup
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/pre_scraped_content_*.json \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json

# 2. Verify restoration
curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count'
# Should return to baseline (4)
```

## 🎯 Expected Enhancements (After Integration)

**New Relationships from Scraped Content**:
- **John Coltrane**: +96 Pitchfork articles mentioning him
- **Art Blakey**: +18 Rolling Stone + 15 Billboard articles
- **Cross-references**: Articles mentioning multiple jazz artists
- **Album reviews**: Direct artist-album relationships
- **Interview content**: Artist-interview relationships

**Relationship Growth Estimate**:
- Current: 4,426 relationships
- Expected after integration: **5,000-6,000 relationships**
- New sources: Pitchfork, Rolling Stone, Billboard content

## 🛡️ Safety Guardrails

### 1. **NO Direct Modification of Production Data**
- All changes go through established `emergency_rebuild_knowledge_graph.py`
- No manual editing of S3 files
- No experimental processing directly on production

### 2. **Mandatory Validation Steps**
- ✅ Backup before any change
- ✅ Test locally before production
- ✅ Validate all critical artists maintain connections
- ✅ Confirm total relationships increase (not decrease)
- ✅ Test API response quality

### 3. **Immediate Rollback Capability**
- Backup stored before integration
- Single command restores previous state
- No dependency on new code for rollback

### 4. **Incremental Approach**
- Start with small subset of articles for testing
- Validate each step before proceeding
- Never process all 129+ articles at once initially

## 📋 Implementation Checklist

- [ ] **Extend emergency_rebuild_knowledge_graph.py** with scraped content processing
- [ ] **Create backup** of current knowledge graph
- [ ] **Test integration locally** with dry run
- [ ] **Validate test results** (relationships, API responses)
- [ ] **Deploy to production** only if all tests pass
- [ ] **Validate production state** immediately after deployment
- [ ] **Monitor for 24 hours** to ensure stability

## 🎯 Success Criteria

**✅ Foundation Preserved**:
- Art Blakey: 4+ connections (maintained)
- All critical artists: No reduction in connections
- API response time: <2 seconds (maintained)
- Total relationships: Increased from 4,426

**✅ Content Successfully Integrated**:
- Scraped articles appearing in relevant artist queries
- New relationships reflecting Pitchfork/Rolling Stone/Billboard content
- Cross-references between articles and existing video content
- Proper attribution to source publications

**✅ System Stability**:
- No API errors or timeouts
- Knowledge graph loading properly
- S3 structure maintained
- Lambda functions responding normally

---

**Next Action**: Extend `emergency_rebuild_knowledge_graph.py` to safely include scraped content processing.