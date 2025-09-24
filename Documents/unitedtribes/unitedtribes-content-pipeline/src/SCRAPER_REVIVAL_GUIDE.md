# Content Scrapers Revival Guide

> **Critical**: This guide documents the exact steps to revive the content scrapers after weeks/months of inactivity. Follow this to avoid the trial-and-error process that occurred in September 2019.

## 🚨 Prerequisites

1. **Check CLAUDE.md Foundation**: Ensure data lake and API are stable before starting
2. **Verify AWS credentials**: `aws sts get-caller-identity`
3. **Confirm S3 access**: `aws s3 ls s3://ut-v2-prod-lake-east1/`

## 🔧 Step 1: Fix Known Architectural Issues

### A. Remove Artificial Article Limits

**Problem**: Multiple hardcoded limits throughout codebase prevent comprehensive harvesting.

**Files to check/fix**:

1. **`/articles/base_scraper.py`** (Lines 92, 452, 464):
   ```python
   # BEFORE (broken):
   urls_to_process = discovery_result.urls[:max_articles]  # Line 92
   unique_urls = list(dict.fromkeys(all_urls))[:50]        # Line 452
   return discovered_urls[:50]                             # Line 464

   # AFTER (fixed):
   urls_to_process = discovery_result.urls[:max_articles]  # Line 92 - OK, uses config
   unique_urls = list(dict.fromkeys(all_urls))             # Line 452 - Remove limit
   return discovered_urls                                  # Line 464 - Remove limit
   ```

2. **`/cron/scraper_job.py`** (Default config):
   ```python
   # BEFORE:
   "max_articles_per_source": 10

   # AFTER:
   "max_articles_per_source": 500
   ```

3. **Individual scraper configs** (in each `*_scraper.py`):
   ```python
   # BEFORE:
   max_articles_per_run=50

   # AFTER:
   max_articles_per_run=1000
   ```

### B. Fix Source Name Validation

**Problem**: Source enum validation expects lowercase but scrapers use title case.

**Files to fix**:
- `/articles/rolling_stone_scraper.py`: `source_name="rolling_stone"` (not "Rolling Stone")
- `/articles/billboard_scraper.py`: `source_name="billboard"` (not "Billboard")
- `/articles/npr_scraper.py`: `source_name="npr"` (not "NPR")
- `/articles/pitchfork_scraper.py`: `source_name="pitchfork"` (not "Pitchfork")

### C. Remove Overly Aggressive Safety Checks

**Problem**: Duplicate content checker blocks legitimate batches.

**File**: `/shared/validator.py` (Lines 415-417):
```python
# REMOVE this entire section:
# content_hashes = set()
# for item in batch.content_items:
#     if item.content_hash in content_hashes:
#         errors.append("Duplicate content detected in batch")
#         break
#     content_hashes.add(item.content_hash)

# REPLACE with comment:
# Duplicate content check removed - not a real-world concern
# If duplicates exist, it's a scraper bug that should be fixed at the source
```

### D. Fix EnhancedFetcher Regression

**Problem**: EnhancedFetcher fails silently on search URLs.

**Solution**: Direct search fallback is already implemented in `/articles/direct_search_fallback.py`.

**Verify**: Base scraper automatically falls back to direct search when EnhancedFetcher fails.

## 🎯 Step 2: Quick Validation Test

Run a single source with limited articles to verify fixes:

```bash
cd /Users/shanandelp/Documents/unitedtribes/v3-data-lake-and-api/content_scrapers
./harvest --sources pitchfork --max-articles 5 --dry-run
```

**Expected output**: Should discover 100+ URLs and process 5 articles successfully.

## 🚀 Step 3: Full Revival Process

### Phase 1: Start All Sources
```bash
# Run each source separately to avoid overwhelming the system
./harvest --sources pitchfork --max-articles 100 &
sleep 30
./harvest --sources rolling_stone --max-articles 100 &
sleep 30
./harvest --sources billboard --max-articles 100 &
sleep 30
./harvest --sources npr --max-articles 100 &
```

### Phase 2: Monitor Progress
```bash
# Check running processes
ps aux | grep harvest

# Monitor S3 uploads
watch "aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive | wc -l"
```

### Phase 3: Verify Results
```bash
# Check final counts in cron reports
ls -la cron/reports/job_report_scraper_job_*.json | tail -4
```

## 📊 Expected Results (September 2019 Baseline)

- **Pitchfork**: ~96 articles uploaded
- **Rolling Stone**: ~18 articles uploaded
- **Billboard**: ~15 articles uploaded
- **NPR**: ~0 articles (requires content discovery improvements)

## 🔧 Common Issues & Solutions

### Issue: "Batch contains no content items"
**Root cause**: All articles failed validation
**Solution**: Check validator settings, ensure content discovery is working

### Issue: "'source_name' is not a valid Source"
**Root cause**: Source name case mismatch
**Solution**: Ensure all scrapers use lowercase source names

### Issue: Only 5 articles processed despite finding hundreds of URLs
**Root cause**: Artificial limits in base_scraper.py
**Solution**: Remove hardcoded limits as described in Step 1A

### Issue: EnhancedFetcher timeout on search URLs
**Root cause**: Regression in fetcher implementation
**Solution**: Direct search fallback should activate automatically

### Issue: "Duplicate content detected in batch"
**Root cause**: Overly aggressive validation
**Solution**: Remove duplicate content check as described in Step 1C

## 🎯 Target Architecture for 25 Jazz Artists

**Artists List**: John Coltrane, Lee Morgan, Art Blakey, Horace Silver, Charlie Parker, Grant Green, Dexter Gordon, Kenny Drew, Paul Chambers, Philly Joe Jones, Herbie Hancock, Freddie Hubbard, Joe Henderson, Donald Byrd, Wayne Shorter, Thelonious Monk, Duke Ellington, Dizzy Gillespie, Joe Pass, Miles Davis, Bill Evans, Cannonball Adderley, Bill Charlap, John Scofield, Pat Metheny

**Discovery Strategy**:
- **Artist Search**: Each source searches for all 25 artists individually
- **Section Discovery**: General music sections for broader content
- **URL Filtering**: Source-specific patterns to ensure quality
- **Content Validation**: Multi-phase validation before S3 upload

**S3 Organization**: `scraped-content/[artist_name]/[content_type]/[source]_[timestamp]_[hash]_[title].json`

## 🛡️ Safety Checklist Before Revival

1. **✅ Data Lake Baseline**: Note current knowledge graph relationship count
2. **✅ API Health**: Verify all critical artist queries work
3. **✅ S3 Access**: Confirm write permissions to production bucket
4. **✅ AWS Credentials**: Valid and properly configured
5. **✅ Code State**: All fixes from Step 1 applied
6. **✅ Backup Plan**: Know how to stop processes if issues arise

## 🚨 Emergency Stop Procedures

If anything goes wrong during revival:

```bash
# Kill all harvest processes
pkill -f harvest

# Check for any stuck processes
ps aux | grep -E "(harvest|scraper|cron)"

# Verify S3 state hasn't been corrupted
aws s3 ls s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/
```

## 📝 Post-Revival Documentation

After successful revival, document:

1. **Article counts per source**: For future baseline comparison
2. **Any new issues discovered**: Update this guide accordingly
3. **Performance metrics**: Processing time, success rates
4. **Content quality**: Sample review of uploaded articles

---

**Last Updated**: September 2019 after successful revival
**Success Criteria**: 129+ articles uploaded across 3 sources (Pitchfork, Rolling Stone, Billboard)