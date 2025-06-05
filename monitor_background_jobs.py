#!/usr/bin/env python3
"""
Background Jobs Monitor
Real-time monitoring script for PDF processing background jobs
"""

import time
import subprocess
import argparse
from datetime import datetime
import json

def tail_logs(log_file="server.log", follow=True, lines=50):
    """Monitor log file for background job activity"""
    print(f"🔍 Monitoring background jobs from {log_file}")
    print("=" * 80)
    
    if follow:
        # Use tail -f for real-time monitoring
        cmd = ["tail", "-f", log_file]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        try:
            for line in iter(process.stdout.readline, ''):
                if any(keyword in line for keyword in [
                    "🚀 Starting background",
                    "📊 BATCH SUMMARY", 
                    "🎉 Batch processing",
                    "⚠️ Processing failed",
                    "⚠️ Webhook",
                    "ERROR",
                    "WARNING",
                    "batch/enhanced",
                    "batch/process"
                ]):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] {line.strip()}")
        except KeyboardInterrupt:
            print("\n📴 Stopping log monitoring...")
            process.terminate()
    else:
        # Show recent logs
        cmd = ["tail", "-n", str(lines), log_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("📋 Recent Background Job Activity:")
        print("-" * 80)
        for line in result.stdout.split('\n'):
            if any(keyword in line for keyword in [
                "🚀 Starting background",
                "📊 BATCH SUMMARY", 
                "🎉 Batch processing",
                "⚠️ Processing failed",
                "⚠️ Webhook",
                "ERROR",
                "WARNING",
                "batch/enhanced",
                "batch/process"
            ]):
                print(line.strip())

def show_batch_status():
    """Show current batch job status from the API"""
    print("\n📊 Current Batch Job Status:")
    print("-" * 80)
    
    try:
        import requests
        
        # Check for recent batch jobs
        response = requests.get("http://127.0.0.1:9000/api/v1/batch/recent", 
                              headers={"X-API-Key": "pdf-processing-api-key-2024"},
                              timeout=5)
        
        if response.status_code == 200:
            batches = response.json()
            for batch in batches[:5]:  # Show last 5 batches
                print(f"Batch ID: {batch.get('batch_id', 'N/A')}")
                print(f"  Status: {batch.get('status', 'N/A')}")
                print(f"  Files: {batch.get('processed_files', 0)}/{batch.get('total_files', 0)}")
                print(f"  Created: {batch.get('created_at', 'N/A')}")
                print("")
        else:
            print("⚠️ Could not fetch batch status from API")
            
    except Exception as e:
        print(f"⚠️ Error connecting to API: {e}")

def main():
    parser = argparse.ArgumentParser(description="Monitor PDF Processing Background Jobs")
    parser.add_argument("--follow", "-f", action="store_true", 
                       help="Follow log file in real-time (like tail -f)")
    parser.add_argument("--lines", "-n", type=int, default=100,
                       help="Number of recent lines to show (default: 100)")
    parser.add_argument("--log-file", default="server.log",
                       help="Log file to monitor (default: server.log)")
    parser.add_argument("--status", "-s", action="store_true",
                       help="Show current batch job status")
    
    args = parser.parse_args()
    
    print("🖥️  PDF Processing API - Background Jobs Monitor")
    print("=" * 80)
    
    if args.status:
        show_batch_status()
    
    if args.follow:
        print("\n⏰ Real-time monitoring (Press Ctrl+C to stop)")
        tail_logs(args.log_file, follow=True)
    else:
        tail_logs(args.log_file, follow=False, lines=args.lines)

if __name__ == "__main__":
    main() 