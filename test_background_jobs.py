#!/usr/bin/env python3
"""
Test script for background job processing functionality
Tests immediate job creation response, progress tracking, and job completion flow.
"""
import asyncio
import time
import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://127.0.0.1:9000"
API_KEY = "pdf-processing-api-key-2024"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Test PDF URLs
TEST_PDF_URLS = [
    "https://arxiv.org/pdf/2301.07041.pdf",  # Small academic paper
    "https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/PDF32000_2008.pdf"  # PDF specification (larger)
]

def make_request(method: str, endpoint: str, data: Dict[Any, Any] = None) -> requests.Response:
    """Make an API request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    
    if method.upper() == "GET":
        response = requests.get(url, headers=HEADERS)
    elif method.upper() == "POST":
        response = requests.post(url, headers=HEADERS, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return response

def test_immediate_job_creation():
    """Test that job creation returns immediately"""
    print("🧪 Testing immediate job creation response...")
    
    job_data = {
        "file_url": TEST_PDF_URLS[0],
        "file_name": "test_paper.pdf",
        "complete_references": False
    }
    
    start_time = time.time()
    response = make_request("POST", "/api/v1/jobs/", job_data)
    response_time = time.time() - start_time
    
    print(f"⏱️  Response time: {response_time:.3f} seconds")
    
    if response.status_code == 202:
        print("✅ Job creation returned immediately (status 202)")
        job_response = response.json()
        print(f"📋 Job ID: {job_response['job_id']}")
        print(f"📊 Initial progress: {job_response.get('progress_percentage', 0)}%")
        print(f"🔄 Initial status: {job_response['status']}")
        
        if response_time < 1.0:
            print("✅ Response time is acceptable (< 1 second)")
        else:
            print("⚠️  Response time is slower than expected (>= 1 second)")
        
        return job_response['job_id']
    else:
        print(f"❌ Job creation failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_progress_tracking(job_id: str):
    """Test progress tracking for a job"""
    print(f"\n🧪 Testing progress tracking for job {job_id}...")
    
    max_checks = 30  # Maximum number of progress checks
    check_interval = 2  # Seconds between checks
    
    for i in range(max_checks):
        response = make_request("GET", f"/api/v1/jobs/{job_id}/progress")
        
        if response.status_code == 200:
            progress_data = response.json()
            status = progress_data['status']
            progress = progress_data['progress_percentage']
            worker_id = progress_data.get('worker_id', 'N/A')
            estimated_completion = progress_data.get('estimated_completion')
            
            print(f"📊 Check {i+1}: {status} - {progress}% (Worker: {worker_id})")
            
            if estimated_completion:
                print(f"⏰ Estimated completion: {estimated_completion}")
            
            # Check if job is complete
            if status in ["completed", "failed"]:
                if status == "completed":
                    print("✅ Job completed successfully!")
                else:
                    print(f"❌ Job failed: {progress_data.get('error_message', 'Unknown error')}")
                return progress_data
            
            # Wait before next check
            time.sleep(check_interval)
        else:
            print(f"❌ Progress check failed: {response.status_code}")
            print(f"Response: {response.text}")
            break
    
    print("⚠️  Job did not complete within expected time")
    return None

def test_final_job_status(job_id: str):
    """Test final job status and results"""
    print(f"\n🧪 Testing final job status for job {job_id}...")
    
    response = make_request("GET", f"/api/v1/jobs/{job_id}")
    
    if response.status_code == 200:
        job_result = response.json()
        status = job_result['status']
        
        print(f"🔄 Final status: {status}")
        print(f"📊 Final progress: {job_result.get('progress_percentage', 0)}%")
        print(f"⏱️  Processing time: {job_result.get('processing_time', 'N/A')} ms")
        print(f"👤 Worker ID: {job_result.get('worker_id', 'N/A')}")
        
        if status == "completed":
            print("✅ Job completed successfully")
            
            # Check if metadata was extracted
            metadata = job_result.get('doc_metadata')
            if metadata:
                title = metadata.get('title', 'N/A')
                authors = metadata.get('authors', [])
                print(f"📄 Title: {title}")
                print(f"👥 Authors: {len(authors) if isinstance(authors, list) else 'N/A'}")
            
            # Check if references were extracted
            references = job_result.get('references')
            if references and isinstance(references, list):
                print(f"📚 References extracted: {len(references)}")
            
            return True
        else:
            error_msg = job_result.get('error', 'Unknown error')
            print(f"❌ Job failed: {error_msg}")
            return False
    else:
        print(f"❌ Failed to get job status: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_concurrent_jobs():
    """Test multiple concurrent jobs"""
    print("\n🧪 Testing concurrent job processing...")
    
    job_ids = []
    
    # Create multiple jobs
    for i, pdf_url in enumerate(TEST_PDF_URLS):
        job_data = {
            "file_url": pdf_url,
            "file_name": f"test_paper_{i+1}.pdf",
            "complete_references": False
        }
        
        response = make_request("POST", "/api/v1/jobs/", job_data)
        
        if response.status_code == 202:
            job_response = response.json()
            job_id = job_response['job_id']
            job_ids.append(job_id)
            print(f"✅ Created job {i+1}: {job_id}")
        else:
            print(f"❌ Failed to create job {i+1}: {response.status_code}")
    
    if not job_ids:
        print("❌ No jobs created for concurrent test")
        return False
    
    print(f"🔄 Monitoring {len(job_ids)} concurrent jobs...")
    
    # Monitor all jobs until completion
    completed_jobs = set()
    max_checks = 30
    
    for check in range(max_checks):
        print(f"\n📊 Concurrent check {check+1}:")
        
        for job_id in job_ids:
            if job_id in completed_jobs:
                continue
                
            response = make_request("GET", f"/api/v1/jobs/{job_id}/progress")
            
            if response.status_code == 200:
                progress_data = response.json()
                status = progress_data['status']
                progress = progress_data['progress_percentage']
                
                print(f"  Job {job_id}: {status} - {progress}%")
                
                if status in ["completed", "failed"]:
                    completed_jobs.add(job_id)
        
        # Check if all jobs are complete
        if len(completed_jobs) == len(job_ids):
            print("✅ All concurrent jobs completed!")
            break
        
        time.sleep(3)
    
    # Final status check
    successful_jobs = 0
    for job_id in job_ids:
        response = make_request("GET", f"/api/v1/jobs/{job_id}")
        if response.status_code == 200:
            job_result = response.json()
            if job_result['status'] == "completed":
                successful_jobs += 1
    
    print(f"\n📈 Concurrent test results: {successful_jobs}/{len(job_ids)} jobs completed successfully")
    return successful_jobs == len(job_ids)

def test_error_handling():
    """Test error handling with invalid PDF URL"""
    print("\n🧪 Testing error handling...")
    
    job_data = {
        "file_url": "https://invalid-url-that-does-not-exist.com/fake.pdf",
        "file_name": "invalid.pdf",
        "complete_references": False
    }
    
    response = make_request("POST", "/api/v1/jobs/", job_data)
    
    if response.status_code == 202:
        job_response = response.json()
        job_id = job_response['job_id']
        print(f"📋 Created error test job: {job_id}")
        
        # Wait for processing to fail
        time.sleep(10)
        
        # Check final status
        response = make_request("GET", f"/api/v1/jobs/{job_id}")
        
        if response.status_code == 200:
            job_result = response.json()
            status = job_result['status']
            
            if status == "failed":
                error_msg = job_result.get('error', 'No error message')
                print(f"✅ Error handling works correctly")
                print(f"❌ Error message: {error_msg}")
                return True
            else:
                print(f"⚠️  Expected 'failed' status, got: {status}")
                return False
        else:
            print(f"❌ Failed to check error job status: {response.status_code}")
            return False
    else:
        print(f"❌ Failed to create error test job: {response.status_code}")
        return False

def main():
    """Run all background job tests"""
    print("🚀 Starting Background Job Processing Tests")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Immediate job creation
    job_id = test_immediate_job_creation()
    test_results.append(("Immediate Job Creation", job_id is not None))
    
    if job_id:
        # Test 2: Progress tracking
        final_progress = test_progress_tracking(job_id)
        test_results.append(("Progress Tracking", final_progress is not None))
        
        # Test 3: Final job status
        final_success = test_final_job_status(job_id)
        test_results.append(("Final Job Status", final_success))
    
    # Test 4: Concurrent jobs
    concurrent_success = test_concurrent_jobs()
    test_results.append(("Concurrent Jobs", concurrent_success))
    
    # Test 5: Error handling
    error_success = test_error_handling()
    test_results.append(("Error Handling", error_success))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, passed in test_results if passed)
    
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Background job processing is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main()) 