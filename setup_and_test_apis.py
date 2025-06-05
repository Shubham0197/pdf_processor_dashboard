#!/usr/bin/env python3
"""
Comprehensive API Setup and Test Script

This script tests all the main API endpoints after the server restart
to verify that simple API key authentication is working correctly.
"""

import httpx
import json
import time
import asyncio

# Configuration
API_BASE_URL = "http://127.0.0.1:9000"
API_KEY = "pdf-processing-api-key-2024"

# Test endpoints
ENDPOINTS = {
    "enhanced_batch": f"{API_BASE_URL}/api/v1/batch/enhanced",
    "standard_batch": f"{API_BASE_URL}/api/v1/batch/process", 
    "batch_status": f"{API_BASE_URL}/api/v1/batch",
    "jobs": f"{API_BASE_URL}/api/v1/jobs/",
    "docs": f"{API_BASE_URL}/docs",
    "openapi": f"{API_BASE_URL}/api/v1/openapi.json"
}

# Test data
enhanced_batch_data = {
    "files": [
        {
            "des_id": 1,
            "entry_id": "test1",
            "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
            "metadata": {"year": "2023", "journal": "Test Journal"}
        }
    ],
    "options": {
        "extract_metadata": True,
        "extract_references": True,
        "extract_full_text": False
    },
    "batch_id": f"test_enhanced_{int(time.time())}",
    "webhook_url": "http://127.0.0.1:8000/api-integration/webhook/"
}

standard_batch_data = {
    "webhook_url": "http://127.0.0.1:8000/api-integration/webhook/",
    "files": [
        {"url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf", "file_id": "doc1"}
    ],
    "options": {
        "extract_references": True,
        "extract_metadata": True,
        "extract_full_text": False
    },
    "batch_id": f"test_standard_{int(time.time())}"
}

job_data = {
    "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
    "file_name": "test-document.pdf",
    "complete_references": False
}

async def test_server_health():
    """Test if the server is running and accessible"""
    print("🏥 Testing Server Health")
    print("-" * 30)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test docs endpoint (should not require auth)
            response = await client.get(ENDPOINTS["docs"])
            if response.status_code == 200:
                print("✅ Server is running - docs accessible")
                return True
            else:
                print(f"⚠️ Server responding but docs returned {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server not accessible: {str(e)}")
            return False

async def test_openapi_endpoints():
    """Check what endpoints are available in OpenAPI spec"""
    print("\n📋 Checking Available Endpoints")
    print("-" * 35)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(ENDPOINTS["openapi"])
            if response.status_code == 200:
                data = response.json()
                batch_endpoints = [path for path in data['paths'].keys() if 'batch' in path]
                job_endpoints = [path for path in data['paths'].keys() if 'jobs' in path]
                
                print("🎯 Batch endpoints found:")
                for endpoint in batch_endpoints:
                    print(f"   - {endpoint}")
                
                print("🎯 Job endpoints found:")
                for endpoint in job_endpoints:
                    print(f"   - {endpoint}")
                    
                # Check if enhanced endpoint exists
                if "/api/v1/batch/enhanced" in batch_endpoints:
                    print("✅ Enhanced batch endpoint is available!")
                else:
                    print("❌ Enhanced batch endpoint NOT found - server needs restart")
                    
                return batch_endpoints, job_endpoints
            else:
                print(f"❌ Could not fetch OpenAPI spec: {response.status_code}")
                return [], []
        except Exception as e:
            print(f"❌ Error fetching OpenAPI spec: {str(e)}")
            return [], []

async def test_authentication():
    """Test that API key authentication is working"""
    print("\n🔐 Testing Authentication")
    print("-" * 25)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test without API key
        try:
            response = await client.post(
                ENDPOINTS["jobs"],
                json=job_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 401:
                print("✅ Authentication working - 401 without API key")
            elif response.status_code == 422:
                print("⚠️ Schema validation before auth - may still need restart")
            else:
                print(f"⚠️ Unexpected response without API key: {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing no-auth: {str(e)}")
        
        # Test with wrong API key
        try:
            response = await client.post(
                ENDPOINTS["jobs"],
                json=job_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "wrong-api-key"
                }
            )
            
            if response.status_code == 401:
                print("✅ Authentication working - 401 with wrong API key")
            else:
                print(f"⚠️ Unexpected response with wrong API key: {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing wrong auth: {str(e)}")

async def test_enhanced_batch():
    """Test the enhanced batch processing endpoint"""
    print("\n🚀 Testing Enhanced Batch API")
    print("-" * 30)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                ENDPOINTS["enhanced_batch"],
                json=enhanced_batch_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                }
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 202:
                result = response.json()
                print("✅ Enhanced batch API working!")
                print(f"   Batch ID: {result.get('batch_id')}")
                return result.get('batch_id')
            elif response.status_code == 404:
                print("❌ Enhanced batch endpoint not found - restart server")
            elif response.status_code == 401:
                print("❌ Authentication failed - check API key")
            else:
                print(f"⚠️ Unexpected response: {response.text[:200]}")
            
        except Exception as e:
            print(f"❌ Error testing enhanced batch: {str(e)}")
    
    return None

async def test_standard_batch():
    """Test the standard batch processing endpoint"""
    print("\n🔄 Testing Standard Batch API")
    print("-" * 30)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                ENDPOINTS["standard_batch"],
                json=standard_batch_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                }
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 202:
                result = response.json()
                print("✅ Standard batch API working!")
                print(f"   Batch ID: {result.get('batch_id')}")
                return result.get('batch_id')
            elif response.status_code == 401:
                print("❌ Authentication failed - server needs restart")
            else:
                print(f"⚠️ Unexpected response: {response.text[:200]}")
            
        except Exception as e:
            print(f"❌ Error testing standard batch: {str(e)}")
    
    return None

async def test_job_processing():
    """Test the single job processing endpoint"""
    print("\n⚙️ Testing Job Processing API")
    print("-" * 30)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                ENDPOINTS["jobs"],
                json=job_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY
                }
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 202:
                result = response.json()
                print("✅ Job processing API working!")
                print(f"   Job ID: {result.get('job_id')}")
                return result.get('job_id')
            elif response.status_code == 401:
                print("❌ Authentication failed - server needs restart")
            elif response.status_code == 500:
                print("❌ Internal server error - server needs restart")
            else:
                print(f"⚠️ Unexpected response: {response.text[:200]}")
            
        except Exception as e:
            print(f"❌ Error testing job processing: {str(e)}")
    
    return None

async def test_batch_status(batch_id):
    """Test the batch status endpoint"""
    if not batch_id:
        print("\n⏩ Skipping batch status test - no batch ID")
        return
        
    print(f"\n📊 Testing Batch Status API for {batch_id}")
    print("-" * 40)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{ENDPOINTS['batch_status']}/{batch_id}/status",
                headers={"X-API-Key": API_KEY}
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Batch status API working!")
                print(f"   Status: {result.get('status')}")
                print(f"   Total files: {result.get('total_files')}")
            elif response.status_code == 401:
                print("❌ Authentication failed - server needs restart")
            elif response.status_code == 404:
                print("⚠️ Batch not found (this may be normal)")
            else:
                print(f"⚠️ Unexpected response: {response.text[:200]}")
            
        except Exception as e:
            print(f"❌ Error testing batch status: {str(e)}")

def print_summary():
    """Print setup summary and next steps"""
    print("\n" + "=" * 60)
    print("📋 SETUP SUMMARY")
    print("=" * 60)
    print(f"🔑 API Key: {API_KEY}")
    print(f"🌐 Base URL: {API_BASE_URL}")
    print(f"📖 Documentation: {ENDPOINTS['docs']}")
    print("\n📌 Key Points:")
    print("   • All API endpoints require X-API-Key header")
    print("   • Enhanced batch endpoint: /api/v1/batch/enhanced")  
    print("   • Standard batch endpoint: /api/v1/batch/process")
    print("   • Single job endpoint: /api/v1/jobs/")
    print("   • Batch status endpoint: /api/v1/batch/{id}/status")
    
    print("\n🔧 If tests fail:")
    print("   1. Stop the FastAPI server")
    print("   2. Restart with: uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload")
    print("   3. Run this test script again")
    
    print("\n📚 Documentation files:")
    print("   • API_DOCUMENTATION.md - Complete API reference")
    print("   • GETTING_STARTED.md - Quick start guide")
    print("   • test_enhanced_batch.py - Test enhanced batch API")
    print("   • test_standard_batch.py - Test standard batch API")
    print("   • test_job_api.py - Test single job API")

async def main():
    """Run all tests"""
    print("🧪 PDF Processing API - Setup and Test")
    print("=" * 60)
    
    # Test server health
    if not await test_server_health():
        print("\n❌ Server is not accessible. Please start the server first.")
        return
    
    # Check available endpoints
    batch_endpoints, job_endpoints = await test_openapi_endpoints()
    
    # Test authentication
    await test_authentication()
    
    # Test APIs
    enhanced_batch_id = await test_enhanced_batch()
    standard_batch_id = await test_standard_batch()
    job_id = await test_job_processing()
    
    # Test status endpoint
    if enhanced_batch_id:
        await test_batch_status(enhanced_batch_id)
    elif standard_batch_id:
        await test_batch_status(standard_batch_id)
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    asyncio.run(main()) 