import os
import json
import re
import io
import base64
import pathlib
from google import genai
from google.genai import client, types
from opik import track
from opik.integrations.genai import track_genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.api_key_service import get_active_key_by_type
from app.schemas.gemini_schemas import MetadataResponse, ReferencesResponse, Reference

async def configure_gemini(db: AsyncSession):
    """Configure Gemini API with key from database"""
    try:
        api_key = await get_active_key_by_type(db, "gemini")
        if api_key:
            return True
        else:
            print("No active Gemini API key found in database")
            return False
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        return False

async def process_pdf_directly(pdf_path: str, db: AsyncSession, extract_metadata=True, extract_references=True, complete_references=False):
    """Process a PDF file directly using Google Gemini API without text extraction"""
    # Ensure Gemini is configured
    if not await configure_gemini(db):
        return {"error": "Failed to configure Gemini API. Please check your API key."}
        
    try:
        try:
            api_key = await get_active_key_by_type(db, "gemini")
            client = genai.Client(api_key=api_key)
            # client = genai.Client(api_key="AIzaSyC_b7uQQUYVBargbN-YNNveg9qArbe4pHk")
            # models = client.list_models()
            # print("Available Gemini models for direct PDF processing:")
            # for model in models:
            #     print(f"- {model.name}")
            
            # For PDF processing, we need a model that supports multimodal input
            # gemini-2.0-flash-lite is known to support PDFs
            model_name = "gemini-2.0-flash-lite"
            print(f"Using gemini-2.0-flash-lite for PDF processing which supports multimodal input")
        except Exception as e:
            print(f"Error listing models: {e}")
            # Fallback to gemini-2.0-flash-lite
            model_name = "gemini-2.0-flash-lite"
            print(f"Error occurred, using default model: {model_name}")
        
        print(f"Creating GenerativeModel with name: {model_name}")
        # model = client.get_model(model_name)
        
        # Check if the file exists and get its size
        path = pathlib.Path(pdf_path)
        if not path.exists():
            return {
                "error": f"PDF file not found at {pdf_path}"
            }
            
        size = path.stat().st_size
        print(f"PDF file size: {size / (1024 * 1024):.2f} MB")
        
        results = {}
        # Extract metadata if requested
        if extract_metadata:
            metadata_prompt = """
Extract the following metadata from this academic article:
- Title
- Authors (with detailed information)
- Abstract
- Keywords
- Journal name
- Volume and issue numbers
- Year of publication
- DOI
- Pages

Return the information in a structured JSON format with these exact keys:
"title", "authors", "abstract", "keywords", "journal", "volume", "issue", "year", "doi", "pages"

For authors, use an array of objects with the following properties (if available):
- "name" (full name)
- "first_name" (include middle name here if present, e.g., for 'John Michael Smith', first_name = 'John Michael')
- "last_name"
- "email"
- "mobile_no"
- "designation" (job title or role, e.g., "Project Assistant-II", "Professor", "Research Scholar")
- "institution" (name of the institution only, e.g., "CSIR - National Environmental Engineering Research Institute" or e.g., "Madras Institute of Technology")
- "parent_institution" (The parent or umbrella institution/university, if present (e.g., "Anna University" for "Madras Institute of Technology, Anna University").)
- "orcid_id"
- "department" (store the department verbatim as it appears, e.g., "Department of Technology")
- "address" (city, state, country of the institution)
- "affiliation" (affiliation of the author)
- "city"
- "state"
- "country"
- "pincode"

IMPORTANT: 
- If an author has a middle name, include it in the "first_name" field along with the first name.
- For the "department" field, always store the department name exactly as it appears in the article, without splitting or abbreviating (e.g., "Department of Technology" should be stored as "Department of Technology").

IMPORTANT: Separate the designation from the institution name. For example, if the affiliation is "Project Assistant-II, CSIR - National Environmental Engineering Research Institute, Nagpur-440020 (India)", then:
- designation = "Project Assistant-II"
- institution = "CSIR - National Environmental Engineering Research Institute"
- address = "Nagpur-440020, India"
- city = "Nagpur"
- state = "Maharashtra"
- country = "India"
- pincode = "440020"

IMPORTANT: If you cannot extract some information, use null or empty arrays as appropriate. Always return valid JSON.
"""
            
            try:
                # Process the PDF directly
                if size < 20 * 1024 * 1024:  # Less than 20MB
                    pdf_bytes = path.read_bytes()
                    print("Direct PDF processing API format has changed, falling back to text extraction")
                    contents = [
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                        metadata_prompt
                    ]
                    print("Sending PDF directly to Gemini API for metadata extraction")
                    print("📨 Sending to Gemini model...")
                    response = client.models.generate_content(model=model_name, contents=contents)
                    
                    # Parse the metadata response
                    metadata = await parse_gemini_response(response, is_metadata=True)
                    results["metadata"] = metadata
                else:
                    # print("PDF file too large for direct processing, falling back to text extraction")
                    # # Fall back to text extraction method
                    # from app.services.pdf_service import extract_text_from_pdf
                    # pdf_text = await extract_text_from_pdf(pdf_path)
                    pdf_io = io.BytesIO(path.read_bytes())
                    uploaded_file = client.files.upload(
                        file=pdf_io,
                        config={"mime_type": "application/pdf"}
                    )
                    contents = [uploaded_file, instruction]
                    response = client.models.generate_content(model=model_name, contents=contents)
                    metadata = await parse_gemini_response(response, is_metadata=True)
                    results["metadata"] = metadata
            except Exception as e:
                print(f"Error extracting metadata directly from PDF: {e}")
                results["metadata"] = MetadataResponse(
                    error=f"Failed to extract metadata: {str(e)}"
                ).dict(exclude_none=True)
        
        # Extract references if requested
        if extract_references:
            references_prompt = """
            Extract all references/citations from this academic article.
            For each reference, provide the following information in a structured format:
            
            1. Full reference text (exactly as it appears in the document as key "text")
            2. Citation type (journal article, book, conference paper, website/URL, etc.)
            3. Authors (list of all authors)
            4. Title of the referenced work
            5. Year of publication
            6. Journal name (if it's a journal article)
            7. Conference name (if it's a conference proceeding)
            8. Volume and issue numbers (if applicable)
            9. Page numbers (if available)
            10. DOI (if available)
            11. URL (if it's a web resource)
            12. Publisher (if it's a book)
            13. Citation position (e.g., reference number in the bibliography)
            
            IMPORTANT: If you don't find any references in the text, look carefully for numbered citations, bracketed citations, or any list of sources at the end of the document. References might be formatted in various ways.

            IMPORTANT:
            - If the reference is a journal article, set "citation_type" to "journal" and fill the "journal" field with the journal name. Leave "conference" empty or null.
            - If the reference is a conference proceeding, set "citation_type" to "conference proceedings" and fill the "conference" field with the conference name. Leave "journal" empty or null.
            - For other types, use the appropriate "citation_type" and fill only the relevant fields.
            
            EXTREMELY IMPORTANT - CITATION CONTINUITY ACROSS PAGES:
            1. You MUST carefully check for citations that span across multiple pages or columns.
            2. A citation is likely continuing from the previous page if:
               - It starts without a citation number but is in the references section
               - It starts mid-sentence or with lowercase letters
               - It starts with "and" or other conjunctions
               - It lacks author information but contains publication details
               - The previous page ends with an incomplete citation
            3. NEVER create two separate citations when one citation spans across pages.
            4. ALWAYS join text that belongs to the same citation, even if it appears on different pages.
            5. IMPORTANT EXAMPLE: If you see "19. Zeidan, F.Y.; San Andres, L. & Vance, J.M. Design and" at the bottom of one page and "application of squeeze film dampers in rotating machinery. Proceedings of the Twenty-Fifth Turbomachinery Symposium, 1996." at the top of the next page, this is ONE citation, not two.
            
            
            For example, for the reference "1. Akram, f., O. Ilyas and B. A. K. Prusty (2015). International Journal of Engineering Technology Science and Research 2(10): 1-11. /n doi: 10.14429/dsj.60.57", provide:
            - text: "1. Akram, f., O. Ilyas and B. A. K. Prusty (2015). International Journal of Engineering Technology Science and Research 2(10): 1-11."
            - citation_type: "journal article"
            - authors: ["Akram, F.", "Ilyas, O.", "Prusty, B.A.K."]
            - title: (extract if present)
            - year: "2015"
            - journal: "International Journal of Engineering Technology Science and Research"
            - volume: "2"
            - issue: "10"
            - pages: "1-11"
            - doi: "10.14429/dsj.60.57"
            - url: (extract if present)
            - publisher: (extract if present)
            - citation_position: "1"
            
            Return the information in a structured JSON format as an array of reference objects.
            If you absolutely cannot find any references, return an empty array but explain why in a comment.
            """
            
            try:
                # Process the PDF directly
                if size < 20 * 1024 * 1024:  # Less than 20MB
                    pdf_bytes = path.read_bytes()
                    
                    if not complete_references:
                        # Regular extraction - single request
                        contents = [
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                            references_prompt
                        ]
                        print("Sending PDF directly to Gemini API for references extraction")
                        print("📨 Sending to Gemini model...")
                        response = client.models.generate_content(model=model_name, contents=contents)
                        
                        # Parse the references response
                        references = await parse_gemini_response(response, is_metadata=False)
                        results["references"] = references
                    else:
                        # Complete references extraction with multiple requests if needed
                        print("Using complete references extraction mode - handling large reference lists")
                        
                        # Initial request for references
                        initial_prompt = """
            Extract all references/citations from this academic article.
            For each reference, provide the following information in a structured format:
            
            1. Full reference text (exactly as it appears in the document as key "text")
            2. Citation type (journal article, book, conference paper, website/URL, etc.)
            3. Authors (list of all authors)
            4. Title of the referenced work
            5. Year of publication
            6. Journal name (if it's a journal article)
            7. Conference name (if it's a conference proceeding)
            8. Volume and issue numbers (if applicable)
            9. Page numbers (if available)
            10. DOI (if available)
            11. URL (if it's a web resource)
            12. Publisher (if it's a book)
            13. Citation position (e.g., reference number in the bibliography)
            
            IMPORTANT: If you don't find any references in the text, look carefully for numbered citations, bracketed citations, or any list of sources at the end of the document. References might be formatted in various ways.

            IMPORTANT:
            - If the reference is a journal article, set "citation_type" to "journal" and fill the "journal" field with the journal name. Leave "conference" empty or null.
            - If the reference is a conference proceeding, set "citation_type" to "conference proceedings" and fill the "conference" field with the conference name. Leave "journal" empty or null.
            - For other types, use the appropriate "citation_type" and fill only the relevant fields.
            
            EXTREMELY IMPORTANT - CITATION CONTINUITY ACROSS PAGES:
            1. You MUST carefully check for citations that span across multiple pages or columns.
            2. A citation is likely continuing from the previous page if:
               - It starts without a citation number but is in the references section
               - It starts mid-sentence or with lowercase letters
               - It starts with "and" or other conjunctions
               - It lacks author information but contains publication details
               - The previous page ends with an incomplete citation
            3. NEVER create two separate citations when one citation spans across pages.
            4. ALWAYS join text that belongs to the same citation, even if it appears on different pages.
            5. IMPORTANT EXAMPLE: If you see "19. Zeidan, F.Y.; San Andres, L. & Vance, J.M. Design and" at the bottom of one page and "application of squeeze film dampers in rotating machinery. Proceedings of the Twenty-Fifth Turbomachinery Symposium, 1996." at the top of the next page, this is ONE citation, not two.
            
            
            For example, for the reference "1. Akram, f., O. Ilyas and B. A. K. Prusty (2015). International Journal of Engineering Technology Science and Research 2(10): 1-11. /n doi: 10.14429/dsj.60.57", provide:
            - text: "1. Akram, f., O. Ilyas and B. A. K. Prusty (2015). International Journal of Engineering Technology Science and Research 2(10): 1-11."
            - citation_type: "journal article"
            - authors: ["Akram, F.", "Ilyas, O.", "Prusty, B.A.K."]
            - title: (extract if present)
            - year: "2015"
            - journal: "International Journal of Engineering Technology Science and Research"
            - volume: "2"
            - issue: "10"
            - pages: "1-11"
            - doi: "10.14429/dsj.60.57"
            - url: (extract if present)
            - publisher: (extract if present)
            - citation_position: "1"
            
            Return the information in a structured JSON format as an array of reference objects.
            If you absolutely cannot find any references, return an empty array but explain why in a comment.
            """
                        
                        contents = [
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                            initial_prompt
                        ]
                        print("📨 Sending initial request to Gemini model for references...")
                        response = client.models.generate_content(model=model_name, contents=contents)
                        
                        # Parse the initial response
                        all_references = []
                        initial_results = await parse_gemini_response(response, is_metadata=False)
                        
                        # Parse the response structure
                        # The response could be either a list of references or a dict with metadata and references
                        total_refs = 0
                        extracted_count = 0
                        references_list = []
                        has_more = False
                        
                        # Handle the case where we get a dictionary with metadata
                        if isinstance(initial_results, dict):
                            # Get metadata about total references from the top-level dictionary
                            total_refs = initial_results.get("total_references", 0)
                            extracted_count = initial_results.get("extracted_count", 0)
                            has_more = initial_results.get("has_more", False)
                            print(f"Metadata from response: total_refs={total_refs}, extracted_count={extracted_count}, has_more={has_more}")
                            
                            # Check if there's a references key containing the actual references
                            if "references" in initial_results and isinstance(initial_results["references"], list):
                                references_list = initial_results["references"]
                                print(f"Found {len(references_list)} references in 'references' key")
                                all_references.extend(references_list)
                            else:
                                print("Warning: No valid references list found in the dictionary response")
                        # Handle the case where we get a list of references directly
                        elif isinstance(initial_results, list):
                            all_references.extend(initial_results)
                            extracted_count = len(initial_results)
                            print(f"Received a list of {extracted_count} references directly")
                            
                            # Try to find metadata about total references in the first item
                            if len(initial_results) > 0 and isinstance(initial_results[0], dict):
                                if "total_references" in initial_results[0]:
                                    total_refs = initial_results[0].get("total_references", 0)
                                    print(f"Found total_references={total_refs} in first reference item")
                                if "has_more" in initial_results[0]:
                                    has_more = initial_results[0].get("has_more", False)
                                    print(f"Found has_more={has_more} in first reference item")
                        
                        # Force has_more to true if we know we have more references based on total_refs
                        if total_refs > 0 and len(all_references) < total_refs:
                            has_more = True
                            print(f"Setting has_more=True because we have {len(all_references)} of {total_refs} total references")
                                    
                        print(f"Initial extraction: {len(all_references)} references, total expected: {total_refs}, has_more: {has_more}")
                        
                        # Calculate how many batches we'll need (25 references per batch)
                        # Add a buffer of 2 extra requests just to be safe
                        required_batches = 1  # We already made the first request
                        if total_refs > 0:
                            required_batches += (total_refs - len(all_references) + 24) // 25
                            print(f"Based on total_refs={total_refs}, we need approximately {required_batches} more batches")
                        elif has_more:
                            # If we don't know the total but has_more is true, we'll use a default limit
                            required_batches = 10
                            print(f"Unknown total references but has_more=True, will try up to {required_batches} batches")
                        
                        # Cap the maximum number of attempts to avoid excessive API calls
                        max_attempts = min(required_batches, 15)  # Never make more than 15 requests total
                        current_attempt = 0
                        
                        # Continue making requests until we have all references or reach our limit
                        while (has_more or (total_refs > 0 and len(all_references) < total_refs)) and current_attempt < max_attempts:
                            current_attempt += 1
                            current_count = len(all_references)
                            
                            # Prepare follow-up request for the next batch of references
                            followup_prompt = f"""
                            Continue extracting references from the academic article.
                            You have already extracted {current_count} references out of approximately {total_refs} total references.
                            
                            Please continue from reference #{current_count + 1} and extract exactly 25 more references.
                            Use the same format as before, providing the following for each reference:
                            1. Full reference text (exactly as it appears in the document)
                            2. Citation type (journal, proceedings, book, website/URL, etc.)
                            3. Authors (list of all authors)
                            4. Title of the referenced work
                            5. Year of publication
                            6. Journal name (if it's a journal article)
                            7. Conference name (if it's a conference proceeding)
                            8. Volume and issue numbers (if applicable)
                            9. Page numbers (if available)
                            10. DOI (if available)
                            11. URL (if it's a web resource)
                            12. Publisher (if it's a book)
                            13. Citation position (e.g., reference number in the bibliography)
                            
                            Return ONLY the array of reference objects in JSON format, without any introduction or explanation.
                            If there are no more references to extract, return an empty array [].
                            """
                            
                            contents = [
                                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                                followup_prompt
                            ]
                            print(f"📨 Sending follow-up request #{current_attempt} to Gemini model for additional references...")
                            response = client.models.generate_content(model=model_name, contents=contents)
                            
                            # Parse the follow-up response
                            followup_results = await parse_gemini_response(response, is_metadata=False)
                            
                            # Process the follow-up results
                            new_references = []
                            if isinstance(followup_results, dict) and "references" in followup_results:
                                new_references = followup_results["references"]
                                has_more = followup_results.get("has_more", False)
                                # Update total_refs if it's available and larger than our current value
                                if "total_references" in followup_results and followup_results["total_references"] > total_refs:
                                    total_refs = followup_results["total_references"]
                                    print(f"Updated total_references to {total_refs} from follow-up response")
                            elif isinstance(followup_results, list):
                                new_references = followup_results
                                
                            # Force has_more to true if we know we have more references based on total_refs
                            if total_refs > 0 and (len(all_references) + len(new_references)) < total_refs:
                                has_more = True
                                print(f"Setting has_more=True because we still need more references to reach {total_refs}")
                                
                            # Add new references to our collection
                            if isinstance(new_references, list):
                                all_references.extend(new_references)
                                print(f"Batch #{current_attempt}: Got {len(new_references)} more references, total now: {len(all_references)}")
                                
                            # Check if we've received any new references
                            if len(new_references) == 0:
                                print("No new references received, stopping further requests")
                                break
                            # Check if we're making progress
                            if len(all_references) == current_count:
                                print("No new references added to the total, stopping further requests")
                                break
                            # Check if we've reached or exceeded the total count
                            if total_refs > 0 and len(all_references) >= total_refs:
                                print(f"Reached total reference count ({total_refs}), stopping further requests")
                                break
                        
                        print(f"Total references extracted: {len(all_references)}")
                        results["references"] = all_references
                else:
                    pdf_io = io.BytesIO(path.read_bytes())
                    uploaded_file = client.files.upload(
                        file=pdf_io,
                        config={"mime_type": "application/pdf"}
                    )
                    contents = [uploaded_file, references_prompt]
                    print("Sending PDF directly to Gemini API for references extraction")
                    print("📨 Sending to Gemini model...")
                    response = client.models.generate_content(model=model_name, contents=contents)
                    references = await parse_gemini_response(response, is_metadata=False)
                    results["references"] = references
            except Exception as e:
                print(f"Error extracting references directly from PDF: {e}")
                results["references"] = [Reference(
                    text="Error extracting references",
                    citation_type="error",
                    error=f"Failed to extract references: {str(e)}"
                ).dict(exclude_none=True)]
        
        return results
    except Exception as e:
        print(f"Error processing PDF directly: {e}")
        return {"error": f"Error processing PDF: {str(e)}"}

async def parse_gemini_response(response, is_metadata=True):
    """Parse the response from Gemini API"""
    try:
        # Extract JSON part from response
        text = response.text
        print(f"Raw response from Gemini: {text[:500]}..." if len(text) > 500 else text)
        
        # Try different patterns to extract JSON
        json_str = None
        
        # Pattern 1: Markdown code block
        json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            print(f"Extracted JSON from markdown code block: {json_str[:200]}..." if len(json_str) > 200 else json_str)
        
        # Pattern 2: Just the JSON object or array
        if not json_str:
            if is_metadata:
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            else:
                json_match = re.search(r'(\[.*\])', text, re.DOTALL)
                
            if json_match:
                json_str = json_match.group(1)
                print(f"Extracted JSON object/array: {json_str[:200]}..." if len(json_str) > 200 else json_str)
        
        # Pattern 3: Look for any JSON-like structure
        if not json_str:
            if is_metadata:
                # Look for any text between { and } that might be JSON
                start_idx = text.find('{')
                if start_idx >= 0:
                    # Find the matching closing brace
                    brace_count = 1
                    for i in range(start_idx + 1, len(text)):
                        if text[i] == '{':
                            brace_count += 1
                        elif text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = text[start_idx:i+1]
                                print(f"Extracted JSON by brace matching: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                                break
            else:
                # Look for any text between [ and ] that might be JSON
                start_idx = text.find('[')
                if start_idx >= 0:
                    # Find the matching closing bracket
                    bracket_count = 1
                    for i in range(start_idx + 1, len(text)):
                        if text[i] == '[':
                            bracket_count += 1
                        elif text[i] == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                json_str = text[start_idx:i+1]
                                print(f"Extracted JSON by bracket matching: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                                break
        
        # If all else fails, use the raw text
        if not json_str:
            json_str = text
            print(f"Using raw text as JSON (last resort): {json_str[:200]}..." if len(json_str) > 200 else json_str)
        
        # Clean and parse JSON
        try:
            # First attempt to parse as is
            parsed_json = json.loads(json_str)
            print(f"Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            
            # Clean up control characters and invalid JSON characters
            # Replace common problematic characters
            cleaned_json = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', json_str)
            
            try:
                parsed_json = json.loads(cleaned_json)
                print(f"Successfully parsed JSON after cleaning control characters")
            except json.JSONDecodeError:
                # More aggressive cleaning
                # Only keep basic ASCII printable characters plus newlines
                ultra_clean_json = ''.join(c for c in json_str if (c.isprintable() or c == '\n'))
                
                try:
                    parsed_json = json.loads(ultra_clean_json)
                    print(f"Successfully parsed JSON after aggressive cleaning")
                except json.JSONDecodeError as final_e:
                    print(f"Still failed to parse JSON after cleaning: {final_e}")
                    # Create a fallback response with an error message
                    if is_metadata:
                        return MetadataResponse(
                            title="Could not extract metadata",
                            abstract="Error parsing response",
                            error=f"Failed to parse JSON: {str(final_e)}"
                        ).dict(exclude_none=True)
                    else:
                        return [Reference(
                            text="Error parsing references",
                            citation_type="error",
                            error=f"Failed to parse JSON: {str(final_e)}"
                        ).dict(exclude_none=True)]
        
        # Validate and convert to appropriate model
        if is_metadata:
            # Convert to Pydantic model and then back to dict
            try:
                metadata_model = MetadataResponse(**parsed_json)
                return metadata_model.dict(exclude_none=True)
            except Exception as e:
                print(f"Error converting to MetadataResponse model: {e}")
                return MetadataResponse(
                    title="Could not extract metadata",
                    abstract="Error in data validation",
                    error=f"Failed to validate metadata: {str(e)}"
                ).dict(exclude_none=True)
        else:
            # Handle references
            try:
                # Validate the response format
                if not isinstance(parsed_json, list):
                    print(f"Warning: References response is not a list: {type(parsed_json)}")
                    # If it's a dict with references key, extract that
                    if isinstance(parsed_json, dict) and 'references' in parsed_json:
                        print("Found references key in dict, using that")
                        parsed_json = parsed_json['references']
                    else:
                        # Create a references response with an error
                        return [Reference(
                            text="Could not extract references",
                            error="Response format invalid",
                            citation_type="error"
                        ).dict(exclude_none=True)]
                
                # Convert each reference to a Pydantic model
                references = []
                for ref in parsed_json:
                    if isinstance(ref, dict):
                        references.append(Reference(**ref).dict(exclude_none=True))
                    else:
                        references.append(Reference(
                            text=str(ref),
                            error="Invalid reference format",
                            citation_type="error"
                        ).dict(exclude_none=True))
                
                return references
            except Exception as e:
                print(f"Error validating references: {e}")
                return [Reference(
                    text="Error validating references",
                    error=f"Validation error: {str(e)}",
                    citation_type="error"
                ).dict(exclude_none=True)]
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        if is_metadata:
            return MetadataResponse(
                title="Could not extract metadata",
                abstract="Error parsing response",
                error=f"Failed to parse response: {str(e)}"
            ).dict(exclude_none=True)
        else:
            return [Reference(
                text="Error parsing references",
                citation_type="error",
                error=f"Failed to parse references: {str(e)}"
            ).dict(exclude_none=True)]

async def extract_metadata_with_gemini(pdf_text: str, db: AsyncSession):
    """Extract metadata from PDF text using Google Gemini API"""
    # Ensure Gemini is configured
    if not await configure_gemini(db):
        return {"error": "Failed to configure Gemini API. Please check your API key."}
    
    try:
        # Use the latest Gemini 1.5 models directly
        # First, let's print the available models for debugging
        try:
            models = genai.list_models()
            print("Available Gemini models:")
            for model in models:
                print(f"- {model.name}")
            
            # Filter for Gemini models
            gemini_models = [model.name for model in models if "gemini" in model.name.lower()]
            print(f"Found {len(gemini_models)} Gemini models: {gemini_models}")
            
            if gemini_models:
                # Use the first available Gemini model
                model_name = gemini_models[0]
                print(f"Selected Gemini model: {model_name}")
            else:
                # Fallback to Gemini 1.5 Pro
                model_name = "gemini-2.0-flash-lite"
                print(f"No Gemini models found, using default: {model_name}")
        except Exception as e:
            print(f"Error listing models: {e}")
            # Fallback to Gemini 1.5 Pro
            model_name = "gemini-2.0-flash-lite"
            print(f"Error occurred, using default model: {model_name}")
        
        print(f"Creating GenerativeModel with name: {model_name}")
        model = genai.GenerativeModel(model_name)
        
        # Extract the first part of the PDF for title, authors, abstract
        first_part = pdf_text[:20000]  # Increase to 20,000 chars to capture more of the beginning
        
        # Look for the abstract section specifically
        abstract_section = None
        abstract_patterns = [
            r'(?i)Abstract\s*\n',
            r'(?i)ABSTRACT\s*:',
            r'(?i)Abstract\s*:',
            r'(?i)\nAbstract\s'
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, first_part)
            if match:
                abstract_start = match.end()
                # Try to find the end of the abstract (usually ends with Introduction or Keywords)
                end_patterns = [
                    r'(?i)\n\s*Introduction\s*\n',
                    r'(?i)\n\s*Keywords\s*:',
                    r'(?i)\n\s*1\.\s*Introduction',
                    r'(?i)\n\s*I\.\s*Introduction'
                ]
                
                abstract_end = len(first_part)
                for end_pattern in end_patterns:
                    end_match = re.search(end_pattern, first_part[abstract_start:])
                    if end_match:
                        abstract_end = abstract_start + end_match.start()
                        break
                
                abstract_section = first_part[abstract_start:abstract_end].strip()
                print(f"Found abstract: {abstract_section[:100]}...")
                break
        
        prompt = f"""
        Extract the following metadata from this academic article:
        - Title
        - Authors (with detailed information)
        - Abstract
        - Keywords
        - Journal name
        - Volume and issue numbers
        - Year of publication
        - DOI
        
        Return the information in a structured JSON format with these exact keys:
        "title", "authors", "abstract", "keywords", "journal", "volume", "issue", "year", "doi"
        
        For authors, use an array of objects with the following properties (if available):
        - "name" (full name)
        - "first_name"
        - "last_name"
        - "email"
        - "mobile_no"
        - "position" (job title or role, e.g., "Project Assistant-II", "Professor", "Research Scholar")
        - "institution" (name of the institution only, e.g., "CSIR - National Environmental Engineering Research Institute")
        - "orcid_id"
        - "department"
        - "location" (city, state, country of the institution)
        
        IMPORTANT: Separate the position from the institution name. For example, if the affiliation is "Project Assistant-II, CSIR - National Environmental Engineering Research Institute, Nagpur-440020 (India)", then:
        - position = "Project Assistant-II"
        - institution = "CSIR - National Environmental Engineering Research Institute"
        - location = "Nagpur-440020, India"
        
        IMPORTANT: If you cannot extract some information, use null or empty arrays as appropriate. Always return valid JSON.
        
        Here is the article text:
        {first_part}
        
        {f'I found the abstract section which might help: {abstract_section}' if abstract_section else ''}
        """
        
        # Generate content without safety settings
        try:
            print(f"Sending prompt to Gemini API (length: {len(prompt)} chars)")
            response = await model.generate_content_async(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 4096}
            )
            
            # Print the raw response for debugging
            print(f"Received response from Gemini API: {response}")
            print(f"Response text: {response.text[:500]}..." if len(response.text) > 500 else response.text)
            
            # Parse JSON from response
            try:
                # Extract JSON part from response
                text = response.text
                
                # Try different patterns to extract JSON
                json_str = None
                
                # Pattern 1: Markdown code block
                json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    print(f"Extracted JSON from markdown code block: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                
                # Pattern 2: Just the JSON object
                if not json_str:
                    json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        print(f"Extracted JSON object: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                
                # Pattern 3: Look for any JSON-like structure
                if not json_str:
                    # Look for any text between { and } that might be JSON
                    start_idx = text.find('{')
                    if start_idx >= 0:
                        # Find the matching closing brace
                        brace_count = 1
                        for i in range(start_idx + 1, len(text)):
                            if text[i] == '{':
                                brace_count += 1
                            elif text[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = text[start_idx:i+1]
                                    print(f"Extracted JSON by brace matching: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                                    break
                
                # If all else fails, use the raw text
                if not json_str:
                    json_str = text
                    print(f"Using raw text as JSON (last resort): {json_str[:200]}..." if len(json_str) > 200 else json_str)
                
                # Clean and parse JSON
                parsed_json = json.loads(json_str)
                print(f"Successfully parsed JSON response")
                
                # Convert to Pydantic model for validation and default values
                if not isinstance(parsed_json, dict):
                    print(f"Warning: Response is not a dictionary: {type(parsed_json)}")
                    return MetadataResponse(
                        title="Could not extract metadata",
                        abstract="Error: Invalid response format",
                        error="Response is not a dictionary"
                    ).dict()
                
                # Convert to Pydantic model and then back to dict
                # This ensures all required fields are present with defaults
                try:
                    metadata_model = MetadataResponse(**parsed_json)
                    return metadata_model.dict(exclude_none=True)
                except Exception as e:
                    print(f"Error converting to Pydantic model: {e}")
                    return MetadataResponse(
                        title="Could not extract metadata",
                        abstract="Error in data validation",
                        error=f"Failed to validate metadata: {str(e)}"
                    ).dict(exclude_none=True)
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                # Return a structured error response using Pydantic model
                return MetadataResponse(
                    title="Could not extract metadata",
                    abstract="Error parsing response",
                    error=f"Failed to parse metadata: {str(e)}",
                    raw_response=response.text[:500] if response and hasattr(response, 'text') else "No response text"
                ).dict(exclude_none=True)
        except Exception as e:
            print(f"Error generating content: {e}")
            # Return a structured error response using Pydantic model
            return MetadataResponse(
                title="Could not extract metadata",
                abstract="Error calling API",
                error=f"Failed to generate content: {str(e)}"
            ).dict(exclude_none=True)
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return MetadataResponse(
            title="Could not extract metadata",
            abstract="Error in API configuration",
            error=f"Error calling Gemini API: {e}"
        ).dict(exclude_none=True)

async def extract_references_with_gemini(pdf_text: str, db: AsyncSession):
    """Extract references from PDF text using Google Gemini API"""
    # Ensure Gemini is configured
    if not await configure_gemini(db):
        return {"error": "Failed to configure Gemini API. Please check your API key."}
    
    try:
        # Use the same model selection logic as in extract_metadata_with_gemini
        try:
            api_key = await get_active_key_by_type(db, "gemini")
            models = genai.list_models()
            print("Available Gemini models for references:")
            for model in models:
                print(f"- {model.name}")
            
            # Filter for Gemini models
            gemini_models = [model.name for model in models if "gemini" in model.name.lower()]
            print(f"Found {len(gemini_models)} Gemini models for references: {gemini_models}")
            
            if gemini_models:
                # Use the first available Gemini model
                # model_name = gemini_models[0]
                model_name = "gemini-2.0-flash-lite"
                print(f"Selected Gemini model for references: {model_name}")
            else:
                # Fallback to Gemini 1.5 Pro
                model_name = "gemini-2.0-flash-lite"
                print(f"No Gemini models found for references, using default: {model_name}")
        except Exception as e:
            print(f"Error listing models for references: {e}")
            # Fallback to Gemini 1.5 Pro
            model_name = "gemini-2.0-flash-lite"
            print(f"Error occurred, using default model for references: {model_name}")
        
        print(f"Creating GenerativeModel for references with name: {model_name}")
        model = genai.GenerativeModel(model_name)
        
        # First, look for a References or Bibliography section in the text
        references_section = None
        patterns = [
            r'(?i)References\s*\n',
            r'(?i)Bibliography\s*\n',
            r'(?i)Literature Cited\s*\n',
            r'(?i)Works Cited\s*\n',
            r'(?i)References Cited\s*\n'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pdf_text)
            if match:
                references_section = pdf_text[match.start():]
                print(f"Found references section starting with: {references_section[:100]}...")
                break
        
        # If no references section found, use the full text
        if not references_section:
            print("No explicit references section found, using full text")
            references_section = pdf_text
        
        # Limit the text to avoid token limits, but use more of the document
        # If we found a references section, use that, otherwise use the last part of the document
        if len(references_section) > 40000:
            text_for_analysis = references_section[:40000]
        else:
            text_for_analysis = references_section
        
        prompt = f"""
        Extract all references/citations from this academic article.
        For each reference, provide the following information in a structured format:
        
        1. Full reference text (exactly as it appears in the document)
        2. Citation type (journal, proceedings, book, website/URL, etc.)
        3. Authors (list of all authors)
        4. Title of the referenced work
        5. Year of publication
        6. Journal name (if it's a journal article)
        7. Conference name (if it's a conference proceeding)
        8. Volume and issue numbers (if applicable)
        9. Page numbers (if available)
        10. DOI (if available)
        11. URL (if it's a web resource)
        12. Publisher (if it's a book)
        13. Citation position (e.g., reference number in the bibliography)
        
        IMPORTANT: If you don't find any references in the text, look carefully for numbered citations, bracketed citations, or any list of sources at the end of the document. References might be formatted in various ways.
        
        For example, for the reference "1. Akram, f., O. Ilyas and B. A. K. Prusty (2015). International Journal of Engineering Technology Science and Research 2(10): 1-11.", provide:
        - text: "1. Akram, f., O. Ilyas and B. A. K. Prusty (2015). International Journal of Engineering Technology Science and Research 2(10): 1-11."
        - citation_type: "journal article"
        - authors: ["Akram, F.", "Ilyas, O.", "Prusty, B.A.K."]
        - title: (extract if present)
        - year: "2015"
        - journal: "International Journal of Engineering Technology Science and Research"
        - volume: "2"
        - issue: "10"
        - pages: "1-11"
        - citation_position: "1"
        
        Return the information in a structured JSON format as an array of reference objects.
        If you absolutely cannot find any references, return an empty array but explain why in a comment.
        
        Here is the article text:
        {text_for_analysis}
        """
        
        # Generate content without safety settings
        try:
            print(f"Sending references prompt to Gemini API (length: {len(prompt)} chars)")
            response = await model.generate_content_async(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 4096}
            )
            
            # Print the raw response for debugging
            print(f"Received references response from Gemini API: {response}")
            print(f"References response text: {response.text[:500]}..." if len(response.text) > 500 else response.text)
            
            # Parse JSON from response
            try:
                # Extract JSON part from response
                text = response.text
                
                # Try different patterns to extract JSON
                json_str = None
                
                # Pattern 1: Markdown code block
                json_match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    print(f"Extracted references JSON from markdown code block: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                
                # Pattern 2: Just the JSON array
                if not json_str:
                    json_match = re.search(r'(\[.*\])', text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        print(f"Extracted references JSON array: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                
                # Pattern 3: Look for any JSON-like structure
                if not json_str:
                    # Look for any text between [ and ] that might be JSON
                    start_idx = text.find('[')
                    if start_idx >= 0:
                        # Find the matching closing bracket
                        bracket_count = 1
                        for i in range(start_idx + 1, len(text)):
                            if text[i] == '[':
                                bracket_count += 1
                            elif text[i] == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    json_str = text[start_idx:i+1]
                                    print(f"Extracted references JSON by bracket matching: {json_str[:200]}..." if len(json_str) > 200 else json_str)
                                    break
                
                # If all else fails, use the raw text
                if not json_str:
                    json_str = text
                    print(f"Using raw text as references JSON (last resort): {json_str[:200]}..." if len(json_str) > 200 else json_str)
                
                # Clean and parse JSON
                parsed_json = json.loads(json_str)
                print(f"Successfully parsed references JSON response")
                
                # Use Pydantic model for validation and default values
                try:
                    # Validate the response format
                    if not isinstance(parsed_json, list):
                        print(f"Warning: References response is not a list: {type(parsed_json)}")
                        # If it's a dict with references key, extract that
                        if isinstance(parsed_json, dict) and 'references' in parsed_json:
                            print("Found references key in dict, using that")
                            parsed_json = parsed_json['references']
                        else:
                            # Create a references response with an error
                            return ReferencesResponse(
                                references=[Reference(
                                    text="Could not extract references",
                                    error="Response format invalid",
                                    citation_type="error"
                                )]
                            ).references
                    
                    # Convert each reference to a Pydantic model
                    references = []
                    for ref in parsed_json:
                        if isinstance(ref, dict):
                            references.append(Reference(**ref).dict(exclude_none=True))
                        else:
                            references.append(Reference(
                                text=str(ref),
                                error="Invalid reference format",
                                citation_type="error"
                            ).dict(exclude_none=True))
                    
                    return references
                except Exception as e:
                    print(f"Error validating references: {e}")
                    return [Reference(
                        text="Error validating references",
                        error=f"Validation error: {str(e)}",
                        citation_type="error"
                    ).dict(exclude_none=True)]
            except Exception as e:
                print(f"Error parsing references JSON: {e}")
                # Return a structured error response using Pydantic model
                return [Reference(
                    text="Error parsing references",
                    citation_type="error",
                    error=f"Failed to parse references: {str(e)}",
                    raw_response=response.text[:500] if response and hasattr(response, 'text') else "No response text"
                ).dict(exclude_none=True)]
        except Exception as e:
            print(f"Error generating references content: {e}")
            # Return a structured error response using Pydantic model
            return [Reference(
                text="Error calling API for references",
                citation_type="error",
                error=f"Failed to generate references content: {str(e)}"
            ).dict(exclude_none=True)]
            
    except Exception as e:
        print(f"Error calling Gemini API for references: {e}")
        return [Reference(
            text="Error in API configuration",
            citation_type="error",
            error=f"Error calling Gemini API: {e}"
        ).dict(exclude_none=True)]
