# Content Scraper Cron Job

This is the **correct** deployment approach for content scrapers - as a scheduled job, not a production service.

## Why Cron Job Approach?

- ✅ **Isolated from customer-facing API** - No risk to production services
- ✅ **Runs independently** - Can be scheduled, monitored, and scaled separately
- ✅ **Safe failure mode** - If it fails, it doesn't impact users
- ✅ **Resource efficient** - Only consumes resources when running
- ✅ **Easy monitoring** - Simple log files and reports

## Deployment Options

### Option 1: AWS EventBridge + Lambda (Recommended)
```bash
# Create Lambda function for scheduled execution
aws lambda create-function \
  --function-name ut-v2-content-scraper-cron \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler scraper_job.lambda_handler \
  --code S3Bucket=ut-v2-prod-artifacts-east1,S3Key=scraper-cron.zip \
  --timeout 900 \
  --memory-size 1024

# Create EventBridge rule for weekly execution
aws events put-rule \
  --name content-scraper-weekly \
  --schedule-expression "cron(0 6 * * SUN *)" \
  --description "Weekly content scraping job"

# Add Lambda target
aws events put-targets \
  --rule content-scraper-weekly \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:ut-v2-content-scraper-cron"
```

### Option 2: EC2 Cron Job
```bash
# On a dedicated EC2 instance or existing server
# Add to crontab for weekly Sunday 6 AM execution
0 6 * * 0 /usr/bin/python3 /path/to/scraper_job.py --sources pitchfork npr --max-articles 20
```

### Option 3: Local Development/Testing
```bash
# Run locally for testing
python3 scraper_job.py --dry-run --sources pitchfork --max-articles 3

# Run with actual S3 upload
python3 scraper_job.py --sources pitchfork npr --max-articles 10
```

## Configuration

Create `config.json`:
```json
{
  "sources": ["pitchfork", "npr"],
  "max_articles_per_source": 20,
  "dry_run": false,
  "enable_safety_checks": true,
  "enable_s3_upload": true,
  "log_level": "INFO",
  "max_runtime_minutes": 60,
  "notification_email": "admin@example.com"
}
```

## Expected S3 Output

Content will be organized as:
```
s3://ut-v2-prod-lake-east1/scraped-content/
├── kendrick_lamar/
│   └── review/
│       └── pitchfork_20240119_damn_review.json
├── patti_smith/
│   └── interview/
│       └── npr_20240119_horses_fresh_air.json
└── miles_davis/
    └── analysis/
        └── rolling_stone_20240119_kind_of_blue.json
```

## Monitoring

- **Logs**: `cron/logs/scraper_YYYYMMDD.log`
- **Reports**: `cron/reports/job_report_scraper_job_TIMESTAMP.json`
- **CloudWatch**: Metrics for Lambda execution (if using EventBridge)

## Safety Features

1. **Pre-job safety checks**: API health, data lake integrity, critical artists
2. **Comprehensive validation**: Content quality, music relevance, format compatibility
3. **Batch safety checks**: Size limits, consistency validation
4. **S3 anti-overwrite**: Collision detection and unique naming
5. **Graceful failure**: Job fails safely without impacting production

## Getting Started

1. **Test locally first**:
   ```bash
   python3 scraper_job.py --dry-run --sources pitchfork --max-articles 2
   ```

2. **Deploy to cron when ready**:
   ```bash
   # Weekly Sunday at 6 AM
   0 6 * * 0 /usr/bin/python3 /path/to/scraper_job.py --sources pitchfork npr --max-articles 20
   ```

3. **Monitor execution**:
   ```bash
   tail -f cron/logs/scraper_$(date +%Y%m%d).log
   ```

This approach keeps content scraping completely separate from customer-facing services while providing all the safety and validation we need.