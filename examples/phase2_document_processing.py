"""Phase 2 example: Simple document processing workflow."""
import asyncio
import logging
import json
import sys
from pathlib import Path

# Добавляем корневую папку проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.local_model_manager import LocalModelManager
from src.workflows.document_processing import DocumentProcessingWorkflow

logging.basicConfig(level=logging.INFO)


# Sample documents for testing
SAMPLE_DOCUMENTS = {
    "invoice": """
INVOICE #INV-2024-001
Date: March 15, 2024
Due Date: April 15, 2024

Bill To:
ABC Company
123 Business St
City, State 12345

From:
XYZ Services LLC
456 Service Ave
Another City, State 67890

Description                    Quantity    Rate      Amount
Web Development Services           40      $125.00   $5,000.00
Domain Registration                 1       $15.00      $15.00
Hosting Services                   12       $25.00     $300.00

                               Subtotal:   $5,315.00
                               Tax (8%):     $425.20
                               Total:      $5,740.20

Payment Terms: Net 30 days
""",
    
    "contract": """
SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into on March 1, 2024, between:

CLIENT: ABC Corporation, a Delaware corporation
ADDRESS: 789 Corporate Blvd, Business City, ST 12345

SERVICE PROVIDER: Tech Solutions Inc, an LLC
ADDRESS: 321 Innovation Dr, Tech Hub, ST 67890

TERM: This agreement shall commence on April 1, 2024, and shall continue for a period of 12 months, expiring on March 31, 2025, unless terminated earlier in accordance with the terms herein.

SERVICES: Provider agrees to deliver software development and maintenance services including:
- Custom application development
- System integration
- Technical support and maintenance
- Monthly performance reporting

COMPENSATION: Client agrees to pay Provider a monthly fee of $10,000, payable within 30 days of invoice receipt.

TERMINATION: Either party may terminate this agreement with 60 days written notice.
""",

    "receipt": """
STORE RECEIPT
ABC Electronics Store
555 Retail Street, Shopping Center
Date: March 10, 2024  Time: 2:45 PM

Item                           Price
Laptop Computer              $899.99
Wireless Mouse                $24.99
USB Cable                     $12.99
Extended Warranty             $99.99

Subtotal:                    $1,037.96
Sales Tax (7.5%):              $77.85
Total:                      $1,115.81

Payment Method: Credit Card ****1234
Transaction ID: TXN-789456123
Thank you for your purchase!
"""
}


async def test_single_document(workflow: DocumentProcessingWorkflow, doc_type: str, content: str):
    """Test processing a single document."""
    print(f"\n{'='*60}")
    print(f"PROCESSING {doc_type.upper()} DOCUMENT")
    print(f"{'='*60}")
    
    try:
        # Process the document
        result = await workflow.process_document(
            document_content=content,
            document_id=f"test_{doc_type}_001"
        )
        
        # Display results
        print(f"Document ID: {result.document_id}")
        print(f"Status: {result.status.value}")
        print(f"Document Type: {result.document_type.value if result.document_type else 'Unknown'}")
        print(f"Classification Confidence: {result.classification_confidence:.2f}")
        print(f"Processing Time: {result.processing_time:.2f}s")
        print(f"Models Used: {', '.join(result.models_used)}")
        print(f"Retry Count: {result.retry_count}")
        
        if result.validation_results:
            print(f"\nValidation Issues ({len(result.validation_results)}):")
            for issue in result.validation_results:
                print(f"  - {issue}")
        
        if result.extracted_data:
            print(f"\nExtracted Data:")
            print(json.dumps(result.extracted_data, indent=2))
        
        if result.human_review_required:
            print(f"\n⚠️  HUMAN REVIEW REQUIRED")
        
        if result.error_message:
            print(f"\n❌ ERROR: {result.error_message}")
        
        print(f"\nProcessing Notes:")
        for note in result.processing_notes:
            print(f"  - {note}")
            
    except Exception as e:
        print(f"❌ Failed to process {doc_type} document: {e}")


async def test_workflow_performance():
    """Test processing multiple documents to see performance patterns."""
    print(f"\n{'='*60}")
    print("WORKFLOW PERFORMANCE TEST")
    print(f"{'='*60}")
    
    manager = LocalModelManager()
    workflow = DocumentProcessingWorkflow(manager)
    
    results = []
    
    for doc_type, content in SAMPLE_DOCUMENTS.items():
        try:
            result = await workflow.process_document(content, f"perf_test_{doc_type}")
            results.append({
                "type": doc_type,
                "time": result.processing_time,
                "models": len(result.models_used),
                "retries": result.retry_count,
                "status": result.status.value
            })
        except Exception as e:
            print(f"Failed to process {doc_type}: {e}")
    
    # Summary
    if results:
        print(f"\nPerformance Summary:")
        print(f"{'Type':<12} {'Time':<8} {'Models':<8} {'Retries':<8} {'Status'}")
        print("-" * 50)
        for r in results:
            print(f"{r['type']:<12} {r['time']:<8.2f} {r['models']:<8} {r['retries']:<8} {r['status']}")
        
        avg_time = sum(r['time'] for r in results) / len(results)
        total_retries = sum(r['retries'] for r in results)
        print(f"\nAverage processing time: {avg_time:.2f}s")
        print(f"Total retries across all documents: {total_retries}")


async def main():
    """Main test function."""
    print("Phase 2: Document Processing Workflow Test")
    print("Make sure Ollama is running with the required models!")
    
    # Initialize components
    manager = LocalModelManager()
    workflow = DocumentProcessingWorkflow(manager)
    
    # Test each document type
    for doc_type, content in SAMPLE_DOCUMENTS.items():
        await test_single_document(workflow, doc_type, content)
    
    # Performance test
    await test_workflow_performance()
    
    print(f"\n{'='*60}")
    print("PHASE 2 COMPLETE!")
    print("Next: Phase 3 will add conditional branching based on document complexity")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())