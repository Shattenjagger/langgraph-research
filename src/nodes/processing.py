"""Document processing nodes."""
import logging
import time
import json
from typing import Dict, Any
from ..models.local_model_manager import LocalModelManager
from ..models.model_configs import ModelType
from ..workflows.state import DocumentProcessingState, DocumentType, ProcessingStatus

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Processes documents based on their type."""
    
    def __init__(self, model_manager: LocalModelManager):
        self.model_manager = model_manager
    
    async def extract_data(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Extract structured data from the document."""
        start_time = time.time()
        state.current_step = "data_extraction"
        
        try:
            # Choose model based on document type
            model_type = self._select_model_for_extraction(state.document_type)
            
            # Create extraction prompt
            prompt = self._create_extraction_prompt(state)
            
            # Extract data using appropriate model
            response = await self.model_manager.invoke_with_fallback(
                model_type,
                prompt,
                max_retries=2
            )
            
            # Parse extracted data
            extracted_data = self._parse_extraction_response(response)
            
            # Update state
            state.extracted_data = extracted_data
            state.models_used.append(f"extraction:{model_type.value}")
            state.processing_notes.append(f"Extracted {len(extracted_data)} fields using {model_type.value}")
            
            logger.info(f"Extracted data: {list(extracted_data.keys())}")
            
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            state.error_message = f"Extraction error: {str(e)}"
            state.retry_count += 1
        
        finally:
            state.processing_time += time.time() - start_time
        
        return state
    
    async def validate_data(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Validate the extracted data."""
        start_time = time.time()
        state.current_step = "validation"
        
        try:
            # Use standard model for validation
            prompt = self._create_validation_prompt(state)
            
            response = await self.model_manager.invoke_with_fallback(
                ModelType.STANDARD,
                prompt,
                max_retries=2
            )
            
            # Parse validation results
            validation_results = self._parse_validation_response(response)
            
            # Update state
            state.validation_results = validation_results
            state.models_used.append(f"validation:{ModelType.STANDARD.value}")
            
            # Determine if human review is needed
            critical_issues = [r for r in validation_results if "CRITICAL" in r.upper()]
            state.human_review_required = len(critical_issues) > 0
            
            if critical_issues:
                state.status = ProcessingStatus.REQUIRES_REVIEW
                state.processing_notes.append(f"Requires review: {len(critical_issues)} critical issues")
            
            logger.info(f"Validation complete: {len(validation_results)} issues found")
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            state.error_message = f"Validation error: {str(e)}"
            state.retry_count += 1
        
        finally:
            state.processing_time += time.time() - start_time
        
        return state
    
    def _select_model_for_extraction(self, doc_type: DocumentType) -> ModelType:
        """Select appropriate model based on document complexity."""
        if doc_type == DocumentType.CONTRACT:
            return ModelType.REASONING  # Complex contracts need reasoning
        elif doc_type == DocumentType.INVOICE:
            return ModelType.STANDARD   # Invoices are structured
        else:
            return ModelType.FAST       # Simple documents
    
    def _create_extraction_prompt(self, state: DocumentProcessingState) -> str:
        """Create prompt for data extraction."""
        doc_type = state.document_type.value if state.document_type else "unknown"
        
        if state.document_type == DocumentType.INVOICE:
            fields = "vendor_name, amount, date, invoice_number, tax_amount, line_items"
        elif state.document_type == DocumentType.CONTRACT:
            fields = "parties, effective_date, expiry_date, key_terms, obligations"
        else:
            fields = "key_information, dates, amounts, parties"
        
        return f"""
Extract structured information from this {doc_type}. Return ONLY valid JSON with these fields: {fields}

Document:
{state.document_content[:2000]}

JSON:"""
    
    def _parse_extraction_response(self, response: str) -> Dict[str, Any]:
        """Parse extracted data from model response."""
        try:
            # Try to find JSON in the response
            response = response.strip()
            
            # Look for JSON block
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            elif '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            return json.loads(json_str)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse extraction JSON: {e}")
            # Return a basic structure
            return {"raw_response": response, "parse_error": str(e)}
    
    def _create_validation_prompt(self, state: DocumentProcessingState) -> str:
        """Create prompt for data validation."""
        return f"""
Validate this extracted data from a {state.document_type.value if state.document_type else 'document'}:

{json.dumps(state.extracted_data, indent=2)}

Check for:
- Missing required fields
- Inconsistent data
- Invalid formats
- Logical errors

Return each issue on a new line starting with CRITICAL: or WARNING:
If no issues, return: VALIDATION_PASSED

Issues:"""
    
    def _parse_validation_response(self, response: str) -> list[str]:
        """Parse validation results from model response."""
        try:
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            if any("VALIDATION_PASSED" in line.upper() for line in lines):
                return []
            
            # Extract issues
            issues = []
            for line in lines:
                if line.upper().startswith(('CRITICAL:', 'WARNING:')):
                    issues.append(line)
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to parse validation response: {e}")
            return [f"CRITICAL: Failed to parse validation results - {str(e)}"]