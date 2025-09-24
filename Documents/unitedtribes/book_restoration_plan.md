# 📚 BOOK CONTENT RESTORATION PLAN
**Date:** September 24, 2025

## 🔴 CRITICAL ISSUE
**16 fully processed books are missing from production knowledge graph**

---

## 📖 Complete Book Inventory

### **Books Successfully Processed (16 total):**

1. **"Just Kids"** - Patti Smith
   - Processed: Sept 2 & Sept 9, 2025
   - 146 relationships extracted

2. **"The Cover Art of Blue Note Records: The Collection"** *(correct title)*
   - Processed: Sept 11, 2025
   - File: `book_blue_note_records_album_cover_art_ultimate_collection.json`

3. **"Amy Winehouse: In Her Own Words"** - Amy Winehouse

4. **"Where's My Guitar?"** - Bernie Marsden

5. **"Strange Fruit - Billie Holiday and the Biography of a Song"** - Billie Holiday

6. **"Kansas City Lightning - The Rise and Times of Charlie Parker"** - Charlie Parker

7. **"Dylan Goes Electric!"** - Elijah Wald

8. **"The John Coltrane Reference"** - John Coltrane

9. **"Cash - The Autobiography of Johnny Cash"** - Johnny Cash

10. **"Barefaced Lies and Boogie-Woogie Boasts"** - Jools Holland

11. **"Fahrenheit 182"** - Mark Hoppus

12. **"My House of Memories"** - Merle Haggard

13. **"The Amplifications"** - Nirvana

14. **"Why Bob Dylan Matters"** - Richard F. Thomas

15. **"Altamont - The Rolling Stones, the Hells Angels"** - Rolling Stones

16. **"Can I Say"** - Travis Barker

---

## 🔍 Root Cause Analysis

### **The Problem:**
1. Books were processed to `ut-processed-content` bucket
2. Production KG rebuild scripts only look at `ut-v2-prod-lake-east1` bucket
3. No synchronization between buckets for book content
4. Rebuild on Sept 19 didn't include books despite metadata claiming 5,211 book relationships

### **Why It Happened:**
```
Processing Pipeline:
Raw Books → ut-processed-content → ✅ Enhanced KG Created
                                    ↓
                                    ❌ Never copied to production bucket
                                    ↓
Production Rebuild → ut-v2-prod-lake-east1 → ❌ No books found
```

---

## 🔧 RESTORATION STEPS

### **Step 1: Copy Book Enhanced KGs to Production**
```bash
# Copy all book enhanced KGs to production bucket
aws s3 sync s3://ut-processed-content/enhanced-knowledge-graph/ \
  s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph-books/ \
  --exclude "*" --include "*book_*"
```

### **Step 2: Update Rebuild Script**
The rebuild script needs to include:
- `ut-v2-prod-lake-east1/enhanced-knowledge-graph-books/`
- `ut-processed-content/enhanced-knowledge-graph/` (for future books)

### **Step 3: Re-run Knowledge Graph Aggregation**
```python
# Update the rebuild script to include books
source_patterns = [
    's3://ut-v2-prod-lake-east1/video_analysis/**/*.json',
    's3://ut-v2-prod-lake-east1/scraped-content/**/*.json',
    's3://ut-v2-prod-lake-east1/enhanced-knowledge-graph-books/**/*.json',  # ADD THIS
    's3://ut-processed-content/enhanced-knowledge-graph/**/*book_*.json'     # ADD THIS
]
```

### **Step 4: Validate Restoration**
```bash
# After rebuild, verify books are included
curl -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
  -H "Content-Type: application/json" \
  -d '{"query": "Just Kids Patti Smith Robert Mapplethorpe", "domain": "music"}'

# Should return relationships from the book
```

---

## 📊 Expected Outcome

### **Before Restoration:**
- 0 book relationships in production
- 7,278 total relationships
- False metadata claiming 5,211 book relationships

### **After Restoration:**
- ~2,000+ book relationships (estimated from 16 books)
- ~9,000+ total relationships
- Accurate metadata

### **Key Relationships to Verify:**
- Patti Smith ↔ Robert Mapplethorpe (Just Kids)
- Amy Winehouse relationships (In Her Own Words)
- Charlie Parker jazz connections (Kansas City Lightning)
- Johnny Cash autobiography connections
- Blue Note Records artist connections

---

## 🚨 Prevention Measures

### **Immediate:**
1. Add book validation to deployment checklist
2. Create automated test for book content presence
3. Fix metadata counting to match actual content

### **Long-term:**
1. Unify bucket architecture (single source of truth)
2. Add content type validation in rebuild scripts
3. Implement regression tests for all content types
4. Add monitoring alerts for content loss

---

## ✅ Verification Commands

```bash
# 1. Check book count in production after fix
aws s3 ls s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph-books/ --recursive | wc -l

# 2. Verify specific book content
aws s3 cp s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph-books/[book_file] - | \
  jq '.total_relationships'

# 3. Test API for book content
for book in "Just Kids" "Amy Winehouse" "Charlie Parker"; do
  echo "Testing: $book"
  curl -s -X POST "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/v2/broker" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$book\", \"domain\": \"music\"}" | \
    jq '.insights.total_relationships_analyzed'
done
```

---

## 📝 Notes
- All 16 books were properly processed through the pipeline
- The content exists and is valid
- This is purely a deployment/aggregation issue
- No data was actually lost, just not included in production
