#!/bin/bash

echo "🚨 EMERGENCY ROLLBACK PROCEDURE"
echo "================================"

# Configuration
BUCKET="ut-v2-prod-lake-east1"
KG_PATH="enhanced-knowledge-graph"
API_ENDPOINT="https://166ws8jk15.execute-api.us-east-1.amazonaws.com/prod"

# Function to test foundation
test_foundation() {
    echo "Testing foundation integrity..."
    ART_BLAKEY_COUNT=$(curl -s -X POST "$API_ENDPOINT/v2/broker" \
      -H "Content-Type: application/json" \
      -d '{"query": "tell me about Art Blakey", "domain": "music"}' | \
      jq '.connections.direct_connections[0].connection_count')

    if [ "$ART_BLAKEY_COUNT" -ge 4 ]; then
        echo "✅ Foundation stable: Art Blakey has $ART_BLAKEY_COUNT connections"
        return 0
    else
        echo "❌ Foundation compromised: Art Blakey has only $ART_BLAKEY_COUNT connections"
        return 1
    fi
}

# Check if rollback is needed
echo "1. Checking current foundation status..."
if test_foundation; then
    echo "Foundation is stable. No rollback needed."
    read -p "Continue with rollback anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Rollback cancelled."
        exit 0
    fi
fi

# Find latest backup
echo "2. Finding latest backup..."
LATEST_BACKUP=$(aws s3 ls s3://$BUCKET/$KG_PATH/backups/ | grep "pre_" | tail -1 | awk '{print $4}')

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No backup files found!"
    echo "Available backups:"
    aws s3 ls s3://$BUCKET/$KG_PATH/backups/
    exit 1
fi

echo "Latest backup found: $LATEST_BACKUP"

# Confirm rollback
echo "3. Confirming rollback operation..."
echo "This will restore the knowledge graph from: $LATEST_BACKUP"
read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# Create safety backup of current state
echo "4. Creating safety backup of current state..."
SAFETY_BACKUP="emergency_rollback_safety_$(date +%Y%m%d_%H%M%S).json"
aws s3 cp s3://$BUCKET/$KG_PATH/current/latest.json \
  s3://$BUCKET/$KG_PATH/backups/$SAFETY_BACKUP

if [ $? -eq 0 ]; then
    echo "✅ Safety backup created: $SAFETY_BACKUP"
else
    echo "❌ Failed to create safety backup!"
    exit 1
fi

# Perform rollback
echo "5. Performing rollback..."
aws s3 cp s3://$BUCKET/$KG_PATH/backups/$LATEST_BACKUP \
  s3://$BUCKET/$KG_PATH/current/latest.json

if [ $? -eq 0 ]; then
    echo "✅ Rollback completed successfully"
else
    echo "❌ Rollback failed!"
    exit 1
fi

# Wait for propagation
echo "6. Waiting for changes to propagate..."
sleep 10

# Validate restoration
echo "7. Validating restoration..."
if test_foundation; then
    echo "✅ ROLLBACK SUCCESSFUL"
    echo "Foundation restored and validated"

    # Show current stats
    echo ""
    echo "Current system status:"
    echo "- Art Blakey connections: $ART_BLAKEY_COUNT"

    TOTAL_RELATIONSHIPS=$(aws s3 cp s3://$BUCKET/$KG_PATH/current/latest.json - | jq '.metadata.total_relationships')
    echo "- Total relationships: $TOTAL_RELATIONSHIPS"

    # Test API health
    API_STATUS=$(curl -s "$API_ENDPOINT/health" | jq -r '.status')
    echo "- API status: $API_STATUS"

    echo ""
    echo "Rollback completed successfully!"
    echo "Safety backup available at: s3://$BUCKET/$KG_PATH/backups/$SAFETY_BACKUP"

else
    echo "❌ ROLLBACK VALIDATION FAILED"
    echo "Foundation still compromised after rollback"
    echo "Manual intervention required!"

    # Show available backups for manual selection
    echo ""
    echo "Available backups for manual restoration:"
    aws s3 ls s3://$BUCKET/$KG_PATH/backups/ | tail -10

    echo ""
    echo "Manual restoration command:"
    echo "aws s3 cp s3://$BUCKET/$KG_PATH/backups/[BACKUP_FILE] s3://$BUCKET/$KG_PATH/current/latest.json"

    exit 1
fi