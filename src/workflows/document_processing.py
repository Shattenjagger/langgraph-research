"""Simple document processing workflow using LangGraph."""
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from ..models.local_model_manager import LocalModelManager
from ..nodes.classification import DocumentClassifier
from ..nodes.processing import DocumentProcessor
from ..workflows.state import DocumentProcessingState, ProcessingStatus

logger = logging.getLogger(__name__)


class DocumentProcessingWorkflow:
    """LangGraph workflow for processing documents."""
    
    def __init__(self, model_manager: LocalModelManager):
        self.model_manager = model_manager
        self.classifier = DocumentClassifier(model_manager)
        self.processor = DocumentProcessor(model_manager)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create graph with our state type
        workflow = StateGraph(DocumentProcessingState)
        
        # Add nodes
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("extract", self._extract_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Set entry point
        workflow.set_entry_point("classify")
        
        # Add edges
        workflow.add_edge("classify", "extract")
        workflow.add_edge("extract", "validate")
        workflow.add_edge("validate", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def _classify_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Classification node wrapper."""
        logger.info(f"Processing document {state.document_id}: Classification")
        return await self.classifier.classify_document(state)
    
    async def _extract_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Data extraction node wrapper."""
        logger.info(f"Processing document {state.document_id}: Data extraction")
        return await self.processor.extract_data(state)
    
    async def _validate_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Validation node wrapper."""
        logger.info(f"Processing document {state.document_id}: Validation")
        return await self.processor.validate_data(state)
    
    async def _finalize_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Finalization node."""
        logger.info(f"Processing document {state.document_id}: Finalization")
        
        # Create final result
        state.final_result = {
            "document_id": state.document_id,
            "document_type": state.document_type.value if state.document_type else "unknown",
            "classification_confidence": state.classification_confidence,
            "extracted_data": state.extracted_data,
            "validation_issues": state.validation_results,
            "human_review_required": state.human_review_required,
            "processing_time": state.processing_time,
            "models_used": state.models_used,
            "retry_count": state.retry_count
        }
        
        # Set final status
        if state.error_message:
            state.status = ProcessingStatus.FAILED
        elif state.human_review_required:
            state.status = ProcessingStatus.REQUIRES_REVIEW
        else:
            state.status = ProcessingStatus.COMPLETED
        
        state.current_step = "completed"
        
        logger.info(f"Document {state.document_id} processing complete: {state.status.value}")
        
        return state
    
    async def process_document(
        self, 
        document_content: str, 
        document_id: str = None
    ) -> DocumentProcessingState:
        """
        Process a document through the complete workflow.
        
        Args:
            document_content: The document text to process
            document_id: Optional document identifier
            
        Returns:
            Final processing state with results
        """
        if not document_id:
            document_id = f"doc_{hash(document_content[:100]) % 10000:04d}"
        
        # Initialize state
        initial_state = DocumentProcessingState(
            document_content=document_content,
            document_id=document_id,
            status=ProcessingStatus.IN_PROGRESS
        )
        
        logger.info(f"Starting document processing workflow for {document_id}")
        
        try:
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow failed for document {document_id}: {e}")
            initial_state.error_message = f"Workflow error: {str(e)}"
            initial_state.status = ProcessingStatus.FAILED
            return initial_state