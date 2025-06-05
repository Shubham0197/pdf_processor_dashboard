# Background Jobs Logging Guide

## 📋 Overview
This guide explains how to monitor and troubleshoot background job processing in the PDF Processing API.

## 🔍 Log File Locations

### Main Server Log
- **File**: `server.log`
- **Content**: All server activity including background jobs, API requests, database operations
- **Format**: Structured logging with timestamps and log levels
- **Size**: Grows continuously (consider log rotation for production)

### Log Components
1. **API Request Logs**: HTTP requests and responses
2. **Background Job Logs**: Batch processing activity with emojis for easy identification
3. **Database Logs**: SQLite operations (DEBUG level)
4. **Error Logs**: Warnings and errors with detailed stack traces

## 🎯 Background Job Log Patterns

### Key Emojis and Patterns to Look For:
- `🚀 Starting background task` - Job initialization
- `📊 BATCH SUMMARY` - Processing completion summary
- `🎉 Batch processing completed` - Successful completion
- `⚠️ Processing failed` - Individual file processing failures
- `⚠️ Webhook` - Webhook delivery issues
- `ERROR` - System errors
- `WARNING` - Non-critical issues

### Log Entry Examples:
```
INFO:app.api.endpoints.batch:🚀 Starting background task with enhanced PDF processing
WARNING:app.api.endpoints.batch:⚠️ Processing failed for http://example.com/file.pdf: PDF file not found
INFO:app.api.endpoints.batch:🎉 Batch processing completed: 2 processed, 0 failed
INFO:app.api.endpoints.batch:📊 BATCH SUMMARY:
```

## 🛠️ Monitoring Tools

### 1. Quick Log Viewer Script
```bash
./show_job_logs.sh
```
**Features:**
- Shows recent background job activity
- Displays processing statistics
- Provides usage suggestions

### 2. Real-time Monitoring
```bash
# Option 1: Using the monitoring script
python monitor_background_jobs.py --follow

# Option 2: Using tail with grep
tail -f server.log | grep -E '(🚀|📊|🎉|⚠️|ERROR)'

# Option 3: Basic tail
tail -f server.log
```

### 3. Filtering Specific Events
```bash
# Show only errors and warnings
grep -E '(ERROR|WARNING|⚠️)' server.log

# Show only successful completions
grep "🎉 Batch processing completed" server.log

# Show batch summaries
grep "📊 BATCH SUMMARY" server.log

# Show failed file processing
grep "⚠️ Processing failed" server.log

# Show webhook issues
grep "⚠️ Webhook" server.log
```

## 📊 Log Analysis Commands

### Processing Statistics
```bash
# Count successful batches
grep -c "🎉 Batch processing completed" server.log

# Count failed file processing attempts
grep -c "⚠️ Processing failed" server.log

# Count webhook delivery issues
grep -c "⚠️ Webhook" server.log

# Show recent batch activity
grep "🚀 Starting background" server.log | tail -10
```

### Recent Activity
```bash
# Last 50 lines of background job logs
grep -E "(🚀|📊|🎉|⚠️)" server.log | tail -50

# Today's processing activity
grep "$(date +%Y-%m-%d)" server.log | grep -E "(🚀|📊|🎉|⚠️)"
```

## 🔧 Troubleshooting Common Issues

### 1. File Not Found Errors
**Pattern**: `⚠️ Processing failed for http://... PDF file not found`
**Cause**: The PDF URL is not accessible
**Solution**: 
- Verify the file URL is correct and accessible
- Check if the external server (Django on port 8000) is running
- Ensure network connectivity between services

### 2. Webhook Delivery Failures
**Pattern**: `⚠️ Webhook returned status 403 for batch`
**Cause**: Webhook endpoint is not accepting requests
**Solution**:
- Verify webhook URL is correct
- Check if the webhook endpoint is running
- Verify authentication/authorization for webhook endpoint

### 3. Processing Timeouts
**Pattern**: Long delays between start and completion
**Cause**: Large files or slow external services
**Solution**:
- Monitor processing time per file
- Check Gemini API response times
- Consider implementing timeout handling

### 4. Database Connection Issues
**Pattern**: SQLite connection errors in DEBUG logs
**Cause**: Database locked or corruption
**Solution**:
- Check database file permissions
- Restart the application
- Consider database backup and restore

## 📈 Performance Monitoring

### Key Metrics to Track:
1. **Batch Completion Rate**: Successful vs. failed batches
2. **File Processing Success Rate**: Individual file success/failure ratio
3. **Processing Time**: Time from start to completion
4. **Webhook Delivery Success**: Webhook notification reliability
5. **Error Patterns**: Common failure reasons

### Monitoring Queries:
```bash
# Average processing time (manual calculation needed)
grep "processing completed" server.log

# Failure patterns
grep "⚠️ Processing failed" server.log | cut -d':' -f4- | sort | uniq -c

# Daily processing volume
grep "$(date +%Y-%m-%d)" server.log | grep "🚀 Starting background" | wc -l
```

## 🔄 Log Rotation (Production Recommendation)

For production environments, implement log rotation:

```bash
# Install logrotate configuration
sudo cat > /etc/logrotate.d/pdf-processing-api << EOF
/path/to/pdf_processing_api/server.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

## ⚙️ Advanced Monitoring Setup

### 1. Real-time Dashboard (Optional)
Consider implementing tools like:
- **Grafana** + **Loki** for log aggregation
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Simple web dashboard** showing batch status

### 2. Alerting (Optional)
Set up alerts for:
- High failure rates
- Processing delays
- Webhook delivery failures
- System errors

### 3. Structured Logging Enhancement
For production, consider:
- JSON formatted logs
- Correlation IDs for tracking requests
- More detailed timing information
- Performance metrics collection

## 📞 Quick Reference Commands

```bash
# Show recent job activity
./show_job_logs.sh

# Monitor in real-time
python monitor_background_jobs.py --follow

# Check server status
ps aux | grep uvicorn

# View last 100 log lines
tail -100 server.log

# Search for specific batch ID
grep "batch_id_here" server.log

# Show only errors
grep -E "(ERROR|⚠️)" server.log | tail -20
```

## 🎯 Best Practices

1. **Regular Monitoring**: Check logs periodically for issues
2. **Error Investigation**: Investigate repeated error patterns
3. **Performance Tracking**: Monitor processing times and success rates
4. **Webhook Testing**: Regularly verify webhook endpoints are working
5. **Log Cleanup**: Implement log rotation for disk space management
6. **Backup Monitoring**: Ensure important logs are backed up

## 📱 Integration with Monitoring Tools

The logs are designed to be easily parsed by monitoring tools. Key integration points:

- **Log Level**: INFO for normal operations, WARNING for issues, ERROR for failures
- **Structured Messages**: Consistent emoji patterns for easy filtering
- **Timestamps**: All entries include timestamps for correlation
- **Batch IDs**: Searchable batch identifiers for tracking specific jobs 