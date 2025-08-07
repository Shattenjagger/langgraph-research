"""Advanced document processing workflow with conditional branching."""
import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from ..models.local_model_manager import LocalModelManager
from ..models.model_configs import ModelType
from ..nodes.classification import DocumentClassifier
from ..nodes.processing import DocumentProcessor
from ..nodes.decision import DocumentRouter, ProcessingPathSelector
from ..workflows.state import DocumentProcessingState, ProcessingStatus, DocumentType

logger = logging.getLogger(__name__)


class ConditionalDocumentWorkflow:
    """LangGraph workflow with conditional branching based on document characteristics."""
    
    def __init__(self, model_manager: LocalModelManager):
        self.model_manager = model_manager
        self.classifier = DocumentClassifier(model_manager)
        self.processor = DocumentProcessor(model_manager)
        self.router = DocumentRouter()
        self.path_selector = ProcessingPathSelector()
        self.graph = self._build_conditional_graph()
    
    def _build_conditional_graph(self) -> StateGraph:
        """Build the conditional workflow graph."""
        workflow = StateGraph(DocumentProcessingState)
        
        # Add all processing nodes
        workflow.add_node("classify", self._classify_node)
        workflow.add_node("route_decision", self._route_decision_node)
        
        # Different processing paths
        workflow.add_node("fast_processing", self._fast_processing_node)
        workflow.add_node("standard_processing", self._standard_processing_node)  
        workflow.add_node("detailed_processing", self._detailed_processing_node)
        workflow.add_node("expert_analysis", self._expert_analysis_node)
        workflow.add_node("enhanced_analysis", self._enhanced_analysis_node)
        
        # Decision and quality control nodes
        workflow.add_node("quality_check", self._quality_check_node)
        workflow.add_node("retry_decision", self._retry_decision_node)
        workflow.add_node("retry_processing", self._retry_processing_node)
        workflow.add_node("human_review_check", self._human_review_check_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Set entry point
        workflow.set_entry_point("classify")
        
        # Main flow edges
        workflow.add_edge("classify", "route_decision")
        
        # Conditional edges from routing decision
        workflow.add_conditional_edges(
            "route_decision",
            self._determine_processing_path,
            {
                "fast_processing": "fast_processing",
                "standard_processing": "standard_processing",
                "detailed_processing": "detailed_processing", 
                "expert_analysis": "expert_analysis",
                "enhanced_analysis": "enhanced_analysis"
            }
        )
        
        # All processing paths go to quality check
        for path in ["fast_processing", "standard_processing", "detailed_processing", 
                    "expert_analysis", "enhanced_analysis"]:
            workflow.add_edge(path, "quality_check")
        
        # Quality check decision
        workflow.add_conditional_edges(
            "quality_check",
            self._should_retry,
            {
                "retry": "retry_decision",
                "continue": "human_review_check"
            }
        )
        
        # Retry flow
        workflow.add_edge("retry_decision", "retry_processing")
        workflow.add_edge("retry_processing", "quality_check")
        
        # Final decision flow
        workflow.add_conditional_edges(
            "human_review_check", 
            self._needs_human_review,
            {
                "review": "finalize",
                "complete": "finalize"
            }
        )
        
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    # Node implementations
    async def _classify_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Classification node."""
        logger.info(f"Step 1: Classifying document {state.document_id}")
        return await self.classifier.classify_document(state)
    
    async def _route_decision_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Routing decision node - determines processing path."""
        logger.info(f"Step 2: Making routing decision for {state.document_id}")
        state.current_step = "routing_decision"
        
        # The actual routing decision is made by the conditional edge
        # This node just prepares state if needed
        return state
    
    # Processing path nodes
    async def _fast_processing_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Fast processing path for simple documents."""
        logger.info(f"Processing path: FAST for {state.document_id}")
        state.current_step = "fast_processing"
        
        # Use fast model for both extraction and validation
        return await self._process_with_model_type(state, ModelType.FAST, "fast")
    
    async def _standard_processing_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Standard processing path."""
        logger.info(f"Processing path: STANDARD for {state.document_id}")
        state.current_step = "standard_processing"
        
        return await self._process_with_model_type(state, ModelType.STANDARD, "standard")
    
    async def _detailed_processing_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Detailed processing for complex invoices."""
        logger.info(f"Processing path: DETAILED for {state.document_id}")
        state.current_step = "detailed_processing"
        
        # Use reasoning model for complex extraction
        return await self._process_with_model_type(state, ModelType.REASONING, "detailed")
    
    async def _expert_analysis_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Expert analysis for complex contracts."""
        logger.info(f"Processing path: EXPERT ANALYSIS for {state.document_id}")
        state.current_step = "expert_analysis"
        
        # Use reasoning model with specialized prompts
        return await self._process_with_specialized_prompts(state)
    
    async def _enhanced_analysis_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Enhanced analysis for unknown/low-confidence documents."""
        logger.info(f"Processing path: ENHANCED ANALYSIS for {state.document_id}")
        state.current_step = "enhanced_analysis"
        
        # Try to reclassify first, then process
        await self.classifier.classify_document(state)  # Re-classify
        return await self._process_with_model_type(state, ModelType.REASONING, "enhanced")
    
    async def _quality_check_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Quality check after processing."""
        logger.info(f"Quality check for {state.document_id}")
        state.current_step = "quality_check"
        
        # Run validation
        await self.processor.validate_data(state)
        
        return state
    
    async def _retry_decision_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Decide how to retry processing."""
        logger.info(f"Retry decision for {state.document_id}")
        state.current_step = "retry_decision"
        
        # Get retry strategy
        strategy = self.path_selector.determine_retry_strategy(state)
        state.processing_notes.append(f"Retry strategy: {strategy}")
        
        return state
    
    async def _retry_processing_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Retry processing with different approach."""
        logger.info(f"Retrying processing for {state.document_id}")
        state.current_step = "retry_processing"
        state.retry_count += 1
        
        # Try with reasoning model as fallback
        return await self._process_with_model_type(state, ModelType.REASONING, "retry")
    
    async def _human_review_check_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Check if human review is needed."""
        logger.info(f"Human review check for {state.document_id}")
        state.current_step = "human_review_check"
        
        state.human_review_required = self.path_selector.should_require_human_review(state)
        
        return state
    
    async def _finalize_node(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Finalize processing."""
        logger.info(f"Finalizing {state.document_id}")
        return await self._create_final_result(state)
    
    # Helper methods
    async def _process_with_model_type(
        self, 
        state: DocumentProcessingState, 
        model_type: ModelType,
        path_name: str
    ) -> DocumentProcessingState:
        """Process document with specific model type."""
        # Extract data
        original_model_selection = self.processor._select_model_for_extraction
        self.processor._select_model_for_extraction = lambda _: model_type
        
        try:
            await self.processor.extract_data(state)
            state.processing_notes.append(f"Used {path_name} processing with {model_type.value} model")
        finally:
            # Restore original model selection
            self.processor._select_model_for_extraction = original_model_selection
        
        return state
    
    async def _process_with_specialized_prompts(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Process with specialized prompts for expert analysis."""
        # This could include contract-specific analysis, risk assessment, etc.
        await self._process_with_model_type(state, ModelType.REASONING, "expert")
        
        # Add expert analysis notes
        if state.document_type == DocumentType.CONTRACT:
            state.processing_notes.append("Applied contract risk analysis protocols")
        
        return state
    
    async def _create_final_result(self, state: DocumentProcessingState) -> DocumentProcessingState:
        """Create final processing result."""
        # Set final status
        if state.error_message and state.retry_count >= 3:
            state.status = ProcessingStatus.FAILED
        elif state.human_review_required:
            state.status = ProcessingStatus.REQUIRES_REVIEW
        else:
            state.status = ProcessingStatus.COMPLETED
        
        # Create final result
        state.final_result = {
            "document_id": state.document_id,
            "processing_path": state.current_step,
            "document_type": state.document_type.value if state.document_type and hasattr(state.document_type, 'value') else str(state.document_type) if state.document_type else "unknown",
            "classification_confidence": state.classification_confidence,
            "extracted_data": state.extracted_data,
            "validation_issues": state.validation_results,
            "human_review_required": state.human_review_required,
            "processing_time": state.processing_time,
            "models_used": state.models_used,
            "retry_count": state.retry_count,
            "processing_notes": state.processing_notes,
            "final_status": state.status.value
        }
        
        state.current_step = "completed"
        logger.info(f"Document {state.document_id} processing complete: {state.status.value}")
        
        return state
    
    # Conditional edge functions
    def _determine_processing_path(self, state: DocumentProcessingState) -> str:
        """Determine which processing path to take."""
        return self.router.determine_processing_path(state)
    
    def _should_retry(self, state: DocumentProcessingState) -> Literal["retry", "continue"]:
        """Determine if processing should be retried."""
        if (state.retry_count < 2 and 
            self.path_selector.should_retry_with_better_model(state)):
            return "retry"
        return "continue"
    
    def _needs_human_review(self, state: DocumentProcessingState) -> Literal["review", "complete"]:
        """Determine if human review is needed."""
        return "review" if state.human_review_required else "complete"
    
    # Public interface
    async def process_document(
        self, 
        document_content: str, 
        document_id: str = None
    ) -> DocumentProcessingState:
        """Process a document through the conditional workflow."""
        if not document_id:
            document_id = f"doc_{hash(document_content[:100]) % 10000:04d}"
        
        initial_state = DocumentProcessingState(
            document_content=document_content,
            document_id=document_id,
            status=ProcessingStatus.IN_PROGRESS
        )
        
        logger.info(f"Starting conditional workflow for {document_id}")
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"Conditional workflow failed for {document_id}: {e}")
            initial_state.error_message = f"Workflow error: {str(e)}"
            initial_state.status = ProcessingStatus.FAILED
            return initial_state