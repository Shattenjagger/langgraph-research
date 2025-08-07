"""Document classification node."""
import logging
import time
from typing import Dict, Any
from ..models.local_model_manager import LocalModelManager
from ..models.model_configs import ModelType
from ..workflows.state import DocumentProcessingState, DocumentType

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Classifies documents using local models."""
    
    def __init__(self, model_manager: LocalModelManager):
        self.model_manager = model_manager
    
    async def classify_document(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """
        Classify the document type and extract basic information.
        Uses fast model for quick classification.
        """
        start_time = time.time()
        state.current_step = "classification"
        
        try:
            # Create classification prompt
            prompt = self._create_classification_prompt(state.document_content)
            
            # Use fast model for quick classification
            response = await self.model_manager.invoke_with_fallback(
                ModelType.FAST,
                prompt,
                max_retries=2
            )
            
            # Parse classification result
            doc_type, confidence = self._parse_classification_response(response)
            
            # Update state
            state.document_type = doc_type
            state.classification_confidence = confidence
            state.models_used.append(f"classification:{ModelType.FAST.value}")
            state.processing_notes.append(f"Classified as {doc_type.value} with {confidence:.2f} confidence")
            
            logger.info(f"Document classified as {doc_type.value} (confidence: {confidence:.2f})")
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            state.error_message = f"Classification error: {str(e)}"
            state.document_type = DocumentType.UNKNOWN
            state.classification_confidence = 0.0
            state.retry_count += 1
        
        finally:
            state.processing_time += time.time() - start_time
        
        return state
    
    def _create_classification_prompt(self, content: str) -> str:
        """Create prompt for document classification."""
        return f"""
Analyze this document and classify its type. Respond with ONLY the classification in this exact format:
TYPE: [invoice|contract|receipt|unknown]
CONFIDENCE: [0.0-1.0]

Document content:
{content[:1000]}...

Classification:"""
    
    def _parse_classification_response(self, response: str) -> tuple[DocumentType, float]:
        """Parse the model's classification response."""
        try:
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            doc_type = DocumentType.UNKNOWN
            confidence = 0.0
            
            for line in lines:
                if line.startswith('TYPE:'):
                    type_str = line.split(':', 1)[1].strip().lower()
                    try:
                        doc_type = DocumentType(type_str)
                    except ValueError:
                        doc_type = DocumentType.UNKNOWN
                
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.split(':', 1)[1].strip())
                        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]
                    except (ValueError, IndexError):
                        confidence = 0.5  # Default confidence
            
            return doc_type, confidence
            
        except Exception as e:
            logger.error(f"Failed to parse classification response: {e}")
            return DocumentType.UNKNOWN, 0.0