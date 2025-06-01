from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator


class Author(BaseModel):
    """Schema for author information"""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile_no: Optional[str] = None
    designation: Optional[str] = None
    institution: Optional[str] = None
    parent_institution: Optional[str] = None
    department: Optional[str] = None
    orcid_id: Optional[str] = None
    address: Optional[str] = None
    affiliation: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    
    class Config:
        # Allow extra fields to be included in the model
        extra = 'ignore'


class MetadataResponse(BaseModel):
    """Schema for metadata response from Gemini API"""
    title: Optional[str] = None
    authors: List[Author] = Field(default_factory=list)
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    journal: Optional[str] = None
    volume: Optional[Union[str, int]] = None
    issue: Optional[Union[str, int]] = None
    year: Optional[Union[str, int]] = None
    doi: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None
    
    class Config:
        # Allow extra fields to be included in the model
        extra = 'ignore'
    
    @validator('authors', pre=True)
    def validate_authors(cls, v):
        """Ensure authors is always a list"""
        if v is None:
            return []
        return v
    
    @validator('keywords', pre=True)
    def validate_keywords(cls, v):
        """Ensure keywords is always a list"""
        if v is None:
            return []
        return v


class Reference(BaseModel):
    """Schema for reference information"""
    text: Optional[str] = None
    citation_type: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    title: Optional[str] = None
    year: Optional[Union[str, int]] = None  # Allow both string and integer
    journal: Optional[str] = None
    conference: Optional[str] = None
    volume: Optional[Union[str, int]] = None  # Allow both string and integer
    issue: Optional[Union[str, int]] = None  # Allow both string and integer
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    citation_position: Optional[Union[str, int]] = None  # Allow both string and integer
    error: Optional[str] = None
    raw_response: Optional[str] = None
    
    @validator('year', 'volume', 'issue', 'citation_position', pre=True)
    def validate_numeric_fields(cls, v):
        """Convert numeric fields to strings if they are integers"""
        if isinstance(v, int):
            return str(v)
        return v
    
    @validator('authors', pre=True)
    def validate_authors(cls, v):
        """Ensure authors is always a list"""
        if v is None:
            return []
        return v


class ReferencesResponse(BaseModel):
    """Schema for references response from Gemini API"""
    references: List[Reference] = Field(default_factory=list)
    error: Optional[str] = None
    
    class Config:
        # Allow extra fields to be included in the model
        extra = 'ignore'
    
    @validator('references', pre=True)
    def validate_references(cls, v):
        """Handle different formats of references response"""
        if v is None:
            return []
        
        # If it's already a list, return it
        if isinstance(v, list):
            return v
            
        # If it's a dict with a 'references' key, use that
        if isinstance(v, dict) and 'references' in v:
            return v['references']
            
        # Otherwise, wrap it in a list
        return [v]


class PDFProcessingResult(BaseModel):
    """Schema for the complete PDF processing result"""
    file_url: str
    extracted_text: Optional[str] = None
    metadata: Optional[MetadataResponse] = None
    references: List[Reference] = Field(default_factory=list)
    processing_time: Optional[int] = None
    error: Optional[str] = None
    
    class Config:
        # Allow extra fields to be included in the model
        extra = 'ignore'
