"""Specialized nodes for loan application processing."""
import logging
import json
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from ..models.fallback_chain import EnhancedModelFallbackChain
from ..models.model_configs import ModelType
from ..workflows.loan_application_state import (
    LoanApplicationState, LoanType, RiskLevel, ProcessingStatus, 
    DecisionReason, ApplicantInfo, LoanDetails, RiskAssessment, DecisionResult
)

logger = logging.getLogger(__name__)


class LoanDocumentAnalyzer:
    """Analyzes loan application documents using multiple models."""
    
    def __init__(self, fallback_chain: EnhancedModelFallbackChain):
        self.fallback_chain = fallback_chain
    
    async def analyze_documents(self, state: LoanApplicationState) -> LoanApplicationState:
        """Analyze all provided documents."""
        step = state.add_processing_step("document_analysis")
        
        try:
            # Analyze each document type
            analysis_results = {}
            
            for doc_type, content in state.documents.items():
                logger.info(f"Analyzing document: {doc_type}")
                
                doc_analysis = await self._analyze_single_document(doc_type, content)
                analysis_results[doc_type] = doc_analysis
                
                if not doc_analysis.get('success', False):
                    state.add_warning(f"Failed to analyze {doc_type} document")
            
            # Extract consolidated information
            applicant_info, loan_details = await self._extract_consolidated_info(
                state.raw_application_data, 
                analysis_results
            )
            
            state.applicant_info = applicant_info
            state.loan_details = loan_details
            state.document_analysis_results = analysis_results
            
            # Determine if we have sufficient information
            completeness_score = self._assess_completeness(applicant_info, loan_details)
            
            if completeness_score < 0.7:
                state.add_warning("Incomplete application data")
                state.trigger_human_review("Insufficient information provided")
            
            state.complete_current_step("completed", completeness_score, 
                                      [f"Analyzed {len(state.documents)} documents"])
            
        except Exception as e:
            state.add_error(f"Document analysis failed: {str(e)}")
            state.complete_current_step("failed")
        
        return state
    
    async def _analyze_single_document(self, doc_type: str, content: str) -> Dict[str, Any]:
        """Analyze a single document."""
        prompt = self._create_document_analysis_prompt(doc_type, content)
        
        context = {
            "document_type": doc_type,
            "analysis_type": "loan_document"
        }
        
        result = await self.fallback_chain.invoke_with_comprehensive_fallbacks(
            ModelType.STANDARD,
            prompt,
            context
        )
        
        if result['success']:
            try:
                # Parse the analysis result
                analysis_data = self._parse_document_analysis(result['result'])
                return {
                    "success": True,
                    "analysis": analysis_data,
                    "confidence": result['confidence'],
                    "source": result['source']
                }
            except Exception as e:
                logger.error(f"Failed to parse {doc_type} analysis: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": "Analysis failed"}
    
    def _create_document_analysis_prompt(self, doc_type: str, content: str) -> str:
        """Create analysis prompt based on document type."""
        if doc_type in ["income_statement", "pay_stub", "tax_return"]:
            return f"""
Analyze this financial document and extract key information. Return JSON format:

Document Type: {doc_type}
Content: {content[:1500]}

Extract:
{{
    "annual_income": number or null,
    "monthly_income": number or null,
    "employment_status": "string",
    "employer_name": "string",
    "employment_duration": "string",
    "additional_income": number or null,
    "deductions": number or null
}}
"""
        
        elif doc_type in ["bank_statement"]:
            return f"""
Analyze this bank statement and extract financial patterns. Return JSON:

Content: {content[:1500]}

Extract:
{{
    "average_balance": number,
    "minimum_balance": number,
    "monthly_deposits": number,
    "monthly_withdrawals": number,
    "overdraft_incidents": number,
    "large_transactions": ["list of significant transactions"],
    "account_stability_months": number
}}
"""
        
        elif doc_type in ["credit_report"]:
            return f"""
Analyze this credit report and extract key metrics. Return JSON:

Content: {content[:1500]}

Extract:
{{
    "credit_score": number,
    "credit_accounts": number,
    "credit_utilization": number,
    "payment_history": "excellent|good|fair|poor",
    "derogatory_marks": number,
    "credit_age_years": number,
    "recent_inquiries": number
}}
"""
        
        else:
            return f"""
Analyze this loan application document and extract relevant information. Return JSON:

Document Type: {doc_type}
Content: {content[:1500]}

Extract any relevant information about:
- Personal information (name, age, contact)
- Financial information (income, debts, assets)
- Loan request details (amount, purpose, term)
- Employment information
- Any other relevant data

Return as JSON object.
"""
    
    def _parse_document_analysis(self, response: str) -> Dict[str, Any]:
        """Parse document analysis response."""
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback to simple key-value extraction
                return {"raw_analysis": response}
        except json.JSONDecodeError:
            return {"raw_analysis": response, "parse_error": True}
    
    async def _extract_consolidated_info(
        self, 
        raw_data: str, 
        analysis_results: Dict[str, Any]
    ) -> Tuple[ApplicantInfo, LoanDetails]:
        """Extract consolidated applicant and loan information."""
        
        # Create consolidation prompt
        prompt = f"""
Based on the loan application and document analysis, extract consolidated information:

Raw Application: {raw_data[:1000]}

Document Analysis Results:
{json.dumps(analysis_results, indent=2, default=str)[:2000]}

Extract and return JSON with two sections:
{{
    "applicant": {{
        "name": "string",
        "age": number or null,
        "employment_status": "string",
        "annual_income": number or null,
        "credit_score": number or null,
        "existing_debts": number or null,
        "employment_years": number or null,
        "phone": "string",
        "email": "string",
        "address": "string"
    }},
    "loan": {{
        "loan_type": "personal|mortgage|business|auto|student",
        "requested_amount": number,
        "loan_term_months": number,
        "purpose": "string",
        "collateral_description": "string or null",
        "collateral_value": number or null
    }}
}}
"""
        
        context = {"consolidation": True}
        result = await self.fallback_chain.invoke_with_comprehensive_fallbacks(
            ModelType.REASONING,
            prompt,
            context
        )
        
        try:
            if result['success']:
                data = json.loads(result['result'])
                
                # Create ApplicantInfo
                applicant_data = data.get('applicant', {})
                applicant = ApplicantInfo(**applicant_data)
                
                # Create LoanDetails
                loan_data = data.get('loan', {})
                if 'loan_type' in loan_data:
                    loan_data['loan_type'] = LoanType(loan_data['loan_type'])
                loan = LoanDetails(**loan_data)
                
                return applicant, loan
            else:
                # Return empty objects if extraction fails
                return ApplicantInfo(name="Unknown"), LoanDetails()
                
        except Exception as e:
            logger.error(f"Failed to consolidate information: {e}")
            return ApplicantInfo(name="Unknown"), LoanDetails()
    
    def _assess_completeness(self, applicant: ApplicantInfo, loan: LoanDetails) -> float:
        """Assess completeness of extracted information."""
        required_applicant_fields = ['name', 'annual_income', 'employment_status']
        required_loan_fields = ['loan_type', 'requested_amount']
        
        applicant_score = 0
        for field in required_applicant_fields:
            if getattr(applicant, field, None) is not None:
                applicant_score += 1
        
        loan_score = 0
        for field in required_loan_fields:
            if getattr(loan, field, None) is not None:
                loan_score += 1
        
        total_required = len(required_applicant_fields) + len(required_loan_fields)
        total_found = applicant_score + loan_score
        
        return total_found / total_required if total_required > 0 else 0.0


class RiskAssessmentEngine:
    """Assesses loan application risk using multiple models and criteria."""
    
    def __init__(self, fallback_chain: EnhancedModelFallbackChain):
        self.fallback_chain = fallback_chain
    
    async def assess_risk(self, state: LoanApplicationState) -> LoanApplicationState:
        """Perform comprehensive risk assessment."""
        step = state.add_processing_step("risk_assessment")
        
        try:
            # Calculate various risk metrics
            financial_risk = await self._assess_financial_risk(state)
            employment_risk = await self._assess_employment_risk(state)
            credit_risk = await self._assess_credit_risk(state)
            collateral_risk = await self._assess_collateral_risk(state)
            
            # Combine risk factors
            overall_risk = await self._combine_risk_factors(
                state, financial_risk, employment_risk, credit_risk, collateral_risk
            )
            
            state.risk_assessment = overall_risk
            
            risk_level_score = {
                RiskLevel.LOW: 0.9,
                RiskLevel.MEDIUM: 0.6,
                RiskLevel.HIGH: 0.3,
                RiskLevel.CRITICAL: 0.1
            }
            
            confidence = risk_level_score.get(overall_risk.overall_risk_level, 0.5)
            
            state.complete_current_step("completed", confidence, 
                                      [f"Risk level: {overall_risk.overall_risk_level.value}"])
            
            # Check if risk is too high
            if overall_risk.overall_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                state.trigger_human_review(f"High risk application: {overall_risk.overall_risk_level.value}")
        
        except Exception as e:
            state.add_error(f"Risk assessment failed: {str(e)}")
            state.complete_current_step("failed")
        
        return state
    
    async def _assess_financial_risk(self, state: LoanApplicationState) -> Dict[str, Any]:
        """Assess financial risk factors."""
        if not state.applicant_info or not state.loan_details:
            return {"error": "Insufficient data for financial assessment"}
        
        prompt = f"""
Assess financial risk for this loan application:

Applicant Income: ${state.applicant_info.annual_income}
Existing Debts: ${state.applicant_info.existing_debts}
Requested Loan: ${state.loan_details.requested_amount}
Loan Term: {state.loan_details.loan_term_months} months

Calculate and return JSON:
{{
    "debt_to_income_ratio": number,
    "payment_capacity_score": number (0-100),
    "loan_to_income_ratio": number,
    "risk_factors": ["list of concerns"],
    "mitigating_factors": ["list of positives"]
}}
"""
        
        result = await self.fallback_chain.invoke_with_comprehensive_fallbacks(
            ModelType.REASONING, prompt, {"assessment_type": "financial"}
        )
        
        try:
            return json.loads(result['result']) if result['success'] else {}
        except:
            return {"calculation_failed": True}
    
    async def _assess_employment_risk(self, state: LoanApplicationState) -> Dict[str, Any]:
        """Assess employment stability risk."""
        if not state.applicant_info:
            return {}
        
        prompt = f"""
Assess employment risk:

Employment Status: {state.applicant_info.employment_status}
Years of Employment: {state.applicant_info.employment_years}
Annual Income: ${state.applicant_info.annual_income}

Return JSON assessment:
{{
    "employment_stability_score": number (0-100),
    "income_stability": "stable|variable|unstable",
    "risk_factors": ["list"],
    "employment_risk_level": "low|medium|high"
}}
"""
        
        result = await self.fallback_chain.invoke_with_comprehensive_fallbacks(
            ModelType.STANDARD, prompt, {"assessment_type": "employment"}
        )
        
        try:
            return json.loads(result['result']) if result['success'] else {}
        except:
            return {}
    
    async def _assess_credit_risk(self, state: LoanApplicationState) -> Dict[str, Any]:
        """Assess credit-related risk."""
        credit_score = state.applicant_info.credit_score if state.applicant_info else None
        
        if not credit_score:
            return {"credit_data_missing": True}
        
        # Simple credit risk assessment
        if credit_score >= 750:
            risk_level = "low"
            score = 90
        elif credit_score >= 700:
            risk_level = "low"
            score = 75
        elif credit_score >= 650:
            risk_level = "medium"
            score = 60
        elif credit_score >= 600:
            risk_level = "medium"
            score = 45
        else:
            risk_level = "high"
            score = 30
        
        return {
            "credit_risk_score": score,
            "credit_risk_level": risk_level,
            "credit_score": credit_score
        }
    
    async def _assess_collateral_risk(self, state: LoanApplicationState) -> Dict[str, Any]:
        """Assess collateral-related risk."""
        if not state.loan_details or not state.loan_details.collateral_value:
            return {"no_collateral": True}
        
        collateral_value = state.loan_details.collateral_value
        loan_amount = state.loan_details.requested_amount
        
        if loan_amount and collateral_value:
            coverage_ratio = float(collateral_value) / float(loan_amount)
            
            return {
                "collateral_coverage_ratio": coverage_ratio,
                "adequate_collateral": coverage_ratio >= 1.2,
                "collateral_risk_level": "low" if coverage_ratio >= 1.5 else 
                                       "medium" if coverage_ratio >= 1.2 else "high"
            }
        
        return {}
    
    async def _combine_risk_factors(
        self, 
        state: LoanApplicationState,
        financial_risk: Dict,
        employment_risk: Dict, 
        credit_risk: Dict,
        collateral_risk: Dict
    ) -> RiskAssessment:
        """Combine all risk factors into overall assessment."""
        
        prompt = f"""
Combine these risk assessments into overall loan risk evaluation:

Financial Risk: {json.dumps(financial_risk, indent=2)}
Employment Risk: {json.dumps(employment_risk, indent=2)}
Credit Risk: {json.dumps(credit_risk, indent=2)}
Collateral Risk: {json.dumps(collateral_risk, indent=2)}

Return JSON:
{{
    "overall_risk_level": "low|medium|high|critical",
    "risk_score": number (0-100, where 100 is highest risk),
    "key_risk_factors": ["list of main concerns"],
    "mitigating_factors": ["list of positive factors"],
    "debt_to_income_ratio": number,
    "payment_capacity_score": number (0-100)
}}
"""
        
        result = await self.fallback_chain.invoke_with_comprehensive_fallbacks(
            ModelType.REASONING, prompt, {"assessment_type": "overall_risk"}
        )
        
        try:
            if result['success']:
                data = json.loads(result['result'])
                
                risk_level_map = {
                    "low": RiskLevel.LOW,
                    "medium": RiskLevel.MEDIUM,
                    "high": RiskLevel.HIGH,
                    "critical": RiskLevel.CRITICAL
                }
                
                return RiskAssessment(
                    overall_risk_level=risk_level_map.get(data.get('overall_risk_level', 'medium'), RiskLevel.MEDIUM),
                    risk_score=data.get('risk_score', 50.0),
                    risk_factors=data.get('key_risk_factors', []),
                    mitigating_factors=data.get('mitigating_factors', []),
                    debt_to_income_ratio=data.get('debt_to_income_ratio'),
                    payment_capacity_score=data.get('payment_capacity_score', 50.0),
                    collateral_coverage_ratio=collateral_risk.get('collateral_coverage_ratio')
                )
            else:
                # Fallback risk assessment
                return RiskAssessment(
                    overall_risk_level=RiskLevel.MEDIUM,
                    risk_score=50.0,
                    risk_factors=["Assessment failed - manual review required"],
                    payment_capacity_score=50.0
                )
                
        except Exception as e:
            logger.error(f"Failed to combine risk factors: {e}")
            return RiskAssessment(
                overall_risk_level=RiskLevel.HIGH,
                risk_score=75.0,
                risk_factors=[f"Risk calculation error: {str(e)}"],
                payment_capacity_score=25.0
            )


class LoanDecisionEngine:
    """Makes final loan approval decisions based on all assessments."""
    
    def __init__(self, fallback_chain: EnhancedModelFallbackChain):
        self.fallback_chain = fallback_chain
    
    async def make_decision(self, state: LoanApplicationState) -> LoanApplicationState:
        """Make final loan decision."""
        step = state.add_processing_step("loan_decision")
        
        try:
            # Use model voting for critical decisions
            decision = await self._make_decision_with_voting(state)
            state.final_decision = decision
            
            # Determine final status
            if decision.decision == ProcessingStatus.APPROVED:
                state.current_status = ProcessingStatus.APPROVED
            elif decision.decision == ProcessingStatus.CONDITIONALLY_APPROVED:
                state.current_status = ProcessingStatus.CONDITIONALLY_APPROVED
            elif decision.manual_review_required:
                state.current_status = ProcessingStatus.REQUIRES_MANUAL_REVIEW
            else:
                state.current_status = ProcessingStatus.DECLINED
            
            state.complete_current_step("completed", decision.confidence_score,
                                      [f"Decision: {decision.decision.value if decision.decision else 'pending'}"])
        
        except Exception as e:
            state.add_error(f"Decision making failed: {str(e)}")
            state.complete_current_step("failed")
            state.current_status = ProcessingStatus.REQUIRES_MANUAL_REVIEW
        
        return state
    
    async def _make_decision_with_voting(self, state: LoanApplicationState) -> DecisionResult:
        """Make decision using model voting for higher accuracy."""
        
        # Prepare decision context
        context_summary = self._prepare_decision_context(state)
        
        # Use available models for voting
        available_models = [ModelType.REASONING, ModelType.STANDARD]
        
        voting_result = await self.fallback_chain.invoke_with_model_voting(
            f"""
Based on this complete loan application analysis, make a final decision:

{context_summary}

Return JSON decision:
{{
    "decision": "approved|conditionally_approved|declined",
    "approved_amount": number or null,
    "interest_rate": number or null,
    "loan_term_months": number or null,
    "conditions": ["list of conditions if conditionally approved"],
    "decline_reasons": ["list of reasons if declined"],
    "confidence_score": number (0-1),
    "manual_review_required": boolean,
    "reasoning": "explanation of decision"
}}
""",
            available_models,
            {"decision_type": "loan_approval"}
        )
        
        try:
            if voting_result['success']:
                decision_data = json.loads(voting_result['result'])
                
                # Map decision string to enum
                decision_map = {
                    "approved": ProcessingStatus.APPROVED,
                    "conditionally_approved": ProcessingStatus.CONDITIONALLY_APPROVED,
                    "declined": ProcessingStatus.DECLINED
                }
                
                # Map decline reasons to enum values
                reason_map = {
                    "insufficient_income": DecisionReason.INSUFFICIENT_INCOME,
                    "poor_credit": DecisionReason.POOR_CREDIT_HISTORY,
                    "high_debt": DecisionReason.HIGH_DEBT_TO_INCOME,
                    "incomplete_docs": DecisionReason.INCOMPLETE_DOCUMENTATION,
                    "approved": DecisionReason.MEETS_ALL_CRITERIA,
                    "conditional": DecisionReason.REQUIRES_CONDITIONS
                }
                
                reasons = []
                if decision_data.get('decline_reasons'):
                    for reason_text in decision_data['decline_reasons']:
                        # Simple mapping - in production would be more sophisticated
                        if 'income' in reason_text.lower():
                            reasons.append(DecisionReason.INSUFFICIENT_INCOME)
                        elif 'credit' in reason_text.lower():
                            reasons.append(DecisionReason.POOR_CREDIT_HISTORY)
                        elif 'debt' in reason_text.lower():
                            reasons.append(DecisionReason.HIGH_DEBT_TO_INCOME)
                
                if not reasons:
                    if decision_data.get('decision') == 'approved':
                        reasons = [DecisionReason.MEETS_ALL_CRITERIA]
                    elif decision_data.get('decision') == 'conditionally_approved':
                        reasons = [DecisionReason.REQUIRES_CONDITIONS]
                
                return DecisionResult(
                    decision=decision_map.get(decision_data.get('decision', 'declined'), ProcessingStatus.DECLINED),
                    approved_amount=Decimal(str(decision_data.get('approved_amount', 0))) if decision_data.get('approved_amount') else None,
                    interest_rate=decision_data.get('interest_rate'),
                    loan_term=decision_data.get('loan_term_months'),
                    conditions=decision_data.get('conditions', []),
                    reasons=reasons,
                    confidence_score=decision_data.get('confidence_score', 0.5),
                    manual_review_required=decision_data.get('manual_review_required', False),
                    expiry_date=datetime.now() + timedelta(days=30)  # Decision valid for 30 days
                )
            else:
                # Fallback decision
                return DecisionResult(
                    decision=ProcessingStatus.REQUIRES_MANUAL_REVIEW,
                    reasons=[DecisionReason.INCOMPLETE_DOCUMENTATION],
                    confidence_score=0.0,
                    manual_review_required=True
                )
                
        except Exception as e:
            logger.error(f"Failed to parse decision result: {e}")
            return DecisionResult(
                decision=ProcessingStatus.REQUIRES_MANUAL_REVIEW,
                reasons=[DecisionReason.POLICY_VIOLATION],
                confidence_score=0.0,
                manual_review_required=True
            )
    
    def _prepare_decision_context(self, state: LoanApplicationState) -> str:
        """Prepare comprehensive context for decision making."""
        context_parts = []
        
        # Application summary
        if state.applicant_info:
            context_parts.append(f"""
APPLICANT INFORMATION:
- Name: {state.applicant_info.name}
- Age: {state.applicant_info.age}
- Annual Income: ${state.applicant_info.annual_income}
- Credit Score: {state.applicant_info.credit_score}
- Employment: {state.applicant_info.employment_status}
- Years Employed: {state.applicant_info.employment_years}
- Existing Debts: ${state.applicant_info.existing_debts}
""")
        
        # Loan details
        if state.loan_details:
            context_parts.append(f"""
LOAN REQUEST:
- Type: {state.loan_details.loan_type.value if state.loan_details.loan_type else 'Unknown'}
- Amount: ${state.loan_details.requested_amount}
- Term: {state.loan_details.loan_term_months} months
- Purpose: {state.loan_details.purpose}
- Collateral: {state.loan_details.collateral_description} (${state.loan_details.collateral_value})
""")
        
        # Risk assessment
        if state.risk_assessment:
            context_parts.append(f"""
RISK ASSESSMENT:
- Overall Risk Level: {state.risk_assessment.overall_risk_level.value}
- Risk Score: {state.risk_assessment.risk_score}/100
- Debt-to-Income Ratio: {state.risk_assessment.debt_to_income_ratio}
- Payment Capacity Score: {state.risk_assessment.payment_capacity_score}/100
- Key Risk Factors: {', '.join(state.risk_assessment.risk_factors)}
- Mitigating Factors: {', '.join(state.risk_assessment.mitigating_factors)}
""")
        
        # Processing notes
        if state.processing_errors:
            context_parts.append(f"PROCESSING ERRORS: {'; '.join(state.processing_errors)}")
        
        if state.warnings:
            context_parts.append(f"WARNINGS: {'; '.join(state.warnings)}")
        
        return '\n'.join(context_parts)