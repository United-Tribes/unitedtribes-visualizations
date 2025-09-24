# United Tribes Content Harvester

**Official Name**: **Content Harvester** (or "Harvester" for short)

A scheduled content acquisition system that enriches the United Tribes knowledge base with music journalism, reviews, and podcast transcripts.

## 📋 System Overview

**What it is**: Background content scraping system for knowledge base enrichment
**What it's not**: Customer-facing API or real-time service
**Purpose**: Gather high-quality music content to improve API citations and knowledge depth
**Architecture**: Cron job with comprehensive validation and S3 organization

## 🚀 How to Invoke the Content Harvester

### Basic Invocation

```bash
# Navigate to the system directory
cd /Users/shanandelp/Documents/unitedtribes/v3-data-lake-and-api/content_scrapers

# Basic harvest (safe default)
python3 cron/scraper_job.py

# Dry run (test without uploading)
python3 cron/scraper_job.py --dry-run
```

### Common Use Cases

#### 1. **Weekly Content Harvest** (Recommended)
```bash
# Harvest from multiple sources weekly
python3 cron/scraper_job.py \
  --sources pitchfork npr rolling_stone \
  --max-articles 20

# Schedule as cron job (Sundays at 6 AM)
0 6 * * 0 cd /path/to/content_scrapers && python3 cron/scraper_job.py --sources pitchfork npr --max-articles 20
```

#### 2. **Targeted Artist Research**
```bash
# Focus on specific artists/topics
python3 cron/scraper_job.py \
  --sources pitchfork \
  --search-keywords "Miles Davis" "John Coltrane" \
  --max-articles 10
```

#### 3. **Breaking News Harvest**
```bash
# Quick harvest of recent content
python3 cron/scraper_job.py \
  --sources all \
  --days-back 3 \
  --max-articles 50
```

#### 4. **Test Run** (Always start here)
```bash
# Safe test with minimal content
python3 cron/scraper_job.py \
  --dry-run \
  --sources pitchfork \
  --max-articles 2
```

## 📖 Command Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `python3 cron/scraper_job.py` | Basic harvest with defaults | Harvests 5 articles from Pitchfork |
| `--dry-run` | Test without uploading to S3 | Safe testing mode |
| `--sources SOURCE [SOURCE...]` | Specify content sources | `--sources pitchfork npr` |
| `--max-articles N` | Limit articles per source | `--max-articles 20` |
| `--config CONFIG_FILE` | Use custom configuration | `--config weekly_harvest.json` |

### Available Sources

| Source | Code | Content Type | Quality |
|--------|------|--------------|---------|
| **Pitchfork** | `pitchfork` | Album reviews, music features | ⭐⭐⭐⭐⭐ |
| **NPR** | `npr` | Fresh Air transcripts, music interviews | ⭐⭐⭐⭐⭐ |
| **Rolling Stone** | `rolling_stone` | Music news, artist profiles | ⭐⭐⭐⭐ |
| **Billboard** | `billboard` | Industry news, chart analysis | ⭐⭐⭐ |

### Configuration Options

Create `config.json` for custom settings:
```json
{
  "sources": ["pitchfork", "npr"],
  "max_articles_per_source": 20,
  "dry_run": false,
  "enable_safety_checks": true,
  "enable_s3_upload": true,
  "log_level": "INFO",
  "max_runtime_minutes": 60
}
```

## 📊 Monitoring & Results

### Check Harvest Status
```bash
# View recent logs
tail -f cron/logs/scraper_$(date +%Y%m%d).log

# Check job reports
ls -la cron/reports/job_report_*.json

# View S3 content
aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive
```

### Harvest Output Structure
```
S3: ut-v2-prod-lake-east1/scraped-content/
├── kendrick_lamar/
│   └── review/
│       └── pitchfork_20240119_damn_review.json
├── patti_smith/
│   └── interview/
│       └── npr_20240119_horses_fresh_air.json
└── miles_davis/
    └── analysis/
        └── rolling_stone_20240119_kind_of_blue.json

Manifests: manifests/scraped/[source]/[date]/batch_[id].json
Logs: cron/logs/scraper_[date].log
Reports: cron/reports/job_report_[timestamp].json
```

## 🛡️ Safety Protocols

### Pre-Harvest Checks (Automatic)
- ✅ API health verification
- ✅ Data lake integrity check
- ✅ S3 access validation
- ✅ Critical artist connection verification

### Harvest Safeguards
- 🔒 **Non-destructive**: Never overwrites existing content
- 🔒 **Isolated**: No impact on customer-facing APIs
- 🔒 **Validated**: Comprehensive content quality checks
- 🔒 **Monitored**: Full logging and reporting
- 🔒 **Rollback-safe**: Operations can be undone if needed

## 🚨 Troubleshooting

### Common Issues

**Issue**: `Safety checks failed`
**Solution**: Check API health and data lake status
```bash
curl -s "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health"
```

**Issue**: `S3 upload failed`
**Solution**: Verify AWS credentials and bucket permissions
```bash
aws s3 ls s3://ut-v2-prod-lake-east1/
```

**Issue**: `No content discovered`
**Solution**: Check source websites and network connectivity

**Issue**: `Validation errors`
**Solution**: Review content quality settings in validator.py

### Emergency Commands
```bash
# Check system health
python3 safety_checklist.py

# Test core components
python3 simple_test.py

# Emergency stop (if running in background)
pkill -f scraper_job.py
```

## 📞 Quick Reference Card

```bash
# SAFE START (always do this first)
python3 cron/scraper_job.py --dry-run --sources pitchfork --max-articles 2

# WEEKLY HARVEST (production)
python3 cron/scraper_job.py --sources pitchfork npr --max-articles 20

# CHECK RESULTS
tail -f cron/logs/scraper_$(date +%Y%m%d).log

# VERIFY API HEALTH
curl -s "https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health"
```

---

## 🎯 System Aliases

For convenience, you can create shell aliases:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias harvest='python3 /path/to/content_scrapers/cron/scraper_job.py'
alias harvest-test='python3 /path/to/content_scrapers/cron/scraper_job.py --dry-run'
alias harvest-logs='tail -f /path/to/content_scrapers/cron/logs/scraper_$(date +%Y%m%d).log'
alias harvest-check='python3 /path/to/content_scrapers/safety_checklist.py'

# Usage:
harvest --sources pitchfork --max-articles 10
harvest-test --sources npr --max-articles 5
harvest-logs
harvest-check
```

**The United Tribes Content Harvester**: Autonomous, safe, and designed to enrich your knowledge base without touching production systems.