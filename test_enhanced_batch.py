#!/usr/bin/env python3
"""
Test script for the enhanced batch processing API

This script demonstrates how to use the new /api/batch/enhanced endpoint
with the specific JSON format required.
"""

import httpx
import json
import time
import asyncio

# Configuration
API_BASE_URL = "http://127.0.0.1:9000"
ENHANCED_BATCH_ENDPOINT = f"{API_BASE_URL}/api/v1/batch/enhanced"
STATUS_ENDPOINT = f"{API_BASE_URL}/api/v1/batch"
API_KEY = "pdf-processing-api-key-2024"

# Test data matching your exact format
test_batch_data = {
    "files": [
        {
            "des_id": 3,
            "entry_id": "20",
            "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
            "metadata": {
                "year": "1234",
                "issue": "12",
                "volume": "123",
                "journal": "test"
            }
        },
        {
            "des_id": 4,
            "entry_id": "21",
            "file_url": "http://127.0.0.1:8000/media/dms_files/2/532-534.pdf",
            "metadata": {
                "year": "1234",
                "issue": "12",
                "volume": "123",
                "journal": "test"
            }
        },
        {
            "des_id": 5,
            "entry_id": "22",
            "file_url": "http://127.0.0.1:8000/media/dms_files/3/223-224.pdf",
            "metadata": {
                "year": "1112",
                "issue": "212",
                "volume": "1233",
                "journal": "test"
            }
        }
    ],
    "options": {
        "extract_metadata": True,
        "extract_full_text": True,
        "extract_references": True
    },
    "batch_id": "test_batch_" + str(int(time.time())),
    "webhook_url": "http://127.0.0.1:8000/api-integration/webhook/"
}

async def test_enhanced_batch_processing():
    """Test the enhanced batch processing endpoint"""
    
    print("🚀 Testing Enhanced Batch Processing API")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Submit batch job
            print("📤 Submitting batch job...")
            print(f"Endpoint: {ENHANCED_BATCH_ENDPOINT}")
            print(f"Batch ID: {test_batch_data['batch_id']}")
            print(f"Files: {len(test_batch_data['files'])}")
            
            response = await client.post(
                ENHANCED_BATCH_ENDPOINT,
                json=test_batch_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                }
            )
            
            if response.status_code == 202:
                result = response.json()
                print("✅ Batch job submitted successfully!")
                print(f"   Batch ID: {result['batch_id']}")
                print(f"   Status: {result['status']}")
                print(f"   Total files: {result['total_files']}")
                print(f"   Created at: {result['created_at']}")
                
                batch_id = result['batch_id']
                
                # 2. Monitor batch status
                print("\n🔍 Monitoring batch status...")
                max_attempts = 30  # Wait up to 30 * 10 = 5 minutes
                attempt = 0
                
                while attempt < max_attempts:
                    attempt += 1
                    await asyncio.sleep(10)  # Wait 10 seconds between checks
                    
                    status_response = await client.get(
                        f"{STATUS_ENDPOINT}/{batch_id}/status",
                        headers={"X-API-Key": API_KEY}
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"   Attempt {attempt}: Status = {status_data['status']}")
                        print(f"   Processed: {status_data['processed_files']}/{status_data['total_files']}")
                        print(f"   Failed: {status_data['failed_files']}")
                        
                        if status_data['status'] in ['completed', 'failed']:
                            print(f"\n🎉 Batch processing {status_data['status']}!")
                            if status_data['completed_at']:
                                print(f"   Completed at: {status_data['completed_at']}")
                            break
                    else:
                        print(f"   ❌ Error checking status: {status_response.status_code}")
                
                else:
                    print("⏰ Timeout waiting for batch completion")
                
            else:
                print(f"❌ Failed to submit batch job: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"💥 Error during testing: {str(e)}")

def test_json_format():
    """Test that our JSON format is valid"""
    print("📋 Testing JSON format...")
    try:
        json_str = json.dumps(test_batch_data, indent=2)
        print("✅ JSON format is valid")
        print("📄 Sample JSON:")
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
        return True
    except Exception as e:
        print(f"❌ JSON format error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Enhanced Batch Processing API Test")
    print("=" * 50)
    
    # Test JSON format first
    if test_json_format():
        print("\n" + "=" * 50)
        # Run the actual test
        asyncio.run(test_enhanced_batch_processing())
    else:
        print("❌ JSON format test failed, skipping API test") 