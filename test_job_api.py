#!/usr/bin/env python3
"""
Test script for the single job processing API

This script tests the /api/v1/jobs/ endpoint.
"""

import httpx
import json
import time
import asyncio

# Configuration
API_BASE_URL = "http://127.0.0.1:9000"
JOBS_ENDPOINT = f"{API_BASE_URL}/api/v1/jobs/"
API_KEY = "pdf-processing-api-key-2024"

# Test data for single job processing
test_job_data = {
    "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
    "file_name": "test-document.pdf",
    "complete_references": False
}

async def test_job_processing():
    """Test the single job processing endpoint"""
    
    print("🚀 Testing Single Job Processing API")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Submit job
            print("📤 Submitting single job...")
            print(f"Endpoint: {JOBS_ENDPOINT}")
            print(f"File URL: {test_job_data['file_url']}")
            
            response = await client.post(
                JOBS_ENDPOINT,
                json=test_job_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                }
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text[:500]}")
            
            if response.status_code == 202:
                result = response.json()
                print("✅ Job submitted successfully!")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Status: {result['status']}")
                print(f"   File URL: {result['file_url']}")
                
                job_id = result['job_id']
                
                # 2. Check job status after a short delay
                print("\n🔍 Checking job status...")
                await asyncio.sleep(5)  # Wait a bit for processing
                
                status_response = await client.get(
                    f"{JOBS_ENDPOINT}{job_id}",
                    headers={"X-API-Key": API_KEY}
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"✅ Job status retrieved successfully!")
                    print(f"   Job ID: {status_data['job_id']}")
                    print(f"   Status: {status_data['status']}")
                    if status_data.get('doc_metadata'):
                        print(f"   Metadata: {json.dumps(status_data['doc_metadata'], indent=2)[:200]}...")
                    if status_data.get('references'):
                        print(f"   References count: {len(status_data['references'])}")
                else:
                    print(f"❌ Failed to get job status: {status_response.status_code}")
                    print(f"   Response: {status_response.text}")
                
            else:
                print(f"❌ Failed to submit job: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"💥 Error during testing: {str(e)}")

def test_json_format():
    """Test that our JSON format is valid"""
    print("📋 Testing job JSON format...")
    try:
        json_str = json.dumps(test_job_data, indent=2)
        print("✅ JSON format is valid")
        print("📄 Sample JSON:")
        print(json_str)
        return True
    except Exception as e:
        print(f"❌ JSON format error: {e}")
        return False

async def test_without_api_key():
    """Test that authentication is required"""
    print("\n🔒 Testing authentication requirement...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                JOBS_ENDPOINT,
                json=test_job_data,
                headers={"Content-Type": "application/json"}
                # No API key header
            )
            
            if response.status_code == 401:
                print("✅ Authentication is working - 401 returned without API key")
            else:
                print(f"⚠️ Unexpected response without API key: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"💥 Error testing authentication: {str(e)}")

if __name__ == "__main__":
    print("🧪 Single Job Processing API Test")
    print("=" * 50)
    
    # Test JSON format first
    if test_json_format():
        print("\n" + "=" * 50)
        # Test authentication
        asyncio.run(test_without_api_key())
        print("\n" + "=" * 50)
        # Run the actual test
        asyncio.run(test_job_processing())
    else:
        print("❌ JSON format test failed, skipping API test") 