# 🏗️ RESILIENT STORAGE ARCHITECTURE PROPOSAL
**Date:** December 24, 2024

## 🎯 Goal: Never Lose Content Again

---

## 🔴 CURRENT PROBLEMS

### **Problem 1: Two-Bucket Split Brain**
```
ut-processed-content/     (has books, podcasts)
         ↕️ No sync
ut-v2-prod-lake-east1/    (missing books)
```

### **Problem 2: No Single Source of Truth**
- Books go to one bucket
- Videos go to another  
- Rebuild scripts don't know where to look
- Metadata lies about what's included

### **Problem 3: No Validation**
- No checksums
- No content verification
- No regression tests
- Silent failures

---

## ✅ PROPOSED SOLUTION: Unified Data Lake Architecture

### **1. PRIMARY STORAGE STRUCTURE**
```
s3://ut-v2-prod-lake-east1/
├── raw-content/
│   ├── books/
│   ├── videos/
│   ├── podcasts/
│   └── articles/
├── processed-content/
│   ├── books/
│   ├── videos/
│   ├── podcasts/
│   └── articles/
├── enhanced-knowledge-graph/
│   ├── current/
│   │   └── latest.json
│   ├── daily-snapshots/
│   │   └── 2024-12-24/
│   └── content-specific/
│       ├── books/
│       ├── videos/
│       ├── podcasts/
│       └── articles/
└── manifests/
    ├── content-registry.json
    └── validation-checksums.json
```

### **2. CONTENT REGISTRY MANIFEST**
```json
{
  "books": {
    "just_kids": {
      "status": "active",
      "raw_path": "s3://ut-v2-prod-lake-east1/raw-content/books/just_kids.pdf",
      "processed_path": "s3://ut-v2-prod-lake-east1/processed-content/books/just_kids.json",
      "enhanced_kg_path": "s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/content-specific/books/just_kids.json",
      "relationships_count": 146,
      "last_validated": "2024-12-24T10:00:00Z",
      "checksum": "sha256:abc123..."
    }
  }
}
```

### **3. AUTOMATED VALIDATION PIPELINE**
```python
# Run daily validation
def validate_content_integrity():
    manifest = load_content_registry()
    
    for content_type in ['books', 'videos', 'podcasts', 'articles']:
        for item in manifest[content_type]:
            # Verify file exists
            # Check relationship count
            # Validate checksum
            # Log any discrepancies
            
    # Alert if any content missing
```

### **4. REBUILD SCRIPT IMPROVEMENTS**
```python
def rebuild_knowledge_graph():
    # ALWAYS check manifest first
    manifest = load_content_registry()
    
    # Gather from ALL registered sources
    all_content = []
    for content_type in manifest:
        for item in manifest[content_type]:
            if item['status'] == 'active':
                all_content.append(item['enhanced_kg_path'])
    
    # Build with validation
    new_kg = aggregate_content(all_content)
    
    # Verify counts match
    assert new_kg.book_count == manifest.book_count
    assert new_kg.total_relationships >= manifest.minimum_relationships
    
    # Only deploy if validation passes
```

---

## 🛡️ PROTECTION MECHANISMS

### **1. Pre-Rebuild Checklist**
```bash
#!/bin/bash
# pre-rebuild-validation.sh

echo "=== PRE-REBUILD VALIDATION ==="

# 1. Check content registry
BOOK_COUNT=$(aws s3 cp s3://ut-v2-prod-lake-east1/manifests/content-registry.json - | jq '.books | length')
echo "Books in registry: $BOOK_COUNT"

# 2. Verify all content accessible
for content_type in books videos podcasts articles; do
  aws s3 ls s3://ut-v2-prod-lake-east1/processed-content/$content_type/ --recursive | wc -l
done

# 3. Backup current KG
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/pre-rebuild-$(date +%Y%m%d-%H%M%S).json

# 4. Only proceed if validation passes
if [ $BOOK_COUNT -lt 16 ]; then
  echo "ERROR: Missing books! Expected 16, found $BOOK_COUNT"
  exit 1
fi
```

### **2. Post-Rebuild Validation**
```bash
# post-rebuild-validation.sh

# 1. Check relationship counts
NEW_BOOK_RELS=$(aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json - | \
  jq '.metadata.book_relationships')

if [ $NEW_BOOK_RELS -lt 2000 ]; then
  echo "ERROR: Book relationships too low: $NEW_BOOK_RELS"
  # Rollback
  aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/backups/latest-backup.json \
    s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/latest.json
  exit 1
fi
```

### **3. Monitoring & Alerts**
```python
# CloudWatch alarm for content loss
def check_content_health():
    kg = load_current_kg()
    metrics = {
        'book_relationships': kg.metadata.book_relationships,
        'video_relationships': kg.metadata.video_relationships,
        'total_relationships': kg.metadata.total_relationships
    }
    
    # Alert if any metric drops by >10%
    for metric, value in metrics.items():
        if value < BASELINE[metric] * 0.9:
            send_alert(f"Content loss detected: {metric} dropped to {value}")
```

---

## 📋 IMMEDIATE ACTIONS BEFORE RESTORATION

### **Step 1: Create Content Registry**
```bash
# Generate registry from existing content
aws s3 ls s3://ut-processed-content/enhanced-knowledge-graph/ --recursive | \
  grep "book_" > /tmp/book_inventory.txt

# Create manifest
python3 create_content_registry.py
```

### **Step 2: Set Up Backup Structure**
```bash
# Create organized backup structure
aws s3api put-object --bucket ut-v2-prod-lake-east1 \
  --key enhanced-knowledge-graph/content-specific/books/

aws s3api put-object --bucket ut-v2-prod-lake-east1 \
  --key manifests/
```

### **Step 3: Implement Validation Scripts**
- Pre-rebuild validation
- Post-rebuild validation
- Daily integrity checks
- Content registry updates

---

## 🚀 BENEFITS

1. **Single Source of Truth**: Everything in ut-v2-prod-lake-east1
2. **Content Registry**: Always know what should be there
3. **Validation**: Catch problems before deployment
4. **Rollback**: Automatic recovery from bad rebuilds
5. **Monitoring**: Real-time alerts for content loss
6. **Audit Trail**: Complete history of all changes

---

## ⚠️ CRITICAL SUCCESS FACTORS

1. **NEVER rebuild without the manifest**
2. **ALWAYS validate before and after**
3. **MAINTAIN checksums for all content**
4. **AUTOMATE rollback on validation failure**
5. **MONITOR relationship counts continuously**

This architecture ensures that even if someone accidentally deletes content or runs a bad rebuild, we can:
- Detect it immediately
- Know exactly what's missing
- Restore from backups automatically
- Prevent deployment of corrupted KGs
