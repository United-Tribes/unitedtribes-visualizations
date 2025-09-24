#!/bin/bash

echo "=== CONTENT PIPELINE VALIDATION ==="

# 1. Foundation Protection
echo "Checking foundation protection..."
ART_BLAKEY_COUNT=$(curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count')

if [ "$ART_BLAKEY_COUNT" -ge 4 ]; then
  echo "✅ Foundation Protected: Art Blakey has $ART_BLAKEY_COUNT connections"
else
  echo "❌ FOUNDATION BREACH: Art Blakey has only $ART_BLAKEY_COUNT connections"
  exit 1
fi

# 2. Content Integration
echo "Checking knowledge graph size..."
TOTAL_RELATIONSHIPS=$(aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json - | jq '.metadata.total_relationships')
SCRAPED_RELATIONSHIPS=$(aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json - | jq '.metadata.scraped_relationships // 0')
echo "✅ Total relationships: $TOTAL_RELATIONSHIPS"
echo "✅ Scraped relationships: $SCRAPED_RELATIONSHIPS"

# 3. Narrative Enhancement
echo "Testing narrative enhancement..."
NARRATIVE_TEST=$(curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about John Coltrane", "domain": "music"}' | \
  jq '.narrative' | grep -i "pitchfork\|rolling stone\|billboard\|recent critical coverage" | wc -l)

if [ "$NARRATIVE_TEST" -gt 0 ]; then
  echo "✅ Narrative Enhancement: Music journalism citations present"
else
  echo "⚠️  Narrative Enhancement: No music journalism citations found"
fi

# 4. API Performance
echo "Testing API performance..."
API_START=$(date +%s%N)
curl -s "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health" > /dev/null
API_END=$(date +%s%N)
API_TIME=$(((API_END - API_START) / 1000000))

if [ "$API_TIME" -lt 2000 ]; then
  echo "✅ API Performance: ${API_TIME}ms response time"
else
  echo "⚠️  API Performance: ${API_TIME}ms response time (>2s)"
fi

# 5. Critical Artists Test
echo "Testing critical artists..."
for artist in "Miles Davis" "Herbie Hancock"; do
  count=$(curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"tell me about $artist\", \"domain\": \"music\"}" | \
    jq '.connections.direct_connections[0].connection_count // 0')
  echo "✅ $artist: $count connections"
done

# 6. Content Coverage
echo "Checking scraped content coverage..."
SCRAPED_COUNT=$(aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive | wc -l)
echo "✅ Scraped articles in S3: $SCRAPED_COUNT"

echo "=== VALIDATION COMPLETE ==="
echo ""
echo "Summary:"
echo "- Foundation: Protected (Art Blakey: $ART_BLAKEY_COUNT connections)"
echo "- Knowledge Graph: $TOTAL_RELATIONSHIPS total relationships ($SCRAPED_RELATIONSHIPS from articles)"
echo "- Narrative Enhancement: $([ "$NARRATIVE_TEST" -gt 0 ] && echo "Active" || echo "Inactive")"
echo "- API Performance: ${API_TIME}ms"
echo "- Content Coverage: $SCRAPED_COUNT articles"