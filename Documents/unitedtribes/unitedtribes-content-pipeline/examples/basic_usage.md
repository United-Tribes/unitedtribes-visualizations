# Basic Usage Examples

> **Quick examples to get started with the United Tribes Content Pipeline**

## 🚀 Getting Started

### 1. Basic Content Scraping

**Scrape from a single source:**
```bash
cd src
./harvest --sources pitchfork --max-articles 20
```

**Scrape from multiple sources:**
```bash
./harvest --sources pitchfork,rolling_stone --max-articles 50
```

**Scrape all supported sources:**
```bash
./harvest --sources pitchfork,rolling_stone,billboard,npr --max-articles 100
```

### 2. Knowledge Graph Building

**Basic rebuild (videos + books only):**
```bash
python3 knowledge_graph_builder.py
```

**Full rebuild including scraped content:**
```bash
python3 knowledge_graph_builder.py --include-scraped-content
```

### 3. System Validation

**Complete health check:**
```bash
./scripts/validate.sh
```

**Quick foundation check:**
```bash
curl -s -X POST "https://api-endpoint/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
  jq '.connections.direct_connections[0].connection_count'
```

## 📋 Common Workflows

### Daily Content Harvest

**Setup as cronjob:**
```bash
# Edit crontab
crontab -e

# Add daily harvest at 2 AM
0 2 * * * cd /path/to/unitedtribes-content-pipeline/src && ./harvest --sources pitchfork,rolling_stone,billboard,npr --max-articles 50 >> /var/log/content-harvest.log 2>&1
```

### Weekly Knowledge Graph Rebuild

**Setup weekly processing:**
```bash
# Add to crontab for Sunday 3 AM
0 3 * * 0 cd /path/to/unitedtribes-content-pipeline && python3 src/knowledge_graph_builder.py --include-scraped-content >> /var/log/kg-rebuild.log 2>&1
```

### Emergency Procedures

**If something goes wrong:**
```bash
# Stop all running harvests
pkill -f harvest

# Check system health
./scripts/validate.sh

# If foundation compromised, rollback immediately
BACKUP=$(aws s3 ls s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/ | tail -1 | awk '{print $4}')
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/$BACKUP \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json
```

## 🎯 Targeting Specific Artists

### Single Artist Focus

**Scrape content for specific artist:**
```bash
# This will find articles mentioning John Coltrane across all sources
./harvest --sources pitchfork,rolling_stone,billboard,npr --max-articles 100
# The scraper automatically searches for target artists including John Coltrane
```

**Check results for specific artist:**
```bash
aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/john_coltrane/ --recursive
```

### Monitor Artist Coverage

**Check which artists are being found:**
```bash
# After knowledge graph rebuild
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json /tmp/kg.json
jq '.relationships[] | select(.relationship_type == "featured_in") | .source_entity' /tmp/kg.json | sort | uniq -c | sort -nr
```

## 🔍 Monitoring & Debugging

### Check Scraper Progress

**Monitor running harvest:**
```bash
# Check process status
ps aux | grep harvest

# Monitor logs (if logging to file)
tail -f /var/log/content-harvest.log
```

### Validate Content Quality

**Check recently scraped content:**
```bash
# List recent uploads
aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive | tail -10

# Examine content structure
aws s3 cp s3://ut-v2-prod-lake-east1/scraped-content/john_coltrane/thematic/pitchfork_20250919_abc123_sample.json /tmp/sample.json
jq '.' /tmp/sample.json | head -20
```

### Test API Enhancement

**Verify music journalism citations:**
```bash
curl -s -X POST "https://api-endpoint/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about John Coltrane", "domain": "music"}' | \
  jq '.narrative' | grep -C 2 -i "pitchfork\|rolling stone\|billboard"
```

## ⚠️ Safety Best Practices

### Always Backup First

**Before any major operation:**
```bash
# Create backup
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/manual_backup_$(date +%Y%m%d_%H%M%S).json

# Record baseline
echo "Baseline Art Blakey connections: $(curl -s -X POST "https://api-endpoint/prod/v2/broker" -H "Content-Type: application/json" -d '{"query": "tell me about Art Blakey", "domain": "music"}' | jq '.connections.direct_connections[0].connection_count')"
```

### Incremental Testing

**Start small and scale up:**
```bash
# Test with small batch first
./harvest --sources pitchfork --max-articles 5

# Validate results
./scripts/validate.sh

# If successful, scale up
./harvest --sources pitchfork --max-articles 50
```

### Monitor Resource Usage

**Check system resources during harvest:**
```bash
# Monitor while running
watch 'ps aux | grep harvest; echo "---"; free -h; echo "---"; df -h'
```

## 🎯 Success Indicators

### What Success Looks Like

**After content harvest:**
```bash
# Should see new files in S3
aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive | wc -l
# Number should increase after each harvest

# Should see content from multiple sources
aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive | grep -o 'pitchfork\|rolling_stone\|billboard\|npr' | sort | uniq -c
```

**After knowledge graph rebuild:**
```bash
# Should see relationship count increase
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json - | jq '.metadata.total_relationships'
# Should be > 7,278 (current baseline)

# Should see scraped relationships
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json - | jq '.metadata.scraped_relationships'
# Should be > 0
```

**After API enhancement:**
```bash
# Should see music journalism in narratives
curl -s -X POST "https://api-endpoint/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "tell me about Miles Davis", "domain": "music"}' | \
  jq '.narrative' | grep -i "recent critical coverage\|pitchfork\|rolling stone" | wc -l
# Should be > 0
```

---

**Remember**: Always validate with `./scripts/validate.sh` after any major operation!