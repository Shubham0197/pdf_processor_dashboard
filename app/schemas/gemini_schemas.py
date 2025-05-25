from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator

class ArticleType(str, Enum):
    ACADEMIC_FORUM       = "ACADEMIC FORUM"
    ANNUAL_REPORT        = "ANNUAL REPORT"
    BRIEF_COMMUNICATION  = "BRIEF COMMUNICATION"
    BRIEF_REPORT         = "BRIEF REPORT"
    CASE_REPORT          = "CASE REPORT"
    CASE_STUDY           = "CASE STUDY"
    COLLOQIA             = "COLLOQIA"
    COMMENTARY           = "COMMENTARY"
    COMMENTS             = "COMMENTS"
    COMMISSION_REPORT    = "COMMISSION REPORT"
    COMMITTEE_REPORT     = "COMMITTEE REPORT"
    CONFERENCE_PROCEEDING= "CONFERENCE PROCEEDING"
    CORPORATE_REPORT     = "CORPORATE REPORT"
    CORRESPONDENCE_RND   = "CORRESPONDENCE R&D"
    CRITICISM            = "CRITICISM"
    DISCUSSION           = "DISCUSSION"
    EDITORIAL            = "EDITORIAL"
    EDUCATION_FORUM      = "EDUCATION FORUM"
    EXCERPTS             = "EXCERPTS"
    EXPERIMENTS          = "EXPERIMENTS"
    GENERAL_ARTICLE      = "GENERAL ARTICLE"
    GENERAL_PAPER        = "GENERAL PAPER"
    GUEST_EDITOR_ARTICLE = "GUEST EDITOR ARTICLE"
    HISTORICAL_NOTE      = "HISTORICAL NOTE"
    INVITED_ARTICLE      = "INVITED ARTICLE"
    INVITED_LECTURE      = "INVITED LECTURE"
    KEYNOTE_ADDRESS      = "KEYNOTE ADDRESS"
    LETTER_TO_EDITOR     = "LETTER TO EDITOR"
    LITERATURE_REVIEW    = "LITERATURE REVIEW"
    MEETS                = "MEETS"
    MEMORIAL_LECTURE     = "MEMORIAL LECTURE"
    MINI_REVIEW          = "MINI REVIEW"
    NATURE_BEHAVIORS     = "NATURE BEHAVIORS"
    OBSERVATION          = "OBSERVATION"
    OPINION_PAPER        = "OPINION PAPER"
    ORIGINAL_ARTICLE     = "ORIGINAL ARTICLE"
    PAPER                = "PAPER"
    PATENT               = "PATENT"
    POINTS_TO_PONDER     = "POINTS TO PONDER"
    RND_FORUM            = "R&D FORUM"
    RND_REPORT           = "R&D REPORT"
    REPORT               = "REPORT"
    REPORT_ANY_OTHER     = "REPORT- ANY OTHER"
    RESEARCH_ARTICLE     = "RESEARCH ARTICLE"
    RESEARCH_COMMUNICATIONS = "RESEARCH COMMUNICATIONS"
    RESEARCH_METHODS     = "RESEARCH METHOD (S)"
    RESEARCH_NEWS        = "RESEARCH NEWS"
    RESEARCH_NOTE        = "RESEARCH NOTE"
    RESEARCH_PAPER       = "RESEARCH PAPER"
    REVIEW_ARTICLE       = "REVIEW ARTICLE"
    ST_REPORTS           = "S&T REPORTS"
    SEMINAR              = "SEMINAR"
    SHORT_COMMUNICATION  = "SHORT COMMUNICATION"
    SPECIAL_ARTICLE      = "SPECIAL ARTICLE"
    SPECIAL_PAPER        = "SPECIAL PAPER"
    STANDARD             = "STANDARD"
    SYMPOSIUM            = "SYMPOSIUM"
    TECHNICAL_REPORT     = "TECHNICAL REPORT"
    WHITE_PAPER          = "WHITE PAPER"
    WORKING_PAPER        = "WORKING PAPER"
    WORKSHOP             = "WORKSHOP"

class DocumentType(str, Enum):
    FULL_TEXT = "Full Text"
    ABSTRACT  = "Abstract"
    INDEXING  = "Indexing"

class Author(BaseModel):
    """Schema for author information"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile_no: Optional[str] = None
    position: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    orcid_id: Optional[str] = None
    location: Optional[str] = None

    model_config = {
        "extra": "allow"  # Allow extra fields
    }
    
class Reference(BaseModel):
    text: Optional[str]                      = None
    citation_type: Optional[str]             = None
    authors: List[str]                       = Field(default_factory=list)
    title: Optional[str]                     = None
    year: Optional[int]                      = None
    journal: Optional[str]                   = None
    volume: Optional[str]                    = None
    issue: Optional[str]                     = None
    pages: Optional[str]                     = None
    doi: Optional[str]                       = None
    url: Optional[str]                   = None
    publisher: Optional[str]                 = None
    citation_position: Optional[str]         = None
    error: Optional[str]                     = None
    raw_response: Optional[str]              = None

    @field_validator('authors', mode='before')
    def ensure_authors_list(cls, v):
        return v or []



    @field_validator('year', 'volume', 'issue', 'citation_position', mode='before')
    def validate_numeric_fields(cls, v):
        """Convert numeric fields to strings if they are integers"""
        if isinstance(v, int):
            return str(v)
        return v

    # @field_validator('authors', mode='before')
    # def validate_authors(cls, v):
    #     """Ensure authors is always a list"""
    #     if v is None:
    #         return []
    #     return v

# class MetadataResponse(BaseModel):
#     """Schema for metadata response from Gemini API"""
#     title: Optional[str] = None
#     authors: List[Author] = Field(default_factory=list)
#     abstract: Optional[str] = None
#     keywords: List[str] = Field(default_factory=list)
#     journal: Optional[str] = None
#     volume: Optional[Union[str, int]] = None
#     issue: Optional[Union[str, int]] = None
#     year: Optional[Union[str, int]] = None
#     doi: Optional[str] = None
#     error: Optional[str] = None
#     raw_response: Optional[str] = None

class MetadataResponse(BaseModel):
    title: Optional[str]                     = None
    abstract: Optional[str]                  = None
    journal: Optional[str]                   = None
    volume: Optional[str]                    = None
    issue: Optional[str]                     = None
    year: Optional[int]                      = None
    doi: Optional[str]                       = None
    pages: Optional[str]                     = None
    keywords: List[str]                      = Field(default_factory=list)
    authors: List[Author]                    = Field(default_factory=list)
    references: List[Reference]              = Field(default_factory=list)
    article_type: Optional[ArticleType]      = None
    raw_response: Optional[str]              = None
    error: Optional[str]                     = None

    model_config = {
        "extra": "allow"  # Allow extra fields
    }

    # @field_validator('authors', mode='before')
    # def validate_authors(cls, v):
    #     """Ensure authors is always a list"""
    #     if v is None:
    #         return []
    #     return v

    # @field_validator('keywords', mode='before')
    # def validate_keywords(cls, v):
    #     """Ensure keywords is always a list"""
    #     if v is None:
    #         return []
    #     return v
    @field_validator('keywords', 'authors', 'references', mode='before')
    def ensure_lists(cls, v):
        return v or []


# class Reference(BaseModel):
#     """Schema for reference information"""
#     text: Optional[str] = None
#     citation_type: Optional[str] = None
#     authors: List[str] = Field(default_factory=list)
#     title: Optional[str] = None
#     year: Optional[Union[str, int]] = None  # Allow both string and integer
#     journal: Optional[str] = None
#     volume: Optional[Union[str, int]] = None  # Allow both string and integer
#     issue: Optional[Union[str, int]] = None  # Allow both string and integer
#     pages: Optional[str] = None
#     doi: Optional[str] = None
#     url: Optional[str] = None
#     publisher: Optional[str] = None
#     citation_position: Optional[Union[str, int]] = None  # Allow both string and integer
#     error: Optional[str] = None
#     raw_response: Optional[str] = None

class ReferencesResponse(BaseModel):
    """Schema for references response from Gemini API"""
    references: List[Reference] = Field(default_factory=list)
    error: Optional[str] = None

    model_config = {
        "extra": "allow"  # Allow extra fields
    }

    @field_validator('references', mode='before')
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

    model_config = {
        "extra": "allow"  # Allow extra fields
    }
