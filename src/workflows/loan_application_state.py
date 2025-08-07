"""State definitions for complex loan application processing workflow."""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


class LoanType(Enum):
    """Types of loan applications."""
    PERSONAL = "personal"
    MORTGAGE = "mortgage"
    BUSINESS = "business"
    AUTO = "auto"
    STUDENT = "student"


class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcessingStatus(Enum):
    """Status of loan application processing."""
    RECEIVED = "received"
    DOCUMENT_ANALYSIS = "document_analysis"
    IDENTITY_VERIFICATION = "identity_verification"
    FINANCIAL_ASSESSMENT = "financial_assessment"
    RISK_EVALUATION = "risk_evaluation"
    CREDIT_CHECK = "credit_check"
    COLLATERAL_ASSESSMENT = "collateral_assessment"
    UNDERWRITER_REVIEW = "underwriter_review"
    DECISION_PENDING = "decision_pending"
    APPROVED = "approved"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    DECLINED = "declined"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class DecisionReason(Enum):
    """Reasons for loan decisions."""
    INSUFFICIENT_INCOME = "insufficient_income"
    POOR_CREDIT_HISTORY = "poor_credit_history"
    HIGH_DEBT_TO_INCOME = "high_debt_to_income"
    INCOMPLETE_DOCUMENTATION = "incomplete_documentation"
    COLLATERAL_INSUFFICIENT = "collateral_insufficient"
    EMPLOYMENT_UNSTABLE = "employment_unstable"
    MEETS_ALL_CRITERIA = "meets_all_criteria"
    REQUIRES_CONDITIONS = "requires_conditions"
    FRAUD_SUSPECTED = "fraud_suspected"
    POLICY_VIOLATION = "policy_violation"


@dataclass
class ApplicantInfo(BaseModel):
    """Applicant information."""
    name: str
    age: Optional[int] = None
    employment_status: Optional[str] = None
    annual_income: Optional[Decimal] = None
    credit_score: Optional[int] = None
    existing_debts: Optional[Decimal] = None
    employment_years: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


@dataclass
class LoanDetails(BaseModel):
    """Loan request details."""
    loan_type: Optional[LoanType] = None
    requested_amount: Optional[Decimal] = None
    loan_term_months: Optional[int] = None
    purpose: Optional[str] = None
    collateral_description: Optional[str] = None
    collateral_value: Optional[Decimal] = None


@dataclass
class ProcessingStep(BaseModel):
    """Individual processing step record."""
    step_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "in_progress"
    model_used: Optional[str] = None
    confidence_score: float = 0.0
    notes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    retry_count: int = 0


@dataclass
class RiskAssessment(BaseModel):
    """Risk assessment results."""
    overall_risk_level: Optional[RiskLevel] = None
    risk_score: float = 0.0  # 0-100 scale
    risk_factors: List[str] = Field(default_factory=list)
    mitigating_factors: List[str] = Field(default_factory=list)
    debt_to_income_ratio: Optional[float] = None
    payment_capacity_score: float = 0.0
    collateral_coverage_ratio: Optional[float] = None


@dataclass
class DecisionResult(BaseModel):
    """Final decision result."""
    decision: Optional[ProcessingStatus] = None
    approved_amount: Optional[Decimal] = None
    interest_rate: Optional[float] = None
    loan_term: Optional[int] = None
    conditions: List[str] = Field(default_factory=list)
    reasons: List[DecisionReason] = Field(default_factory=list)
    confidence_score: float = 0.0
    manual_review_required: bool = False
    expiry_date: Optional[datetime] = None


class LoanApplicationState(BaseModel):
    """Complete state for loan application processing."""
    
    # Application metadata
    application_id: str
    submission_time: datetime = Field(default_factory=datetime.now)
    current_status: ProcessingStatus = ProcessingStatus.RECEIVED
    
    # Input documents and data
    documents: Dict[str, str] = Field(default_factory=dict)  # document_type -> content
    raw_application_data: str = ""
    
    # Extracted information
    applicant_info: Optional[ApplicantInfo] = None
    loan_details: Optional[LoanDetails] = None
    
    # Processing tracking
    processing_steps: List[ProcessingStep] = Field(default_factory=list)
    current_step: Optional[str] = None
    total_processing_time: float = 0.0
    
    # Analysis results
    document_analysis_results: Dict[str, Any] = Field(default_factory=dict)
    identity_verification_result: Optional[Dict[str, Any]] = None
    financial_assessment: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[RiskAssessment] = None
    credit_check_results: Optional[Dict[str, Any]] = None
    collateral_assessment: Optional[Dict[str, Any]] = None
    
    # Decision and output
    underwriter_notes: List[str] = Field(default_factory=list)
    final_decision: Optional[DecisionResult] = None
    
    # System metadata
    models_used: List[str] = Field(default_factory=list)
    fallback_instances: List[Dict[str, Any]] = Field(default_factory=list)
    total_retry_count: int = 0
    quality_checks_passed: int = 0
    quality_checks_failed: int = 0
    
    # Error handling
    processing_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    human_review_triggers: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
    
    def add_processing_step(self, step_name: str, model_used: str = None) -> ProcessingStep:
        """Add a new processing step and return it."""
        step = ProcessingStep(
            step_name=step_name,
            start_time=datetime.now(),
            model_used=model_used
        )
        self.processing_steps.append(step)
        self.current_step = step_name
        
        if model_used and model_used not in self.models_used:
            self.models_used.append(model_used)
        
        return step
    
    def complete_current_step(self, status: str = "completed", confidence: float = 0.0, notes: List[str] = None):
        """Complete the current processing step."""
        if self.processing_steps:
            current = self.processing_steps[-1]
            current.end_time = datetime.now()
            current.status = status
            current.confidence_score = confidence
            if notes:
                current.notes.extend(notes)
    
    def add_error(self, error_message: str, step_name: str = None):
        """Add an error to the current step and global errors."""
        self.processing_errors.append(f"[{step_name or self.current_step}] {error_message}")
        
        if self.processing_steps and (not step_name or step_name == self.current_step):
            self.processing_steps[-1].errors.append(error_message)
    
    def add_warning(self, warning_message: str):
        """Add a warning."""
        self.warnings.append(f"[{self.current_step}] {warning_message}")
    
    def trigger_human_review(self, reason: str):
        """Trigger human review with reason."""
        self.human_review_triggers.append(f"[{self.current_step}] {reason}")
        if self.final_decision:
            self.final_decision.manual_review_required = True
    
    def record_fallback(self, fallback_info: Dict[str, Any]):
        """Record fallback usage."""
        fallback_info.update({
            "step": self.current_step,
            "timestamp": datetime.now().isoformat()
        })
        self.fallback_instances.append(fallback_info)
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing status."""
        completed_steps = [s for s in self.processing_steps if s.status == "completed"]
        failed_steps = [s for s in self.processing_steps if s.status == "failed"]
        
        return {
            "application_id": self.application_id,
            "current_status": self.current_status.value,
            "steps_completed": len(completed_steps),
            "steps_failed": len(failed_steps),
            "total_steps": len(self.processing_steps),
            "processing_time": self.total_processing_time,
            "models_used": self.models_used,
            "retry_count": self.total_retry_count,
            "fallback_count": len(self.fallback_instances),
            "error_count": len(self.processing_errors),
            "warning_count": len(self.warnings),
            "human_review_required": len(self.human_review_triggers) > 0 or 
                                   (self.final_decision and self.final_decision.manual_review_required)
        }