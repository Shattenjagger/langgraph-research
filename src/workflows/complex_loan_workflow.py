"""Complex multi-model loan application processing workflow."""
import logging
import time
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from ..models.local_model_manager import LocalModelManager
from ..models.fallback_chain import EnhancedModelFallbackChain
from ..nodes.loan_processing_nodes import (
    LoanDocumentAnalyzer, RiskAssessmentEngine, LoanDecisionEngine
)
from ..workflows.loan_application_state import (
    LoanApplicationState, ProcessingStatus, RiskLevel
)

logger = logging.getLogger(__name__)


class ComplexLoanProcessingWorkflow:
    """
    Complex loan application processing workflow demonstrating:
    - Multi-model coordination
    - Conditional branching based on risk and completeness
    - Retry mechanisms with exponential backoff
    - Sophisticated fallback strategies
    - Human handoff for edge cases
    - Quality checkpoints and validation
    """
    
    def __init__(self, model_manager: LocalModelManager):
        self.model_manager = model_manager
        self.fallback_chain = EnhancedModelFallbackChain(model_manager)
        
        # Initialize processing nodes
        self.document_analyzer = LoanDocumentAnalyzer(self.fallback_chain)
        self.risk_engine = RiskAssessmentEngine(self.fallback_chain)
        self.decision_engine = LoanDecisionEngine(self.fallback_chain)
        
        # Build the workflow graph
        self.graph = self._build_workflow_graph()
    
    def _build_workflow_graph(self) -> StateGraph:
        """Build the complex loan processing workflow graph."""
        workflow = StateGraph(LoanApplicationState)
        
        # Add processing nodes
        workflow.add_node("initialize", self._initialize_processing)
        workflow.add_node("analyze_documents", self._analyze_documents_node)
        workflow.add_node("quality_check_documents", self._quality_check_documents)
        workflow.add_node("assess_risk", self._assess_risk_node)
        workflow.add_node("quality_check_risk", self._quality_check_risk)
        workflow.add_node("make_decision", self._make_decision_node)
        workflow.add_node("final_validation", self._final_validation_node)
        workflow.add_node("prepare_response", self._prepare_response_node)
        
        # Error handling and retry nodes
        workflow.add_node("handle_document_retry", self._handle_document_retry)
        workflow.add_node("handle_risk_retry", self._handle_risk_retry)
        workflow.add_node("escalate_to_human", self._escalate_to_human)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # Main processing flow
        workflow.add_edge("initialize", "analyze_documents")
        
        # Document analysis flow with quality check
        workflow.add_conditional_edges(
            "analyze_documents",
            self._check_document_analysis_success,
            {
                "success": "quality_check_documents",
                "retry": "handle_document_retry",
                "fail": "escalate_to_human"
            }
        )
        
        # Document quality check
        workflow.add_conditional_edges(
            "quality_check_documents",
            self._check_document_quality,
            {
                "pass": "assess_risk",
                "insufficient": "escalate_to_human",
                "retry": "handle_document_retry"
            }
        )
        
        # Document retry handling
        workflow.add_conditional_edges(
            "handle_document_retry",
            self._should_retry_documents,
            {
                "retry": "analyze_documents",
                "escalate": "escalate_to_human"
            }
        )
        
        # Risk assessment flow
        workflow.add_conditional_edges(
            "assess_risk",
            self._check_risk_assessment_success,
            {
                "success": "quality_check_risk",
                "retry": "handle_risk_retry", 
                "fail": "escalate_to_human"
            }
        )
        
        # Risk quality check
        workflow.add_conditional_edges(
            "quality_check_risk",
            self._check_risk_quality,
            {
                "pass": "make_decision",
                "high_risk": "escalate_to_human",
                "retry": "handle_risk_retry"
            }
        )
        
        # Risk retry handling
        workflow.add_conditional_edges(
            "handle_risk_retry",
            self._should_retry_risk,
            {
                "retry": "assess_risk",
                "escalate": "escalate_to_human"
            }
        )
        
        # Decision making flow
        workflow.add_conditional_edges(
            "make_decision",
            self._check_decision_quality,
            {
                "valid": "final_validation",
                "requires_review": "escalate_to_human",
                "retry": "make_decision"
            }
        )
        
        # Final steps
        workflow.add_edge("final_validation", "prepare_response")
        workflow.add_edge("prepare_response", END)
        workflow.add_edge("escalate_to_human", END)
        
        return workflow.compile()
    
    # Node implementations
    async def _initialize_processing(self, state: LoanApplicationState) -> LoanApplicationState:
        """Initialize the loan processing workflow."""
        logger.info(f"Initializing loan application processing: {state.application_id}")
        
        step = state.add_processing_step("initialization")
        state.current_status = ProcessingStatus.DOCUMENT_ANALYSIS
        
        # Record start time
        start_time = time.time()
        
        # Basic validation
        if not state.documents and not state.raw_application_data:
            state.add_error("No documents or application data provided")
            state.trigger_human_review("Missing application data")
        
        state.complete_current_step("completed", 1.0, ["Workflow initialized"])
        return state
    
    async def _analyze_documents_node(self, state: LoanApplicationState) -> LoanApplicationState:
        """Document analysis node."""
        logger.info(f"Analyzing documents for application {state.application_id}")
        return await self.document_analyzer.analyze_documents(state)
    
    async def _quality_check_documents(self, state: LoanApplicationState) -> LoanApplicationState:
        """Quality check for document analysis results."""
        step = state.add_processing_step("document_quality_check")
        
        try:
            # Check completeness of extracted information
            completeness_issues = []
            
            if not state.applicant_info or not state.applicant_info.name:
                completeness_issues.append("Missing applicant name")
            
            if not state.applicant_info or not state.applicant_info.annual_income:
                completeness_issues.append("Missing income information")
            
            if not state.loan_details or not state.loan_details.requested_amount:
                completeness_issues.append("Missing loan amount")
            
            if completeness_issues:
                state.add_warning(f"Completeness issues: {', '.join(completeness_issues)}")
                state.quality_checks_failed += 1
            else:
                state.quality_checks_passed += 1
            
            confidence = 1.0 - (len(completeness_issues) * 0.2)
            state.complete_current_step("completed", confidence, 
                                      [f"Found {len(completeness_issues)} completeness issues"])
            
        except Exception as e:
            state.add_error(f"Document quality check failed: {str(e)}")
            state.complete_current_step("failed")
        
        return state
    
    async def _assess_risk_node(self, state: LoanApplicationState) -> LoanApplicationState:
        """Risk assessment node."""
        logger.info(f"Assessing risk for application {state.application_id}")
        state.current_status = ProcessingStatus.RISK_EVALUATION
        return await self.risk_engine.assess_risk(state)
    
    async def _quality_check_risk(self, state: LoanApplicationState) -> LoanApplicationState:
        """Quality check for risk assessment."""
        step = state.add_processing_step("risk_quality_check")
        
        try:
            risk_issues = []
            
            if not state.risk_assessment:
                risk_issues.append("No risk assessment completed")
            elif state.risk_assessment.overall_risk_level == RiskLevel.CRITICAL:
                risk_issues.append("Critical risk level detected")
            elif state.risk_assessment.risk_score > 80:
                risk_issues.append("Very high risk score")
            
            if risk_issues:
                state.quality_checks_failed += 1
                for issue in risk_issues:
                    state.add_warning(issue)
            else:
                state.quality_checks_passed += 1
            
            confidence = 1.0 - (len(risk_issues) * 0.3)
            state.complete_current_step("completed", confidence,
                                      [f"Risk quality check: {len(risk_issues)} issues"])
            
        except Exception as e:
            state.add_error(f"Risk quality check failed: {str(e)}")
            state.complete_current_step("failed")
        
        return state
    
    async def _make_decision_node(self, state: LoanApplicationState) -> LoanApplicationState:
        """Decision making node."""
        logger.info(f"Making decision for application {state.application_id}")
        state.current_status = ProcessingStatus.DECISION_PENDING
        return await self.decision_engine.make_decision(state)
    
    async def _final_validation_node(self, state: LoanApplicationState) -> LoanApplicationState:
        """Final validation before response."""
        step = state.add_processing_step("final_validation")
        
        try:
            validation_issues = []
            
            # Validate decision consistency
            if not state.final_decision:
                validation_issues.append("No final decision made")
            elif state.final_decision.decision == ProcessingStatus.APPROVED:
                if not state.final_decision.approved_amount:
                    validation_issues.append("Approved loan missing amount")
                if not state.final_decision.interest_rate:
                    validation_issues.append("Approved loan missing interest rate")
            
            # Check for unresolved errors
            if state.processing_errors and not state.human_review_triggers:
                validation_issues.append("Unresolved processing errors")
            
            if validation_issues:
                for issue in validation_issues:
                    state.add_warning(f"Final validation: {issue}")
                state.quality_checks_failed += 1
            else:
                state.quality_checks_passed += 1
            
            confidence = 1.0 - (len(validation_issues) * 0.25)
            state.complete_current_step("completed", confidence,
                                      [f"Final validation: {len(validation_issues)} issues"])
            
        except Exception as e:
            state.add_error(f"Final validation failed: {str(e)}")
            state.complete_current_step("failed")
        
        return state
    
    async def _prepare_response_node(self, state: LoanApplicationState) -> LoanApplicationState:
        """Prepare final response."""
        step = state.add_processing_step("prepare_response")
        
        try:
            # Calculate total processing time
            if state.processing_steps:
                start_time = state.processing_steps[0].start_time
                end_time = time.time()
                state.total_processing_time = end_time - start_time.timestamp()
            
            # Set final status if not already set
            if state.current_status == ProcessingStatus.DECISION_PENDING:
                if state.final_decision:
                    state.current_status = state.final_decision.decision or ProcessingStatus.REQUIRES_MANUAL_REVIEW
                else:
                    state.current_status = ProcessingStatus.REQUIRES_MANUAL_REVIEW
            
            state.complete_current_step("completed", 1.0, ["Response prepared"])
            logger.info(f"Completed processing for application {state.application_id}: {state.current_status.value}")
            
        except Exception as e:
            state.add_error(f"Response preparation failed: {str(e)}")
            state.complete_current_step("failed")
        
        return state
    
    # Retry handling nodes
    async def _handle_document_retry(self, state: LoanApplicationState) -> LoanApplicationState:
        """Handle document analysis retry."""
        state.total_retry_count += 1
        state.add_processing_step("document_retry")
        
        # Record fallback usage
        state.record_fallback({
            "type": "document_analysis_retry",
            "retry_count": state.total_retry_count,
            "reason": "Document analysis failed or incomplete"
        })
        
        state.complete_current_step("completed", 0.5, ["Preparing document analysis retry"])
        return state
    
    async def _handle_risk_retry(self, state: LoanApplicationState) -> LoanApplicationState:
        """Handle risk assessment retry."""
        state.total_retry_count += 1
        state.add_processing_step("risk_retry")
        
        state.record_fallback({
            "type": "risk_assessment_retry", 
            "retry_count": state.total_retry_count,
            "reason": "Risk assessment failed or incomplete"
        })
        
        state.complete_current_step("completed", 0.5, ["Preparing risk assessment retry"])
        return state
    
    async def _escalate_to_human(self, state: LoanApplicationState) -> LoanApplicationState:
        """Escalate to human review."""
        step = state.add_processing_step("human_escalation")
        
        state.current_status = ProcessingStatus.REQUIRES_MANUAL_REVIEW
        state.trigger_human_review("Automated processing failed - requires human intervention")
        
        # Record comprehensive fallback to human
        state.record_fallback({
            "type": "human_escalation",
            "reason": "All automated processing attempts failed",
            "errors": state.processing_errors,
            "retry_count": state.total_retry_count
        })
        
        state.complete_current_step("completed", 0.0, ["Escalated to human review"])
        logger.warning(f"Application {state.application_id} escalated to human review")
        
        return state
    
    # Conditional edge functions
    def _check_document_analysis_success(self, state: LoanApplicationState) -> Literal["success", "retry", "fail"]:
        """Check if document analysis was successful."""
        if not state.processing_steps:
            return "fail"
        
        latest_step = state.processing_steps[-1]
        
        if latest_step.status == "completed" and latest_step.confidence_score > 0.6:
            return "success"
        elif state.total_retry_count < 2:
            return "retry"
        else:
            return "fail"
    
    def _check_document_quality(self, state: LoanApplicationState) -> Literal["pass", "insufficient", "retry"]:
        """Check document analysis quality."""
        if state.quality_checks_failed > state.quality_checks_passed:
            if state.total_retry_count < 1:
                return "retry"
            else:
                return "insufficient"
        return "pass"
    
    def _should_retry_documents(self, state: LoanApplicationState) -> Literal["retry", "escalate"]:
        """Determine if document processing should be retried."""
        return "retry" if state.total_retry_count < 3 else "escalate"
    
    def _check_risk_assessment_success(self, state: LoanApplicationState) -> Literal["success", "retry", "fail"]:
        """Check if risk assessment was successful."""
        if state.risk_assessment and state.risk_assessment.overall_risk_level:
            return "success"
        elif state.total_retry_count < 2:
            return "retry"
        else:
            return "fail"
    
    def _check_risk_quality(self, state: LoanApplicationState) -> Literal["pass", "high_risk", "retry"]:
        """Check risk assessment quality."""
        if not state.risk_assessment:
            return "retry" if state.total_retry_count < 2 else "high_risk"
        
        if state.risk_assessment.overall_risk_level == RiskLevel.CRITICAL:
            return "high_risk"
        
        return "pass"
    
    def _should_retry_risk(self, state: LoanApplicationState) -> Literal["retry", "escalate"]:
        """Determine if risk assessment should be retried."""
        return "retry" if state.total_retry_count < 2 else "escalate"
    
    def _check_decision_quality(self, state: LoanApplicationState) -> Literal["valid", "requires_review", "retry"]:
        """Check decision quality."""
        if not state.final_decision:
            return "retry" if state.total_retry_count < 1 else "requires_review"
        
        if state.final_decision.manual_review_required:
            return "requires_review"
        
        if state.final_decision.confidence_score < 0.5:
            return "retry" if state.total_retry_count < 1 else "requires_review"
        
        return "valid"
    
    # Public interface
    async def process_loan_application(
        self,
        application_data: str,
        documents: Dict[str, str] = None,
        application_id: str = None
    ) -> LoanApplicationState:
        """
        Process a complete loan application through the workflow.
        
        Args:
            application_data: Raw application data/form
            documents: Dictionary of document_type -> content
            application_id: Optional application ID
            
        Returns:
            Final application state with decision
        """
        if not application_id:
            application_id = f"loan_app_{int(time.time())}"
        
        # Initialize state
        initial_state = LoanApplicationState(
            application_id=application_id,
            raw_application_data=application_data,
            documents=documents or {},
            current_status=ProcessingStatus.RECEIVED
        )
        
        logger.info(f"Starting loan application processing: {application_id}")
        
        try:
            # Run the complete workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Handle both object and dictionary returns
            if hasattr(final_state, 'current_status'):
                status = final_state.current_status.value if hasattr(final_state.current_status, 'value') else str(final_state.current_status)
            else:
                status = final_state.get('current_status', {})
                status = status.value if hasattr(status, 'value') else str(status)
            
            logger.info(f"Completed loan application processing: {application_id} -> {status}")
            
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow failed for application {application_id}: {e}")
            initial_state.add_error(f"Workflow execution failed: {str(e)}")
            initial_state.current_status = ProcessingStatus.REQUIRES_MANUAL_REVIEW
            return initial_state
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get overall workflow system status."""
        return self.fallback_chain.get_comprehensive_status()