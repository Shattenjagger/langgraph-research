"""Фаза 6: Сложный многомодельный рабочий процесс обработки кредитных заявок."""
import asyncio
import logging
import json
import time
import sys
from pathlib import Path
from decimal import Decimal

# Добавляем корневую папку проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.local_model_manager import LocalModelManager
from src.workflows.complex_loan_workflow import ComplexLoanProcessingWorkflow

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Комплексные тестовые кредитные заявки
LOAN_APPLICATION_SCENARIOS = {
    "high_quality_personal": {
        "description": "Высококачественная заявка на личный кредит - должна быть одобрена",
        "application_data": """
Personal Loan Application

Applicant Information:
- Full Name: Sarah Johnson
- Age: 32
- Phone: (555) 123-4567
- Email: sarah.johnson@email.com
- Address: 123 Main Street, Anytown, ST 12345

Employment Information:
- Employment Status: Full-time employed
- Employer: Tech Solutions Inc.
- Position: Senior Software Engineer
- Years with employer: 4
- Annual Income: $95,000
- Employment Type: Permanent

Financial Information:
- Monthly Income: $7,900
- Existing monthly debt payments: $1,200
- Credit Score: 750
- Bank Account: Checking and Savings with ABC Bank
- Other assets: 401k ($45,000), Stock portfolio ($15,000)

Loan Request:
- Loan Type: Personal
- Requested Amount: $25,000
- Purpose: Home improvement and debt consolidation
- Preferred Term: 36 months
""",
        "documents": {
            "pay_stub": """
PAY STATEMENT
Tech Solutions Inc.
Pay Period: 01/01/2024 - 01/15/2024

Employee: Sarah Johnson
Position: Senior Software Engineer

EARNINGS:
Regular Pay (80 hrs @ $45.67/hr): $3,653.60
Overtime (5 hrs @ $68.51/hr): $342.55
Bonus: $500.00
Total Gross Pay: $4,496.15

DEDUCTIONS:
Federal Tax: $718.38
State Tax: $179.59
Social Security: $278.76
Medicare: $65.19
401k: $359.69
Health Insurance: $125.00
Total Deductions: $1,726.61

NET PAY: $2,769.54
YTD Gross: $8,992.30
YTD Net: $5,539.08
""",
            "bank_statement": """
ABC BANK - CHECKING ACCOUNT STATEMENT
Account: ****1234
Statement Period: 12/01/2023 - 12/31/2023

Beginning Balance: $8,450.23

DEPOSITS:
12/15/2023 - Direct Deposit - Tech Solutions Inc - $2,769.54
12/31/2023 - Direct Deposit - Tech Solutions Inc - $2,769.54
Total Deposits: $5,539.08

WITHDRAWALS:
12/01/2023 - Mortgage Payment - First National Bank - $1,850.00
12/05/2023 - Car Payment - Auto Finance Co - $425.00
12/10/2023 - Credit Card Payment - Visa ****5678 - $300.00
12/15/2023 - Utilities - Electric/Gas - $145.78
12/20/2023 - Groceries - Various - $520.45
12/25/2023 - Insurance - Auto/Home - $280.00
Total Withdrawals: $3,521.23

Ending Balance: $10,468.08
Average Daily Balance: $9,125.45
""",
            "credit_report": """
CREDIT REPORT SUMMARY
Report Date: January 2024
Credit Score: 750 (Excellent)

ACCOUNT SUMMARY:
Total Accounts: 8
Open Accounts: 6
Closed Accounts: 2

CREDIT UTILIZATION:
Total Credit Limit: $35,000
Total Balance: $4,200
Utilization Rate: 12%

PAYMENT HISTORY:
On-time payments: 98%
Late payments (30 days): 1 (over 2 years ago)
Late payments (60+ days): 0
Bankruptcies: 0
Foreclosures: 0

CREDIT AGE:
Average Account Age: 6.5 years
Oldest Account: 12 years
Newest Account: 8 months

RECENT ACTIVITY:
Hard Inquiries (24 months): 2
New Accounts (24 months): 1
"""
        },
        "expected_outcome": "approved"  # одобрена
    },
    
    "risky_business_loan": {
        "description": "Рискованный бизнес-кредит - должен требовать ручного рассмотрения",
        "application_data": """
Business Loan Application

Business Information:
- Business Name: StartUp Innovations LLC
- Business Type: Technology Startup
- Years in Business: 1.5
- Industry: Software Development
- Business Address: 456 Startup Ave, Innovation City, ST 54321

Applicant (Owner) Information:
- Full Name: Michael Chen
- Age: 28
- Ownership Percentage: 85%
- Role: CEO/Founder
- Phone: (555) 987-6543
- Email: michael@startupinnovations.com

Financial Information:
- Annual Business Revenue: $180,000
- Monthly Revenue (average): $15,000
- Annual Business Expenses: $165,000
- Personal Annual Income: $45,000
- Personal Credit Score: 680
- Existing Business Debts: $25,000

Loan Request:
- Loan Type: Business
- Requested Amount: $150,000
- Purpose: Equipment purchase and working capital
- Preferred Term: 60 months
- Collateral: Business equipment and inventory (estimated value: $75,000)
""",
        "documents": {
            "business_financials": """
PROFIT & LOSS STATEMENT
StartUp Innovations LLC
Year Ending December 31, 2023

REVENUE:
Software Development Services: $165,000
Consulting Services: $15,000
Total Revenue: $180,000

EXPENSES:
Salaries & Benefits: $85,000
Office Rent: $24,000
Equipment & Software: $18,000
Marketing & Advertising: $12,000
Utilities & Communications: $6,000
Professional Services: $8,000
Insurance: $4,500
Other Expenses: $7,500
Total Expenses: $165,000

NET INCOME: $15,000

CASH FLOW:
Operating Cash Flow: $22,000
Investing Cash Flow: -$35,000
Financing Cash Flow: $18,000
Net Cash Flow: $5,000
""",
            "personal_credit_report": """
PERSONAL CREDIT REPORT
Michael Chen
Report Date: January 2024
Credit Score: 680 (Good)

ACCOUNT SUMMARY:
Total Accounts: 12
Open Accounts: 8
Closed Accounts: 4

PAYMENT HISTORY:
On-time payments: 88%
Late payments (30 days): 6
Late payments (60 days): 2
Bankruptcies: 0

CREDIT UTILIZATION:
Total Credit Limit: $22,000
Total Balance: $12,500
Utilization Rate: 57%

DEROGATORY MARKS:
Collection Account: $850 (Medical - Paid)
Charge-off: Credit Card - $2,500 (3 years ago)

RECENT ACTIVITY:
Hard Inquiries (24 months): 8
New Accounts (24 months): 3
"""
        },
        "expected_outcome": "manual_review"  # ручное рассмотрение
    },
    
    "insufficient_income": {
        "description": "Заявка с недостаточным доходом - должна быть отклонена", 
        "application_data": """
Personal Loan Application

Applicant Information:
- Full Name: Robert Martinez
- Age: 45
- Phone: (555) 456-7890
- Email: robert.martinez@email.com
- Address: 789 Oak Street, Smalltown, ST 67890

Employment Information:
- Employment Status: Part-time
- Employer: Retail Store
- Position: Sales Associate
- Years with employer: 2
- Annual Income: $22,000
- Employment Type: Hourly

Financial Information:
- Monthly Income: $1,833
- Existing monthly debt payments: $1,650
- Credit Score: 620
- Bank Account: Checking with XYZ Credit Union

Loan Request:
- Loan Type: Personal
- Requested Amount: $15,000
- Purpose: Medical expenses
- Preferred Term: 48 months
""",
        "documents": {
            "pay_stub": """
RETAIL STORE PAY STATEMENT
Pay Period: 01/01/2024 - 01/15/2024

Employee: Robert Martinez
Position: Sales Associate (Part-time)

EARNINGS:
Regular Pay (32 hrs @ $12.00/hr): $384.00
Total Gross Pay: $384.00

DEDUCTIONS:
Federal Tax: $38.40
State Tax: $15.36
Social Security: $23.81
Medicare: $5.57
Total Deductions: $83.14

NET PAY: $300.86
YTD Gross: $768.00
YTD Net: $601.72
""",
            "debt_summary": """
MONTHLY DEBT OBLIGATIONS

Credit Cards:
- Visa ****1234: Minimum payment $125, Balance $4,200
- MasterCard ****5678: Minimum payment $85, Balance $2,800

Loans:
- Auto Loan: Monthly payment $385, Balance $12,500
- Student Loan: Monthly payment $180, Balance $8,900

Other:
- Medical Payment Plan: $75/month
- Personal Loan (family): $200/month

Total Monthly Debt Payments: $1,050

Rent: $600/month
Total Fixed Monthly Obligations: $1,650
""",
        },
        "expected_outcome": "declined"  # отклонена
    }
}


async def process_loan_application(workflow: ComplexLoanProcessingWorkflow, scenario_name: str, scenario: dict):
    """Обработка одного сценария кредитной заявки."""
    print(f"\n{'='*80}")
    print(f"ОБРАБОТКА КРЕДИТНОЙ ЗАЯВКИ: {scenario_name.upper()}")
    print(f"Описание: {scenario['description']}")
    print(f"Ожидаемый результат: {scenario['expected_outcome']}")
    print(f"{'='*80}")
    
    try:
        start_time = time.time()
        
        # Process the loan application
        result = await workflow.process_loan_application(
            application_data=scenario["application_data"],
            documents=scenario["documents"],
            application_id=f"test_{scenario_name}"
        )
        
        processing_time = time.time() - start_time
        
        # Helper functions for safe attribute access
        def safe_get(obj, key, default=None):
            if hasattr(obj, 'get'):
                return obj.get(key, default)
            else:
                return getattr(obj, key, default)
        
        def safe_get_value(obj):
            if hasattr(obj, 'value'):
                return obj.value
            else:
                return str(obj) if obj else "unknown"
        
        # Отображение комплексных результатов
        print(f"\n📊 РЕЗУЛЬТАТЫ ОБРАБОТКИ:")
        print(f"   ID заявки: {safe_get(result, 'application_id', 'Unknown')}")
        
        current_status = safe_get(result, 'current_status')
        status_str = safe_get_value(current_status)
        print(f"   Финальный статус: {status_str}")
        print(f"   Общее время обработки: {processing_time:.2f}с")
        
        # Информация о заявителе
        applicant_info = safe_get(result, 'applicant_info')
        if applicant_info:
            print(f"\n👤 ПРОФИЛЬ ЗАЯВИТЕЛЯ:")
            print(f"   Имя: {safe_get(applicant_info, 'name', 'N/A')}")
            print(f"   Возраст: {safe_get(applicant_info, 'age', 'N/A')}")
            print(f"   Годовой доход: ${safe_get(applicant_info, 'annual_income', 'N/A')}")
            print(f"   Кредитный рейтинг: {safe_get(applicant_info, 'credit_score', 'N/A')}")
            print(f"   Трудоустройство: {safe_get(applicant_info, 'employment_status', 'N/A')}")
        
        # Show loan details
        loan_details = safe_get(result, 'loan_details')
        if loan_details:
            print(f"\n💰 LOAN REQUEST:")
            loan_type = safe_get(loan_details, 'loan_type')
            print(f"   Type: {safe_get_value(loan_type)}")
            print(f"   Amount: ${safe_get(loan_details, 'requested_amount', 'N/A')}")
            print(f"   Term: {safe_get(loan_details, 'loan_term_months', 'N/A')} months")
            print(f"   Purpose: {safe_get(loan_details, 'purpose', 'N/A')}")
        
        # Show risk assessment
        risk_assessment = safe_get(result, 'risk_assessment')
        if risk_assessment:
            print(f"\n⚖️ RISK ASSESSMENT:")
            risk_level = safe_get(risk_assessment, 'overall_risk_level')
            print(f"   Risk Level: {safe_get_value(risk_level)}")
            print(f"   Risk Score: {safe_get(risk_assessment, 'risk_score', 0):.1f}/100")
            debt_ratio = safe_get(risk_assessment, 'debt_to_income_ratio')
            if debt_ratio:
                print(f"   Debt-to-Income Ratio: {debt_ratio:.2%}")
            else:
                print("   Debt-to-Income Ratio: Not calculated")
            print(f"   Payment Capacity: {safe_get(risk_assessment, 'payment_capacity_score', 0):.1f}/100")
            
            risk_factors = safe_get(risk_assessment, 'risk_factors', [])
            if risk_factors:
                print(f"   Risk Factors: {', '.join(risk_factors[:3])}")
            
            mitigating_factors = safe_get(risk_assessment, 'mitigating_factors', [])
            if mitigating_factors:
                print(f"   Mitigating Factors: {', '.join(mitigating_factors[:3])}")
        
        # Show final decision
        final_decision = safe_get(result, 'final_decision')
        if final_decision:
            print(f"\n🎯 FINAL DECISION:")
            decision = safe_get(final_decision, 'decision')
            print(f"   Decision: {safe_get_value(decision) if decision else 'Pending'}")
            print(f"   Confidence: {safe_get(final_decision, 'confidence_score', 0):.2f}")
            
            decision_value = safe_get_value(decision) if decision else ''
            if decision_value in ['approved', 'conditionally_approved']:
                print(f"   Approved Amount: ${safe_get(final_decision, 'approved_amount', 'N/A')}")
                print(f"   Interest Rate: {safe_get(final_decision, 'interest_rate', 'N/A')}%")
                print(f"   Term: {safe_get(final_decision, 'loan_term', 'N/A')} months")
                
                conditions = safe_get(final_decision, 'conditions', [])
                if conditions:
                    print(f"   Conditions: {', '.join(conditions)}")
            
            reasons = safe_get(final_decision, 'reasons', [])
            if reasons:
                reasons_text = ', '.join([safe_get_value(r) for r in reasons])
                print(f"   Reasons: {reasons_text}")
            
            if safe_get(final_decision, 'manual_review_required', False):
                print(f"   🚨 Manual Review Required")
        
        # Show processing details
        print(f"\n⚙️ PROCESSING DETAILS:")
        processing_steps = safe_get(result, 'processing_steps', [])
        print(f"   Steps Completed: {len([s for s in processing_steps if safe_get(s, 'status') == 'completed'])}")
        print(f"   Steps Failed: {len([s for s in processing_steps if safe_get(s, 'status') == 'failed'])}")
        print(f"   Models Used: {', '.join(safe_get(result, 'models_used', []))}")
        print(f"   Total Retries: {safe_get(result, 'total_retry_count', 0)}")
        print(f"   Fallback Instances: {len(safe_get(result, 'fallback_instances', []))}")
        print(f"   Quality Checks Passed: {safe_get(result, 'quality_checks_passed', 0)}")
        print(f"   Quality Checks Failed: {safe_get(result, 'quality_checks_failed', 0)}")
        
        # Show errors and warnings
        processing_errors = safe_get(result, 'processing_errors', [])
        if processing_errors:
            print(f"\n❌ PROCESSING ERRORS ({len(processing_errors)}):")
            for error in processing_errors[:3]:  # Show first 3
                print(f"   - {error}")
            if len(processing_errors) > 3:
                print(f"   ... and {len(processing_errors) - 3} more errors")
        
        warnings = safe_get(result, 'warnings', [])
        if warnings:
            print(f"\n⚠️ WARNINGS ({len(warnings)}):")
            for warning in warnings[:3]:  # Show first 3
                print(f"   - {warning}")
        
        human_review_triggers = safe_get(result, 'human_review_triggers', [])
        if human_review_triggers:
            print(f"\n👨‍💼 HUMAN REVIEW TRIGGERS:")
            for trigger in human_review_triggers:
                print(f"   - {trigger}")
        
        # Show processing timeline
        print(f"\n⏱️ PROCESSING TIMELINE:")
        for i, step in enumerate(processing_steps[-5:], 1):  # Show last 5 steps
            step_status = safe_get(step, 'status', 'unknown')
            step_name = safe_get(step, 'step_name', 'Unknown Step')
            status_emoji = {"completed": "+", "failed": "-", "in_progress": "+"}.get(step_status, "?")
            duration = ""
            end_time = safe_get(step, 'end_time')
            start_time = safe_get(step, 'start_time')
            if end_time and start_time:
                duration = f" ({(end_time - start_time).total_seconds():.1f}s)"
            print(f"   {i}. {status_emoji} {step_name}{duration}")
        
        # Compare with expected outcome
        expected = scenario['expected_outcome']
        actual = safe_get_value(current_status)
        
        outcome_match = (
            (expected == "approved" and actual == "approved") or
            (expected == "declined" and actual == "declined") or
            (expected == "manual_review" and actual == "requires_manual_review")
        )

        print(f"\n OUTCOME ASSESSMENT:")
        print(f"   Expected: {expected}")
        print(f"   Actual: {actual}")
        print(f"   Match: {'Yes' if outcome_match else 'No'}")
        
        return {
            "scenario": scenario_name,
            "expected": expected,
            "actual": actual,
            "match": outcome_match,
            "processing_time": processing_time,
            "steps_completed": len([s for s in processing_steps if safe_get(s, 'status') == 'completed']),
            "retries": safe_get(result, 'total_retry_count', 0),
            "fallbacks": len(safe_get(result, 'fallback_instances', [])),
            "errors": len(safe_get(result, 'processing_errors', []))
        }
        
    except Exception as e:
        print(f"X SCENARIO FAILED: {str(e)}")
        return {
            "scenario": scenario_name,
            "error": str(e),
            "match": False
        }


async def demonstrate_workflow_capabilities():
    """Demonstrate advanced workflow capabilities."""
    print(f"\n{'='*80}")
    print("WORKFLOW CAPABILITY DEMONSTRATION")
    print(f"{'='*80}")
    
    manager = LocalModelManager()
    workflow = ComplexLoanProcessingWorkflow(manager)
    
    print("Key Capabilities Being Demonstrated:")
    print("   - Multi-model coordination (Fast -> Standard -> Reasoning)")
    print("   - Conditional branching based on risk and quality")
    print("   - Automatic retry with exponential backoff")
    print("   - Circuit breaker protection")
    print("   - Comprehensive fallback strategies")
    print("   - Quality checkpoints and validation")
    print("   - Human escalation for edge cases")
    print("   - Model voting for critical decisions")
    
    # Get system status
    status = workflow.get_workflow_status()
    
    print(f"\nSYSTEM STATUS:")
    print(f"   Available Models: {', '.join(status['available_models'])}")
    print(f"   Service Level: {status['service_level']}")
    
    if status.get('circuit_breakers'):
        print(f"   Circuit Breaker Status:")
        for model, cb_status in status['circuit_breakers'].items():
            state_emoji = {"closed": "OK", "open": "FAIL", "half_open": "WAIT"}.get(cb_status.get('state'), "N/A")
            print(f"     {model}: {state_emoji} {cb_status.get('state', 'unknown')}")


async def comprehensive_workflow_test():
    """Run comprehensive test of the complex workflow."""
    print("Phase 6: Complex Multi-Model Loan Processing Workflow")
    print("This is the grand finale - combining all patterns from previous phases!")
    print("Make sure Ollama is running with the required models!\n")
    
    manager = LocalModelManager()
    workflow = ComplexLoanProcessingWorkflow(manager)
    
    # Demonstrate capabilities first
    await demonstrate_workflow_capabilities()
    
    # Process all loan application scenarios
    results = []
    
    for scenario_name, scenario in LOAN_APPLICATION_SCENARIOS.items():
        result = await process_loan_application(workflow, scenario_name, scenario)
        if result:
            results.append(result)
    
    # Show comprehensive summary
    print(f"\n{'='*80}")
    print("+++ COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    if results:
        successful_scenarios = [r for r in results if r.get('match', False)]
        total_processing_time = sum(r.get('processing_time', 0) for r in results)
        total_steps = sum(r.get('steps_completed', 0) for r in results)
        total_retries = sum(r.get('retries', 0) for r in results)
        total_fallbacks = sum(r.get('fallbacks', 0) for r in results)
        total_errors = sum(r.get('errors', 0) for r in results)
        
        print(f"++++ OVERALL PERFORMANCE:")
        print(f"   Scenarios Processed: {len(results)}")
        print(f"   Expected Outcomes Matched: {len(successful_scenarios)}/{len(results)} ({len(successful_scenarios)/len(results)*100:.1f}%)")
        print(f"   Total Processing Time: {total_processing_time:.2f}s")
        print(f"   Average Time per Application: {total_processing_time/len(results):.2f}s")
        print(f"   Total Processing Steps: {total_steps}")
        print(f"   Total Retries Used: {total_retries}")
        print(f"   Total Fallback Instances: {total_fallbacks}")
        print(f"   Total Processing Errors: {total_errors}")
        
        print(f"\n📋 SCENARIO BREAKDOWN:")
        print(f"{'Scenario':<25} {'Expected':<15} {'Actual':<20} {'Time':<8} {'Match'}")
        print("-" * 85)
        
        for result in results:
            if 'error' not in result:
                match_emoji = "✅" if result['match'] else "X"
                print(f"{result['scenario']:<25} {result['expected']:<15} {result['actual']:<20} "
                      f"{result['processing_time']:<8.1f} {match_emoji}")
        
        # Show system insights
        system_status = workflow.get_workflow_status()
        
        if system_status.get('model_stats'):
            print(f"\n! MODEL USAGE STATISTICS:")
            for model_name, stats in system_status['model_stats'].items():
                print(f"   {model_name.upper()}: {stats['total_operations']} operations, "
                      f"{stats['success_rate']:.1%} success rate")


async def main():
    """Главная функция для Фазы 6."""
    await comprehensive_workflow_test()
    
    print(f"\n{'='*80}")
    print("🎉 ФАЗА 6 ЗАВЕРШЕНА - ПРОЕКТ ОКОНЧЕН! 🎉")
    print(f"{'='*80}")
    print("🏆 МАСТЕРСТВО LANGGRAPH ДОСТИГНУТО!")
    print("")
    print("📚 Что вы изучили во всех фазах:")
    print("   Фаза 1: Настройка локальных моделей с базовыми retry/fallback")
    print("   Фаза 2: Простые рабочие процессы LangGraph с управлением состоянием")
    print("   Фаза 3: Условное ветвление и интеллектуальная маршрутизация")
    print("   Фаза 4: Продвинутые механизмы повторов с circuit breakers")
    print("   Фаза 5: Сложные стратегии отказоустойчивости с кэшированием")
    print("   Фаза 6: Комплексная автоматизация бизнес-процессов с множественными моделями")
    print("")
    print("Освоенные паттерны реального мира:")
    print("   - Оркестрация и координация нескольких моделей")
    print("   - Условные рабочие процессы с динамической маршрутизацией")
    print("   - Экспоненциальная задержка и паттерны circuit breaker")
    print("   - Интеллектуальное кэширование и оптимизация ответов")
    print("   - Процедуры передачи человеку и эскалации")
    print("   - Контрольные точки качества и шлюзы валидации")
    print("   - Комплексная обработка ошибок и восстановление")
    print("   - Механизмы голосования моделей и консенсуса")
    print("")
    print("Теперь вы готовы создавать продакшн LangGraph приложения!")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())