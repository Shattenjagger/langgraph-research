"""Phase 3 example: Conditional branching workflow."""
import asyncio
import logging
import json
import sys
from pathlib import Path

# Добавляем корневую папку проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.local_model_manager import LocalModelManager
from src.workflows.conditional_workflow import ConditionalDocumentWorkflow

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Enhanced sample documents for testing different branching paths
BRANCHING_TEST_DOCUMENTS = {
    "simple_invoice": """
INVOICE #001
Date: March 15, 2024
From: ABC Services
To: XYZ Company
Service: Basic Consulting - $1,000
Tax: $80
Total: $1,080
""",
    
    "complex_invoice": """
INVOICE #INV-2024-5678
Date: March 15, 2024
Purchase Order: PO-2024-ABC-789
Contract Reference: MSA-2024-001

Bill To:
Enterprise Corp
Attn: Procurement Department
123 Business Complex, Suite 500
Metro City, State 12345

From:
Professional Services LLC
456 Corporate Plaza
Tech Hub, State 67890

Line Items:
1. Software Development - Milestone 1    Hours: 160    Rate: $125/hr    Amount: $20,000.00
2. Architecture Review                   Hours: 40     Rate: $150/hr    Amount: $6,000.00  
3. Technical Documentation              Hours: 24     Rate: $100/hr    Amount: $2,400.00
4. Project Management                   Hours: 80     Rate: $110/hr    Amount: $8,800.00

                                       Subtotal: $37,200.00
                            Volume Discount (5%): -$1,860.00
                                    Net Subtotal: $35,340.00
                                     Tax (8.5%): $3,003.90
                                          Total: $38,343.90

Payment Terms: Net 30 days
Recurring: Monthly billing for 12 months
""",

    "high_value_contract": """
MASTER SERVICE AGREEMENT

This Master Service Agreement ("Agreement") is entered into on January 1, 2024, between:

CLIENT: Fortune500 Corporation, a Delaware corporation  
ADDRESS: 1000 Corporate Drive, Executive Tower, Metro City, ST 12345

PROVIDER: Elite Consulting Group LLC
ADDRESS: 500 Professional Blvd, Consulting Plaza, Tech City, ST 67890

TERM: January 1, 2024 to December 31, 2026 (3 years)

SERVICES: Provider will deliver comprehensive digital transformation services including:
- Enterprise software development and integration
- Cloud migration and infrastructure management  
- Data analytics and AI implementation
- Change management and training
- 24/7 technical support and maintenance

FINANCIAL TERMS:
- Total Contract Value: $2,500,000 over 36 months
- Monthly Base Fee: $50,000
- Additional project work: Time and materials at agreed rates
- Annual rate increases: 3% per year

TERMINATION: Either party may terminate with 90 days written notice. 
Client may terminate for convenience with payment of 30% of remaining contract value.
Early termination penalty applies for first 18 months.

INTELLECTUAL PROPERTY: All custom developments become client property.
Provider retains rights to methodologies and pre-existing IP.

CONFIDENTIALITY: Both parties agree to maintain confidentiality of sensitive business information.

GOVERNING LAW: Delaware State Law
""",

    "unclear_document": """
doc received via email - not sure what type

march something 2024

payment for stuff we did
amount looks like maybe $500 or $5000??? 
hard to read

contact info:
someone at some company
phone: 555-xxxx
email: unclear@domain.com

notes: this might be important but format is terrible
missing lots of information
""",

    "simple_receipt": """
Coffee Shop Receipt
March 10, 2024
2 Coffees: $8.50
1 Muffin: $3.25
Tax: $0.59
Total: $12.34
Card Payment
Thank you!
"""
}


async def test_conditional_routing(workflow: ConditionalDocumentWorkflow, doc_name: str, content: str):
    """Test conditional routing for a specific document."""
    print(f"\n{'='*70}")
    print(f"TESTING CONDITIONAL ROUTING: {doc_name.upper()}")
    print(f"{'='*70}")
    
    try:
        result = await workflow.process_document(
            document_content=content,
            document_id=f"conditional_test_{doc_name}"
        )
        
        print(f"📋 Document ID: {result.document_id}")
        print(f"🔄 Final Status: {result.status.value}")
        print(f"📊 Processing Time: {result.processing_time:.2f}s")
        print(f"🔄 Retry Count: {result.retry_count}")
        
        if result.final_result:
            processing_path = result.final_result.get("processing_path", "unknown")
            print(f"🛤️  Processing Path: {processing_path}")
        
        print(f"🧠 Models Used: {', '.join(result.models_used)}")
        
        # Show classification results
        doc_type = result.document_type.value if result.document_type else "unknown"
        print(f"📄 Document Type: {doc_type} (confidence: {result.classification_confidence:.2f})")
        
        # Show processing notes (routing decisions)
        print(f"\n📝 Processing Decision Trail:")
        for i, note in enumerate(result.processing_notes, 1):
            print(f"   {i}. {note}")
        
        # Show validation results if any
        if result.validation_results:
            print(f"\n⚠️  Validation Issues ({len(result.validation_results)}):")
            for issue in result.validation_results:
                print(f"   - {issue}")
        
        # Show human review status
        if result.human_review_required:
            print(f"\n👤 HUMAN REVIEW REQUIRED")
            print("   Reasons: Check validation issues and processing notes above")
        else:
            print(f"\n✅ AUTOMATED PROCESSING COMPLETED")
        
        # Show key extracted data
        if result.extracted_data and len(result.extracted_data) > 0:
            print(f"\n💾 Key Extracted Data:")
            # Show first few fields to avoid clutter
            shown_fields = 0
            for key, value in result.extracted_data.items():
                if shown_fields < 3 and key != "raw_response":
                    print(f"   {key}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
                    shown_fields += 1
            if len(result.extracted_data) > 3:
                print(f"   ... and {len(result.extracted_data) - 3} more fields")
        
        if result.error_message:
            print(f"\n❌ ERROR: {result.error_message}")
        
        return result
        
    except Exception as e:
        print(f"❌ Failed to process {doc_name}: {e}")
        return None


async def analyze_routing_patterns():
    """Analyze the different routing patterns used."""
    print(f"\n{'='*70}")
    print("ROUTING PATTERN ANALYSIS")
    print(f"{'='*70}")
    
    manager = LocalModelManager()
    workflow = ConditionalDocumentWorkflow(manager)
    
    results = []
    
    for doc_name, content in BRANCHING_TEST_DOCUMENTS.items():
        result = await test_conditional_routing(workflow, doc_name, content)
        if result and result.final_result:
            results.append({
                "name": doc_name,
                "path": result.final_result.get("processing_path", "unknown"),
                "doc_type": result.document_type.value if result.document_type else "unknown",
                "confidence": result.classification_confidence,
                "models_used": len(result.models_used),
                "retry_count": result.retry_count,
                "human_review": result.human_review_required,
                "time": result.processing_time,
                "status": result.status.value
            })
    
    if results:
        print(f"\n📊 ROUTING SUMMARY:")
        print(f"{'Document':<20} {'Path':<18} {'Type':<12} {'Conf':<6} {'Models':<7} {'Review':<7} {'Status'}")
        print("-" * 85)
        
        for r in results:
            review_marker = "YES" if r['human_review'] else "NO"
            print(f"{r['name']:<20} {r['path']:<18} {r['doc_type']:<12} {r['confidence']:<6.2f} "
                  f"{r['models_used']:<7} {review_marker:<7} {r['status']}")
        
        # Analysis
        print(f"\n🔍 ROUTING INSIGHTS:")
        paths_used = set(r['path'] for r in results)
        print(f"   • Unique processing paths used: {len(paths_used)}")
        print(f"   • Paths: {', '.join(sorted(paths_used))}")
        
        avg_confidence = sum(r['confidence'] for r in results) / len(results)
        print(f"   • Average classification confidence: {avg_confidence:.2f}")
        
        human_reviews = sum(1 for r in results if r['human_review'])
        print(f"   • Documents requiring human review: {human_reviews}/{len(results)}")
        
        total_retries = sum(r['retry_count'] for r in results)
        print(f"   • Total retries across all documents: {total_retries}")


async def main():
    """Main test function for Phase 3."""
    print("🚀 Phase 3: Conditional Branching Workflow Test")
    print("This demonstrates smart routing based on document characteristics")
    print("Make sure Ollama is running with the required models!\n")
    
    # Run routing pattern analysis
    await analyze_routing_patterns()
    
    print(f"\n{'='*70}")
    print("✅ PHASE 3 COMPLETE!")
    print("Key Features Demonstrated:")
    print("  • 5 different processing paths based on document complexity")
    print("  • Smart model selection for each path") 
    print("  • Automatic retry logic with fallbacks")
    print("  • Human review triggers for high-risk documents")
    print("  • Detailed decision trail tracking")
    print("\nNext: Phase 4 will add advanced retry mechanisms with exponential backoff")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())