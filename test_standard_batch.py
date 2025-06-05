#!/usr/bin/env python3
"""
Test script for the standard batch processing API

This script tests the existing /api/v1/batch/process endpoint.
"""

import httpx
import json
import time
import asyncio

# Configuration
API_BASE_URL = "http://127.0.0.1:9000"
BATCH_ENDPOINT = f"{API_BASE_URL}/api/v1/batch/process"
STATUS_ENDPOINT = f"{API_BASE_URL}/api/v1/batch"
API_KEY = "pdf-processing-api-key-2024"

# Test data for standard batch format
test_batch_data = {
    "webhook_url": "http://127.0.0.1:8000/api-integration/webhook/",
    "files": [
        {
            "url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
            "file_id": "doc1"
        },
        {
            "url": "http://127.0.0.1:8000/media/dms_files/2/532-534.pdf", 
            "file_id": "doc2"
        }
    ],
    "options": {
        "extract_references": True,
        "extract_metadata": True,
        "extract_full_text": False,
        "complete_references": True
    },
    "batch_id": "test_standard_batch_" + str(int(time.time()))
}

async def test_standard_batch_processing():
    """Test the standard batch processing endpoint"""
    
    print("🚀 Testing Standard Batch Processing API")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Submit batch job
            print("📤 Submitting standard batch job...")
            print(f"Endpoint: {BATCH_ENDPOINT}")
            print(f"Batch ID: {test_batch_data['batch_id']}")
            print(f"Files: {len(test_batch_data['files'])}")
            
            response = await client.post(
                BATCH_ENDPOINT,
                json=test_batch_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                }
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text[:500]}")
            
            if response.status_code == 202:
                result = response.json()
                print("✅ Standard batch job submitted successfully!")
                print(f"   Batch ID: {result['batch_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Total files: {result['total_files']}")
                print(f"   Created at: {result['created_at']}")
                
            else:
                print(f"❌ Failed to submit batch job: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"💥 Error during testing: {str(e)}")

def test_json_format():
    """Test that our JSON format is valid"""
    print("📋 Testing standard batch JSON format...")
    try:
        json_str = json.dumps(test_batch_data, indent=2)
        print("✅ JSON format is valid")
        print("📄 Sample JSON:")
        print(json_str)
        return True
    except Exception as e:
        print(f"❌ JSON format error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Standard Batch Processing API Test")
    print("=" * 50)
    
    # Test JSON format first
    if test_json_format():
        print("\n" + "=" * 50)
        # Run the actual test
        asyncio.run(test_standard_batch_processing())
    else:
        print("❌ JSON format test failed, skipping API test") 