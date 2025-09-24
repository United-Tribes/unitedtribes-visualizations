# Content Pipeline Runbook

> **Quick reference for running the complete content scraping and processing pipeline**

## 🚀 Complete Pipeline Execution

### Prerequisites Checklist
- [ ] AWS credentials configured
- [ ] S3 access to `ut-v2-prod-lake-east1` bucket
- [ ] Working directory: `/Users/shanandelp/Documents/unitedtribes/v3-data-lake-and-api`

### Step-by-Step Execution

#### 1. Foundation Protection Setup
```bash
# Create backup before ANY changes
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/pre_content_run_$(date +%Y%m%d_%H%M%S).json

# Record baseline Art Blakey connections
echo "Baseline Art Blakey connections:"
curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count'
```

#### 2. Content Scraping
```bash
cd content_scrapers

# Launch all sources in parallel (recommended)
./harvest --sources pitchfork --max-articles 100 &
./harvest --sources rolling_stone --max-articles 100 &
./harvest --sources billboard --max-articles 100 &
./harvest --sources npr --max-articles 100 &

# Wait for completion
wait

# Or run sequentially if preferred
./harvest --sources pitchfork --max-articles 100
./harvest --sources rolling_stone --max-articles 100
./harvest --sources billboard --max-articles 100
./harvest --sources npr --max-articles 100
```

#### 3. Content Processing
```bash
cd /Users/shanandelp/Documents/unitedtribes/v3-data-lake-and-api

# Process ALL content (videos + books + scraped articles)
python3 scripts/emergency_rebuild_knowledge_graph.py --include-scraped-content
```

#### 4. Narrative Enhancement Deployment
```bash
cd ut_api_v2

# Create minimal Lambda package
zip broker_api_minimal.zip enhanced_query_processor.py lambda_function.py enhanced_handler.py s3_data_service.py config.py models.py cache_service.py

# Deploy to production
aws lambda update-function-code --function-name ut-v2-prod-broker_api --zip-file fileb://broker_api_minimal.zip
```

#### 5. Validation & Testing
```bash
# Test critical artists maintain/improve connections
echo "=== POST-PROCESSING VALIDATION ==="
for artist in "Art Blakey" "Miles Davis" "John Coltrane" "Herbie Hancock"; do
  echo "Testing: $artist"
  count=$(curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"tell me about $artist\", \"domain\": \"music\"}" | \
    jq '.connections.direct_connections[0].connection_count // 0')
  echo "✅ $artist: $count connections"
done

# Test narrative enhancement with music journalism
echo "=== NARRATIVE ENHANCEMENT TEST ==="
curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about John Coltrane", "domain": "music"}' | \
  jq '.narrative' | grep -i "pitchfork\|rolling stone\|billboard\|npr"
```

## 🔧 Individual Component Operations

### Scraper Operations
```bash
cd content_scrapers

# Check scraper status
./harvest --help

# Run specific source only
./harvest --sources pitchfork --max-articles 50

# Run with safety checks disabled (if needed)
./harvest --sources rolling_stone --max-articles 100 --disable-safety-checks

# Check S3 content after scraping
aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive | wc -l
```

### Knowledge Graph Operations
```bash
# Standard rebuild (videos + books only)
python3 scripts/emergency_rebuild_knowledge_graph.py

# Full rebuild including scraped content
python3 scripts/emergency_rebuild_knowledge_graph.py --include-scraped-content

# Check current knowledge graph stats
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json /tmp/current_kg.json
jq '.metadata.total_relationships' /tmp/current_kg.json
```

### Lambda Deployment Operations
```bash
cd ut_api_v2

# Check current Lambda status
aws lambda get-function --function-name ut-v2-prod-broker_api --query 'Configuration.LastModified'

# Create and deploy minimal package
zip broker_api_minimal.zip enhanced_query_processor.py lambda_function.py enhanced_handler.py s3_data_service.py config.py models.py cache_service.py
aws lambda update-function-code --function-name ut-v2-prod-broker_api --zip-file fileb://broker_api_minimal.zip

# Verify deployment
aws lambda get-function --function-name ut-v2-prod-broker_api --query 'Configuration.LastModified'
```

## 🚨 Emergency Procedures

### Immediate Rollback
```bash
# If validation fails, restore from backup
BACKUP_FILE=$(aws s3 ls s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/ | grep pre_content_run | tail -1 | awk '{print $4}')
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/$BACKUP_FILE \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json

# Verify restoration
curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count'
```

### Stop All Background Scrapers
```bash
# Kill all running harvest processes
pkill -f harvest

# Check no scrapers running
ps aux | grep harvest
```

### Health Check All Systems
```bash
# API health
curl -s "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health"

# S3 bucket access
aws s3 ls s3://ut-v2-prod-lake-east1/

# Lambda function status
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ut-v2`)].FunctionName'
```

## 📊 Monitoring Commands

### Content Metrics
```bash
# Count scraped articles by source
echo "Scraped content by source:"
aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive | grep -o 'pitchfork\|rolling_stone\|billboard\|npr' | sort | uniq -c

# Knowledge graph growth
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json /tmp/current_kg.json
echo "Total relationships: $(jq '.metadata.total_relationships' /tmp/current_kg.json)"
echo "Video relationships: $(jq '.metadata.video_relationships' /tmp/current_kg.json)"
echo "Scraped relationships: $(jq '.metadata.scraped_relationships' /tmp/current_kg.json)"
echo "Book relationships: $(jq '.metadata.book_relationships' /tmp/current_kg.json)"
```

### Performance Monitoring
```bash
# API response time test
time curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Miles Davis", "domain": "music"}' > /dev/null

# Lambda function metrics
aws logs filter-log-events --log-group-name /aws/lambda/ut-v2-prod-broker_api \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "Duration"
```

## 🎯 Target Metrics for Success

**Scraping Success:**
- Pitchfork: 90+ articles
- Rolling Stone: 15+ articles
- Billboard: 15+ articles
- NPR: Variable (source dependent)

**Processing Success:**
- Knowledge graph growth: +1,500 relationships minimum
- Foundation protection: Art Blakey ≥ 4 connections
- No processing errors in logs

**Enhancement Success:**
- "Recent Critical Coverage" appears in narratives
- Music journalism citations present
- API response time < 2 seconds

---

**Quick Success Check:**
```bash
# One command to verify everything worked
echo "Art Blakey connections: $(curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" -H "Content-Type: application/json" -d '{"query": "tell me about Art Blakey", "domain": "music"}' | jq '.connections.direct_connections[0].connection_count')"
echo "Total KG relationships: $(aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json - | jq '.metadata.total_relationships')"
```