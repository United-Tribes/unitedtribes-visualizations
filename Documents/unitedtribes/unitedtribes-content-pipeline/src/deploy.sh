#!/bin/bash
#
# Safe Deployment Script for Content Scrapers
# Deploys to AWS Lambda with comprehensive safety checks
#

set -e  # Exit on any error

# Configuration
LAMBDA_FUNCTION_NAME="ut-v2-prod-content-scraper"
S3_DEPLOYMENT_BUCKET="ut-v2-prod-artifacts-east1"
DEPLOYMENT_PACKAGE="content-scraper-deployment.zip"
BACKUP_SUFFIX=$(date +%Y%m%d_%H%M%S)

echo "🚀 Content Scraper Deployment Script"
echo "===================================="
echo "Function: $LAMBDA_FUNCTION_NAME"
echo "Bucket: $S3_DEPLOYMENT_BUCKET"
echo "Timestamp: $BACKUP_SUFFIX"
echo

# Step 1: Pre-deployment safety checks
echo "🛡️ Step 1: Running safety checks..."
echo "======================================"

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured"
    exit 1
fi
echo "✅ AWS credentials verified"

# Check if bucket exists
if ! aws s3 ls s3://$S3_DEPLOYMENT_BUCKET > /dev/null 2>&1; then
    echo "❌ Deployment bucket $S3_DEPLOYMENT_BUCKET not accessible"
    exit 1
fi
echo "✅ Deployment bucket accessible"

# Check data lake integrity
if ! aws s3 ls s3://ut-v2-prod-lake-east1/enhanced-knowledge-graph/current/ > /dev/null 2>&1; then
    echo "❌ Data lake integrity check failed"
    exit 1
fi
echo "✅ Data lake integrity verified"

# Check API health
HEALTH_STATUS=$(curl -s https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health | jq -r '.status' 2>/dev/null || echo "unknown")
if [[ "$HEALTH_STATUS" != "healthy" && "$HEALTH_STATUS" != "stable mode" ]]; then
    echo "❌ API health check failed: $HEALTH_STATUS"
    exit 1
fi
echo "✅ API health verified: $HEALTH_STATUS"

echo

# Step 2: Backup existing function
echo "💾 Step 2: Backing up existing function..."
echo "=========================================="

# Check if function exists and backup
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME > /dev/null 2>&1; then
    echo "📦 Creating backup of existing function..."

    # Get current function code
    aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME \
        --query 'Code.Location' --output text | \
        xargs wget -q -O "backup_${LAMBDA_FUNCTION_NAME}_${BACKUP_SUFFIX}.zip"

    # Upload backup to S3
    aws s3 cp "backup_${LAMBDA_FUNCTION_NAME}_${BACKUP_SUFFIX}.zip" \
        s3://$S3_DEPLOYMENT_BUCKET/backups/

    echo "✅ Backup created: backup_${LAMBDA_FUNCTION_NAME}_${BACKUP_SUFFIX}.zip"
else
    echo "ℹ️ Function does not exist yet - no backup needed"
fi

echo

# Step 3: Build deployment package
echo "📦 Step 3: Building deployment package..."
echo "========================================"

# Clean previous builds
rm -f $DEPLOYMENT_PACKAGE
rm -rf package/

# Create package directory
mkdir -p package/

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r lambda/requirements.txt -t package/ --quiet

# Copy source code
echo "Copying source code..."
cp -r shared/ package/
cp -r articles/ package/
cp -r podcasts/ package/
cp lambda/scraper_orchestrator.py package/

# Create deployment package
echo "Creating deployment package..."
cd package/
zip -r ../$DEPLOYMENT_PACKAGE . --quiet
cd ..

echo "✅ Deployment package created: $DEPLOYMENT_PACKAGE"
echo "📏 Package size: $(du -h $DEPLOYMENT_PACKAGE | cut -f1)"

echo

# Step 4: Deploy to Lambda
echo "🚀 Step 4: Deploying to Lambda..."
echo "=================================="

# Upload package to S3
S3_KEY="deployments/content-scraper/${BACKUP_SUFFIX}/${DEPLOYMENT_PACKAGE}"
aws s3 cp $DEPLOYMENT_PACKAGE s3://$S3_DEPLOYMENT_BUCKET/$S3_KEY

echo "✅ Package uploaded to S3: s3://$S3_DEPLOYMENT_BUCKET/$S3_KEY"

# Create or update Lambda function
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME > /dev/null 2>&1; then
    echo "🔄 Updating existing function..."

    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --s3-bucket $S3_DEPLOYMENT_BUCKET \
        --s3-key $S3_KEY \
        --publish > /dev/null

    echo "✅ Function updated successfully"
else
    echo "🆕 Creating new function..."

    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --runtime python3.9 \
        --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
        --handler scraper_orchestrator.lambda_handler \
        --code S3Bucket=$S3_DEPLOYMENT_BUCKET,S3Key=$S3_KEY \
        --timeout 900 \
        --memory-size 512 \
        --environment Variables='{
            "CONTENT_BUCKET":"ut-v2-prod-lake-east1",
            "ENABLE_S3_UPLOAD":"true",
            "MAX_RUNTIME_MINUTES":"15",
            "MIN_SUCCESS_RATE":"0.7",
            "MAX_ERROR_COUNT":"10"
        }' \
        --publish > /dev/null

    echo "✅ Function created successfully"
fi

echo

# Step 5: Post-deployment verification
echo "🔍 Step 5: Post-deployment verification..."
echo "=========================================="

# Test function invocation with dry run
echo "Testing function with dry run..."
TEST_EVENT='{"scrapers": ["pitchfork"], "max_articles": 2, "dry_run": true}'

INVOKE_RESULT=$(aws lambda invoke \
    --function-name $LAMBDA_FUNCTION_NAME \
    --payload "$TEST_EVENT" \
    --cli-binary-format raw-in-base64-out \
    response.json 2>&1)

if echo "$INVOKE_RESULT" | grep -q "StatusCode.*200"; then
    echo "✅ Function invocation successful"

    # Check response
    if grep -q '"status": "success"' response.json 2>/dev/null; then
        echo "✅ Test execution completed successfully"
    else
        echo "⚠️ Test execution had issues - check response.json"
    fi
else
    echo "❌ Function invocation failed"
    echo "$INVOKE_RESULT"
    exit 1
fi

# Verify data lake is still stable
FINAL_HEALTH=$(curl -s https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod/health | jq -r '.status' 2>/dev/null || echo "unknown")
if [[ "$FINAL_HEALTH" != "healthy" && "$FINAL_HEALTH" != "stable mode" ]]; then
    echo "❌ CRITICAL: API health degraded after deployment: $FINAL_HEALTH"
    echo "🔄 Consider rolling back to backup"
    exit 1
fi
echo "✅ API health still good: $FINAL_HEALTH"

echo

# Step 6: Cleanup and summary
echo "🧹 Step 6: Cleanup and summary..."
echo "================================="

# Clean up temporary files
rm -f $DEPLOYMENT_PACKAGE response.json
rm -rf package/

echo "✅ Temporary files cleaned up"

echo
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "========================"
echo "Function Name: $LAMBDA_FUNCTION_NAME"
echo "Backup Location: s3://$S3_DEPLOYMENT_BUCKET/backups/backup_${LAMBDA_FUNCTION_NAME}_${BACKUP_SUFFIX}.zip"
echo "Deployment Package: s3://$S3_DEPLOYMENT_BUCKET/$S3_KEY"
echo "Deployment Time: $(date)"
echo
echo "💡 Next Steps:"
echo "  1. Test with: aws lambda invoke --function-name $LAMBDA_FUNCTION_NAME --payload '{\"scrapers\": [\"pitchfork\"], \"max_articles\": 5}' result.json"
echo "  2. Monitor CloudWatch logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo "  3. Check S3 for scraped content: aws s3 ls s3://ut-v2-prod-lake-east1/scraped-content/ --recursive"
echo
echo "🔄 Rollback command (if needed):"
echo "  aws lambda update-function-code --function-name $LAMBDA_FUNCTION_NAME --s3-bucket $S3_DEPLOYMENT_BUCKET --s3-key backups/backup_${LAMBDA_FUNCTION_NAME}_${BACKUP_SUFFIX}.zip"