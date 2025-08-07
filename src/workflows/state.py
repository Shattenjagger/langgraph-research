"""State definitions for LangGraph workflows."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum


class DocumentType(Enum):
    """Types of documents that can be processed."""
    INVOICE = "invoice"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    UNKNOWN = "unknown"


class ProcessingStatus(Enum):
    """Status of document processing."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class DocumentProcessingState(BaseModel):
    """State for document processing workflow."""
    
    # Input
    document_content: str = ""
    document_id: str = ""
    
    # Processing results
    document_type: Optional[DocumentType] = None
    classification_confidence: float = 0.0
    extracted_data: Dict[str, Any] = {}
    validation_results: List[str] = []
    processing_notes: List[str] = []
    
    # Status tracking
    status: ProcessingStatus = ProcessingStatus.PENDING
    current_step: str = "initialization"
    error_message: Optional[str] = None
    
    # Model usage tracking
    models_used: List[str] = []
    processing_time: float = 0.0
    retry_count: int = 0
    
    # Final output
    final_result: Optional[Dict[str, Any]] = None
    human_review_required: bool = False
    
    class Config:
        use_enum_values = True