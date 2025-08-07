"""Decision nodes for conditional routing in workflows."""
import logging
from typing import Literal, Dict, Any
from ..workflows.state import DocumentProcessingState, DocumentType

logger = logging.getLogger(__name__)


class DocumentRouter:
    """Handles conditional routing based on document characteristics."""
    
    def determine_processing_path(self, state: DocumentProcessingState) -> str:
        """
        Determine which processing path to take based on document analysis.
        
        Returns:
            Path name for LangGraph routing
        """
        # Get document characteristics
        doc_type = state.document_type
        confidence = state.classification_confidence
        content_length = len(state.document_content)
        
        logger.info(f"Routing decision for {doc_type.value if doc_type else 'unknown'} "
                   f"(confidence: {confidence:.2f}, length: {content_length})")
        
        # Route based on confidence first
        if confidence < 0.6:
            state.processing_notes.append("Low confidence - routing to enhanced analysis")
            return "enhanced_analysis"
        
        # Route based on document type and complexity
        if doc_type == DocumentType.CONTRACT:
            if content_length > 2000:
                state.processing_notes.append("Complex contract - routing to expert analysis")
                return "expert_analysis"
            else:
                state.processing_notes.append("Standard contract - routing to standard processing")
                return "standard_processing"
        
        elif doc_type == DocumentType.INVOICE:
            # Check for complex invoice indicators
            if self._is_complex_invoice(state):
                state.processing_notes.append("Complex invoice - routing to detailed processing")
                return "detailed_processing"
            else:
                state.processing_notes.append("Simple invoice - routing to fast processing")
                return "fast_processing"
        
        elif doc_type == DocumentType.RECEIPT:
            state.processing_notes.append("Receipt - routing to fast processing")
            return "fast_processing"
        
        else:  # Unknown or other types
            state.processing_notes.append("Unknown document type - routing to enhanced analysis")
            return "enhanced_analysis"
    
    def _is_complex_invoice(self, state: DocumentProcessingState) -> bool:
        """Determine if an invoice is complex based on content analysis."""
        content = state.document_content.lower()
        
        # Indicators of complex invoices
        complex_indicators = [
            'line item',
            'discount',
            'tax exemption', 
            'multiple currencies',
            'purchase order',
            'contract reference',
            'milestone',
            'recurring'
        ]
        
        # Count complexity indicators
        complexity_score = sum(1 for indicator in complex_indicators if indicator in content)
        
        # Consider it complex if it has 2+ indicators or is very long
        return complexity_score >= 2 or len(state.document_content) > 1500


class ProcessingPathSelector:
    """Selects specific processing paths for different routing decisions."""
    
    @staticmethod
    def should_require_human_review(state: DocumentProcessingState) -> bool:
        """Determine if human review should be required."""
        # Always require review for contracts over certain value
        if state.document_type == DocumentType.CONTRACT:
            content = state.document_content.lower()
            if any(term in content for term in ['$100,000', '$50,000', 'million', 'termination']):
                state.processing_notes.append("High-value contract detected - requiring human review")
                return True
        
        # Require review if validation found critical issues
        critical_issues = [issue for issue in state.validation_results 
                          if 'CRITICAL' in issue.upper()]
        if len(critical_issues) >= 2:
            state.processing_notes.append("Multiple critical issues - requiring human review")
            return True
        
        # Require review for low confidence classifications
        if state.classification_confidence < 0.5:
            state.processing_notes.append("Low classification confidence - requiring human review")
            return True
        
        return False
    
    @staticmethod
    def should_retry_with_better_model(state: DocumentProcessingState) -> bool:
        """Determine if we should retry with a more powerful model."""
        # Retry if we got poor extraction results
        if not state.extracted_data or len(state.extracted_data) < 3:
            state.processing_notes.append("Poor extraction results - retrying with better model")
            return True
        
        # Retry if we have parse errors
        if 'parse_error' in state.extracted_data:
            state.processing_notes.append("Parse errors detected - retrying with better model")
            return True
        
        return False
    
    @staticmethod
    def determine_retry_strategy(state: DocumentProcessingState) -> Dict[str, Any]:
        """Determine the best retry strategy for failed processing."""
        strategy = {
            "max_retries": 2,
            "use_different_model": False,
            "adjust_parameters": False,
            "simplify_prompt": False
        }
        
        # If we've already retried multiple times, try different approaches
        if state.retry_count >= 2:
            strategy["use_different_model"] = True
            strategy["adjust_parameters"] = True
            state.processing_notes.append("Multiple failures - changing model and parameters")
        
        # For complex documents that keep failing, simplify the approach
        if (state.document_type == DocumentType.CONTRACT and 
            state.retry_count >= 1 and 
            len(state.document_content) > 3000):
            strategy["simplify_prompt"] = True
            state.processing_notes.append("Complex document - simplifying extraction approach")
        
        return strategy