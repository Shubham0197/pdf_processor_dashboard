import os
import tempfile
import time
import asyncio
import httpx
import fitz  # PyMuPDF
from sqlalchemy.ext.asyncio import AsyncSession
# from app.services.gemini_service import extract_metadata_with_gemini, extract_references_with_gemini
from app.schemas.gemini_schemas import PDFProcessingResult, MetadataResponse, Reference

async def download_pdf(url: str, timeout: int = 30):
    """Download PDF from URL to a temporary file"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(response.content)
                return temp_file.name
    except Exception as e:
        print(f"Error downloading PDF from {url}: {e}")
        raise

async def extract_text_from_pdf(pdf_path: str):
    """Extract text from PDF file with improved handling"""
    try:
        text = ""
        # Open the PDF file
        with fitz.open(pdf_path) as doc:
            print(f"PDF has {len(doc)} pages")
            
            # Iterate through each page
            for page_num, page in enumerate(doc):
                # Get text with better formatting preservation
                page_text = page.get_text("text")
                
                # Add page number for reference
                text += f"\n\n--- Page {page_num + 1} ---\n\n"
                text += page_text
                
                # Log progress for large documents
                if page_num % 10 == 0 and page_num > 0:
                    print(f"Processed {page_num} pages of PDF")
        
        print(f"Extracted {len(text)} characters of text from PDF")
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise
    finally:
        # Clean up the temporary file
        try:
            os.unlink(pdf_path)
        except:
            pass

async def process_pdf(file_url: str, db: AsyncSession, options=None):
    """Process a PDF file and extract metadata and references"""
    start_time = time.time()
    
    if options is None:
        options = {
            "extract_metadata": True,
            "extract_references": True,
            "extract_full_text": False
        }
    
    try:
        # Download the PDF
        pdf_path = await download_pdf(file_url)
        
        # Initialize result with file URL
        result = {
            "file_url": file_url,
        }
        
        # Use direct PDF processing with Gemini if both metadata and references are requested
        if options.get("extract_metadata", True) or options.get("extract_references", True):
            try:
                # Process the PDF directly with Gemini
                from app.services.gemini_service import process_pdf_directly
                
                print(f"Processing PDF directly with Gemini API: {pdf_path}")
                gemini_result = await process_pdf_directly(
                    pdf_path=pdf_path,
                    db=db,
                    extract_metadata=options.get("extract_metadata", True),
                    extract_references=options.get("extract_references", True),
                    complete_references=options.get("complete_references", False)
                )
                
                # Add the results to our response
                if "metadata" in gemini_result:
                    result["metadata"] = gemini_result["metadata"]
                
                if "references" in gemini_result:
                    result["references"] = gemini_result["references"]
                    
                if "error" in gemini_result:
                    print(f"Error in direct PDF processing: {gemini_result['error']}")
                    # If there was an error, fall back to text extraction
                    if "metadata" not in result and options.get("extract_metadata", True):
                        print("Falling back to text extraction for metadata")
                        # pdf_text = await extract_text_from_pdf(pdf_path)
                        # metadata = await extract_metadata_with_gemini(pdf_text, db)
                        # result["metadata"] = metadata
                        
                    if "references" not in result and options.get("extract_references", True):
                        print("Falling back to text extraction for references")
                        # pdf_text = await extract_text_from_pdf(pdf_path)
                        # references = await extract_references_with_gemini(pdf_text, db)
                        # result["references"] = references
            except Exception as e:
                print(f"Error in direct PDF processing, falling back to text extraction: {e}")
                # Fall back to text extraction method
                pdf_text = await extract_text_from_pdf(pdf_path)
                
                # Add extracted text if requested
                if options.get("extract_full_text", False):
                    result["extracted_text"] = pdf_text
                else:
                    result["extracted_text"] = None
                
                # Extract metadata if requested
                # if options.get("extract_metadata", True):
                #     try:
                #         # metadata = await extract_metadata_with_gemini(pdf_text, db)
                #         # result["metadata"] = metadata
                #     except Exception as metadata_error:
                #         print(f"Error extracting metadata: {metadata_error}")
                #         result["metadata"] = MetadataResponse(
                #             error=f"Error extracting metadata: {str(metadata_error)}"
                #         ).dict(exclude_none=True)
                
                # Extract references if requested
                # if options.get("extract_references", True):
                #     try:
                #         references = await extract_references_with_gemini(pdf_text, db)
                #         result["references"] = references
                #     except Exception as references_error:
                #         print(f"Error extracting references: {references_error}")
                #         result["references"] = [Reference(
                #             text="Error extracting references",
                #             citation_type="error",
                #             error=f"Error extracting references: {str(references_error)}"
                #         ).dict(exclude_none=True)]
        else:
            # If neither metadata nor references are requested, just extract text
            pdf_text = await extract_text_from_pdf(pdf_path)
            if options.get("extract_full_text", False):
                result["extracted_text"] = pdf_text
            else:
                result["extracted_text"] = None
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)  # in milliseconds
        result["processing_time"] = processing_time
        
        # Validate the result with Pydantic model
        try:
            validated_result = PDFProcessingResult(**result)
            return validated_result.dict(exclude_none=True)
        except Exception as e:
            print(f"Error validating result: {e}")
            # Return the original result if validation fails
            return result
    except Exception as e:
        # Calculate processing time even for errors
        processing_time = int((time.time() - start_time) * 1000)
        
        # Use Pydantic model for error response
        try:
            error_result = PDFProcessingResult(
                file_url=file_url,
                error=str(e),
                processing_time=processing_time
            )
            return error_result.dict(exclude_none=True)
        except Exception as validation_error:
            print(f"Error creating error response: {validation_error}")
            # Fallback to simple dict if Pydantic model fails
            return {
                "file_url": file_url,
                "error": str(e),
                "processing_time": processing_time
            }
