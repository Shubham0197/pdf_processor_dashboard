from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import uuid
import asyncio
import logging
import httpx
import json

from app.database import get_db, SessionLocal
from app.config import settings
from app.models.batch import BatchJob
from app.schemas.batch import BatchRequest, BatchResponse, BatchStatusResponse, EnhancedBatchRequest
from app.utils.auth import get_current_user
from app.utils.simple_auth import verify_api_key
from app.models.user import User
from app.services.pdf_service import process_pdf
from app.services.gemini_service import process_pdf_directly
from app.services.processing_service import process_document

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

async def send_webhook_notification(webhook_url: str, batch_id: str, results: dict, status: str):
    """Send results to webhook URL"""
    try:
        webhook_payload = {
            "batch_id": batch_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=webhook_payload)
            if response.status_code == 200:
                logger.info(f"✅ Webhook notification sent successfully for batch {batch_id}")
            else:
                logger.warning(f"⚠️ Webhook returned status {response.status_code} for batch {batch_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send webhook notification for batch {batch_id}: {str(e)}")

async def process_batch_job_with_real_pdf_processing(batch_id: uuid.UUID):
    """Background task that processes real PDF files with proper async context"""
    logger.info(f"🚀 Starting REAL PDF batch processing for batch_id: {batch_id}")
    
    try:
        # Use SessionLocal to maintain proper async context
        async with SessionLocal() as session:
            logger.info(f"✅ Created async session for batch {batch_id}")
            
            # Get batch information
            result = await session.execute(select(BatchJob).where(BatchJob.id == batch_id))
            batch = result.scalars().first()
            
            if not batch:
                logger.error(f"❌ Batch {batch_id} not found")
                return
            
            logger.info(f"📋 Found batch: {batch.batch_id} with {batch.total_files} files")
            
            # Update to processing status
            batch.status = "processing"
            await session.commit()
            logger.info(f"🔄 Updated batch status to processing")
            
            # Get the files to process
            files = batch.request_data.get("files", []) if batch.request_data else []
            options_data = batch.request_data.get("options", {}) if batch.request_data else {}
            
            # Convert options to dict if it's a Pydantic model
            if hasattr(options_data, 'dict'):
                options = options_data.dict()
            elif isinstance(options_data, dict):
                options = options_data
            else:
                options = {}
            
            logger.info(f"📁 Processing {len(files)} files with options: {options}")
            
            # Process files with REAL PDF processing
            processed_count = 0
            failed_count = 0
            
            for idx, file_request in enumerate(files):
                try:
                    file_url = file_request.get("url", "")
                    logger.info(f"🔍 Processing file {idx + 1}/{len(files)}: {file_url}")
                    
                    if file_url and file_url.startswith("http"):
                        # REAL PDF processing using the pdf_service
                        logger.info(f"📄 Starting real PDF processing for: {file_url}")
                        
                        try:
                            # Process the PDF using the existing PDF service
                            result = await process_pdf(file_url, session, options)
                            
                            logger.info(f"📊 PDF processing completed for {file_url}")
                            logger.debug(f"📊 Processing result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                            
                            # Check if processing was successful
                            if isinstance(result, dict) and "error" not in result:
                                processed_count += 1
                                logger.info(f"✅ Successfully processed {file_url}")
                                
                                # Log some details about what was extracted
                                if "metadata" in result:
                                    logger.info(f"📈 Extracted metadata for {file_url}")
                                if "references" in result:
                                    ref_count = len(result["references"]) if isinstance(result["references"], list) else 0
                                    logger.info(f"📚 Extracted {ref_count} references for {file_url}")
                                if "extracted_text" in result:
                                    text_length = len(result["extracted_text"]) if result["extracted_text"] else 0
                                    logger.info(f"📝 Extracted {text_length} characters of text for {file_url}")
                            else:
                                failed_count += 1
                                error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else "Processing failed"
                                logger.warning(f"⚠️ Processing failed for {file_url}: {error_msg}")
                                
                        except Exception as pdf_error:
                            failed_count += 1
                            logger.error(f"💥 Error in PDF processing for {file_url}: {str(pdf_error)}")
                            logger.exception("PDF processing error details:")
                    else:
                        failed_count += 1
                        logger.warning(f"⚠️ Invalid URL: {file_url}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Error processing file: {str(e)}")
                    logger.exception("File processing error details:")
            
            # Update final results
            batch.status = "completed"
            batch.processed_files = processed_count
            batch.failed_files = failed_count
            batch.completed_at = datetime.now()
            await session.commit()
            
            logger.info(f"🎉 Batch processing completed: {processed_count} processed, {failed_count} failed")
            
            # Log summary
            logger.info(f"📊 BATCH SUMMARY:")
            logger.info(f"   Total files: {batch.total_files}")
            logger.info(f"   Successfully processed: {processed_count}")
            logger.info(f"   Failed: {failed_count}")
            logger.info(f"   Options used: {options}")
            
    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in batch processing: {str(e)}")
        logger.exception("Full error details:")
        
        # Mark as failed
        try:
            async with SessionLocal() as session:
                result = await session.execute(select(BatchJob).where(BatchJob.id == batch_id))
                batch = result.scalars().first()
                if batch:
                    batch.status = "failed"
                    batch.completed_at = datetime.now()
                    await session.commit()
                    logger.info(f"📝 Marked batch {batch_id} as failed")
        except Exception as fail_error:
            logger.error(f"💀 Could not mark batch as failed: {fail_error}")

async def process_enhanced_batch_job(batch_id: uuid.UUID):
    """Background task that processes enhanced batch with webhook notifications using the NEW document framework"""
    logger.info(f"🚀 Starting enhanced batch processing for batch_id: {batch_id}")
    
    try:
        async with SessionLocal() as session:
            logger.info(f"✅ Created async session for batch {batch_id}")
            
            # Get batch information
            result = await session.execute(select(BatchJob).where(BatchJob.id == batch_id))
            batch = result.scalars().first()
            
            if not batch:
                logger.error(f"❌ Batch {batch_id} not found")
                return
            
            logger.info(f"📋 Found batch: {batch.batch_id} with {batch.total_files} files")
            
            # Update to processing status
            batch.status = "processing"
            await session.commit()
            logger.info(f"🔄 Updated batch status to processing")
            
            # Get the files to process
            files = batch.request_data.get("files", []) if batch.request_data else []
            options_data = batch.request_data.get("options", {}) if batch.request_data else {}
            webhook_url = batch.webhook_url
            
            # Convert options to dict if it's a Pydantic model
            if hasattr(options_data, 'dict'):
                options = options_data.dict()
            elif isinstance(options_data, dict):
                options = options_data
            else:
                options = {}
            
            logger.info(f"📁 Processing {len(files)} files with options: {options}")
            
            # Process files with results collection
            processed_count = 0
            failed_count = 0
            batch_results = []
            
            for idx, file_request in enumerate(files):
                file_result = {
                    "des_id": file_request.get("des_id"),
                    "entry_id": file_request.get("entry_id"),
                    "file_url": file_request.get("file_url", ""),
                    "original_metadata": file_request.get("metadata", {}),
                    "processing_status": "pending",
                    "extracted_data": {},
                    "error": None
                }
                
                try:
                    file_url = file_request.get("file_url", "")
                    logger.info(f"🔍 Processing file {idx + 1}/{len(files)}: {file_url}")
                    
                    if file_url and file_url.startswith("http"):
                        logger.info(f"📄 Starting enhanced document processing for: {file_url}")
                        
                        try:
                            # *** CRITICAL FIX: Use the new document framework instead of just processing PDFs ***
                            # This will properly save to the database with the new schema
                            processing_request, ai_results = await process_document(
                                db=session,
                                file_url=file_url,
                                options=options,
                                batch_id=batch_id,
                                webhook_url=webhook_url
                            )
                            
                            logger.info(f"📊 Document processing completed for {file_url}")
                            logger.info(f"🆔 Created processing request: {processing_request.id}")
                            logger.info(f"📝 Created {len(ai_results)} AI processing results")
                            
                            # Check if processing was successful
                            if processing_request.status == "completed":
                                processed_count += 1
                                file_result["processing_status"] = "completed"
                                
                                # Collect results from AI processing results
                                extracted_data = {}
                                for ai_result in ai_results:
                                    if ai_result.processing_type == "metadata" and ai_result.status == "completed":
                                        extracted_data["metadata"] = ai_result.processed_result
                                        logger.info(f"📈 Extracted metadata for {file_url}")
                                    elif ai_result.processing_type == "references" and ai_result.status == "completed":
                                        extracted_data["references"] = ai_result.processed_result
                                        ref_count = len(ai_result.processed_result) if isinstance(ai_result.processed_result, list) else 0
                                        logger.info(f"📚 Extracted {ref_count} references for {file_url}")
                                
                                file_result["extracted_data"] = extracted_data
                                logger.info(f"✅ Successfully processed {file_url} with new document framework")
                                
                            else:
                                failed_count += 1
                                error_msg = processing_request.error_message or "Processing failed"
                                file_result["processing_status"] = "failed"
                                file_result["error"] = error_msg
                                logger.warning(f"⚠️ Document processing failed for {file_url}: {error_msg}")
                                
                        except Exception as doc_error:
                            failed_count += 1
                            file_result["processing_status"] = "failed"
                            file_result["error"] = str(doc_error)
                            logger.error(f"💥 Error in document processing for {file_url}: {str(doc_error)}")
                    else:
                        failed_count += 1
                        file_result["processing_status"] = "failed"
                        file_result["error"] = f"Invalid URL: {file_url}"
                        logger.warning(f"⚠️ Invalid URL: {file_url}")
                        
                except Exception as e:
                    failed_count += 1
                    file_result["processing_status"] = "failed"
                    file_result["error"] = str(e)
                    logger.error(f"❌ Error processing file: {str(e)}")
                
                batch_results.append(file_result)
            
            # Update final results
            batch.status = "completed"
            batch.processed_files = processed_count
            batch.failed_files = failed_count
            batch.completed_at = datetime.now()
            await session.commit()
            
            logger.info(f"🎉 Enhanced batch processing completed: {processed_count} processed, {failed_count} failed")
            
            # Send webhook notification with results
            if webhook_url:
                logger.info(f"📤 Sending webhook notification to: {webhook_url}")
                await send_webhook_notification(
                    webhook_url,
                    batch.batch_id,
                    {
                        "total_files": batch.total_files,
                        "processed_files": processed_count,
                        "failed_files": failed_count,
                        "files": batch_results
                    },
                    "completed"
                )
            
            # Log summary
            logger.info(f"📊 ENHANCED BATCH SUMMARY (NEW DOCUMENT FRAMEWORK):")
            logger.info(f"   Batch ID: {batch.batch_id}")
            logger.info(f"   Total files: {batch.total_files}")
            logger.info(f"   Successfully processed: {processed_count}")
            logger.info(f"   Failed: {failed_count}")
            logger.info(f"   Options used: {options}")
            logger.info(f"   Webhook URL: {webhook_url}")
            logger.info(f"   ✅ All data saved to new document-centric database schema")
            
    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in enhanced batch processing: {str(e)}")
        logger.exception("Full error details:")
        
        # Mark as failed and send failure webhook
        try:
            async with SessionLocal() as session:
                result = await session.execute(select(BatchJob).where(BatchJob.id == batch_id))
                batch = result.scalars().first()
                if batch:
                    batch.status = "failed"
                    batch.completed_at = datetime.now()
                    await session.commit()
                    logger.info(f"📝 Marked batch {batch_id} as failed")
                    
                    # Send failure webhook notification
                    if batch.webhook_url:
                        await send_webhook_notification(
                            batch.webhook_url,
                            batch.batch_id,
                            {"error": str(e)},
                            "failed"
                        )
        except Exception as fail_error:
            logger.error(f"💀 Could not mark batch as failed: {fail_error}")

@router.post("/process", response_model=BatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_batch_job(
    request: BatchRequest,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Create a new batch job with real PDF processing
    """
    logger.info(f"🎯 Creating new batch job with {len(request.files) if request.files else 0} files")
    
    # Validate request
    if not request.files:
        logger.error("❌ No files provided for processing")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for processing"
        )
    
    # Generate batch ID
    batch_id_str = request.batch_id or str(uuid.uuid4())
    logger.info(f"🆔 Using batch ID: {batch_id_str}")
    
    # Log the files that will be processed
    logger.info(f"📋 Files to process:")
    for idx, file_req in enumerate(request.files):
        logger.info(f"   {idx + 1}. {file_req.url} (ID: {file_req.file_id})")
    
    logger.info(f"⚙️ Processing options: {request.options}")
    
    # Create batch job
    batch = BatchJob(
        batch_id=batch_id_str,
        webhook_url=request.webhook_url,
        total_files=len(request.files),
        request_data=request.dict(),
        status="pending"
    )
    
    try:
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        logger.info(f"💾 Created batch job in database with ID: {batch.id}")
        
        # Start background task with REAL PDF processing
        logger.info(f"🚀 Starting background task with REAL PDF processing")
        asyncio.create_task(process_batch_job_with_real_pdf_processing(batch.id))
        
        logger.info(f"✅ Batch job created successfully")
        
        return BatchResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            total_files=batch.total_files,
            created_at=batch.created_at
        )
        
    except Exception as e:
        logger.error(f"💥 Error creating batch job: {str(e)}")
        logger.exception("Full error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create batch job: {str(e)}"
        )

@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get status of a batch job
    """
    result = await db.execute(select(BatchJob).where(BatchJob.batch_id == batch_id))
    batch = result.scalars().first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job with ID {batch_id} not found"
        )
    
    return BatchStatusResponse(
        batch_id=batch.batch_id,
        status=batch.status,
        total_files=batch.total_files,
        processed_files=batch.processed_files,
        failed_files=batch.failed_files,
        created_at=batch.created_at,
        completed_at=batch.completed_at
    )

@router.post("/enhanced", response_model=BatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_enhanced_batch_job(
    request: EnhancedBatchRequest,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Create a new enhanced batch job with the specific JSON format
    """
    logger.info(f"🎯 Creating enhanced batch job with {len(request.files)} files")
    
    # Validate request
    if not request.files:
        logger.error("❌ No files provided for processing")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for processing"
        )
    
    logger.info(f"🆔 Using batch ID: {request.batch_id}")
    
    # Log the files that will be processed
    logger.info(f"📋 Files to process:")
    for idx, file_req in enumerate(request.files):
        logger.info(f"   {idx + 1}. {file_req.file_url} (des_id: {file_req.des_id}, entry_id: {file_req.entry_id})")
    
    logger.info(f"⚙️ Processing options: {request.options}")
    logger.info(f"🔗 Webhook URL: {request.webhook_url}")
    
    # Check if batch_id already exists
    existing_batch = await db.execute(select(BatchJob).where(BatchJob.batch_id == request.batch_id))
    if existing_batch.scalars().first():
        logger.error(f"❌ Batch ID {request.batch_id} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch with ID {request.batch_id} already exists"
        )
    
    # Create batch job
    batch = BatchJob(
        batch_id=request.batch_id,
        webhook_url=request.webhook_url,
        total_files=len(request.files),
        request_data=request.dict(),
        status="pending",
        source="enhanced_api"
    )
    
    try:
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        logger.info(f"💾 Created enhanced batch job in database with ID: {batch.id}")
        
        # Start background task with enhanced processing
        logger.info(f"🚀 Starting background task with enhanced PDF processing")
        asyncio.create_task(process_enhanced_batch_job(batch.id))
        
        logger.info(f"✅ Enhanced batch job created successfully")
        
        return BatchResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            total_files=batch.total_files,
            created_at=batch.created_at
        )
        
    except Exception as e:
        logger.error(f"💥 Error creating enhanced batch job: {str(e)}")
        logger.exception("Full error details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create enhanced batch job: {str(e)}"
        )
