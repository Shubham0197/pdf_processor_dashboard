#!/bin/bash

echo "📊 PDF Processing API - Background Job Logs"
echo "============================================="

# Check if server.log exists
if [ ! -f "server.log" ]; then
    echo "❌ server.log not found. Make sure the server is running with logs redirected to server.log"
    exit 1
fi

echo ""
echo "🔍 Recent Background Job Activity:"
echo "-----------------------------------"

# Show background job related logs
grep -E "(🚀 Starting background|📊 BATCH SUMMARY|🎉 Batch processing|⚠️ Processing failed|⚠️ Webhook|batch/enhanced|batch/process)" server.log | tail -20

echo ""
echo "📈 Job Processing Statistics:"
echo "-----------------------------"

# Count successful jobs
successful=$(grep -c "🎉 Batch processing completed" server.log)
echo "✅ Completed batches: $successful"

# Count failed jobs
failed=$(grep -c "⚠️ Processing failed" server.log)
echo "❌ Failed file processing: $failed"

# Count webhook issues
webhook_issues=$(grep -c "⚠️ Webhook" server.log)
echo "📡 Webhook issues: $webhook_issues"

echo ""
echo "📋 Usage Options:"
echo "-----------------"
echo "To monitor in real-time: tail -f server.log | grep -E '(🚀|📊|🎉|⚠️|ERROR)'"
echo "To see all logs: tail -100 server.log"
echo "To see only errors: grep -E '(ERROR|⚠️)' server.log"
echo "To monitor live: python monitor_background_jobs.py --follow"

echo ""
echo "💡 Log File Locations:"
echo "----------------------"
echo "• Main server logs: ./server.log"
echo "• Database logs: Embedded in server.log (DEBUG level)"
echo "• Background job logs: Embedded in server.log (INFO level)" 