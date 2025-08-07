"""Phase 4 example: Advanced retry mechanisms and circuit breakers."""
import asyncio
import logging
import json
import time
import sys
from pathlib import Path

# Добавляем корневую папку проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.local_model_manager import LocalModelManager
from src.models.model_configs import ModelType
from src.utils.retry_handler import RetryableError, NonRetryableError, RetryConfig, RetryStrategy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Test prompts designed to trigger different failure scenarios
TEST_SCENARIOS = {
    "normal": {
        "prompt": "What is 2+2? Answer briefly.",
        "description": "Simple prompt that should succeed"
    },
    
    "timeout_prone": {
        "prompt": """
Write a detailed 2000-word essay about the philosophical implications of artificial intelligence, 
including historical context, current debates, future predictions, ethical considerations, 
societal impacts, and provide specific examples and citations. Make sure to cover all aspects thoroughly.
""",
        "description": "Long complex prompt that may timeout on smaller models"
    },
    
    "parse_error_prone": {
        "prompt": "Return your response as valid JSON with keys: result, confidence, explanation",
        "description": "Prompt that may produce parse errors due to format issues"
    },
    
    "empty_response_prone": {
        "prompt": "",
        "description": "Empty prompt that may cause empty responses"
    },
    
    "complex_reasoning": {
        "prompt": """
Solve this step by step:
If a train leaves Station A at 2:15 PM traveling at 65 mph, and another train leaves Station B 
at 2:45 PM traveling at 80 mph toward Station A, and the stations are 420 miles apart, 
at what time will they meet and how far from Station A?
""",
        "description": "Complex reasoning that may require multiple attempts"
    }
}


async def simulate_model_failures():
    """Simulate various model failure scenarios to test retry mechanisms."""
    print("🧪 SIMULATING MODEL FAILURES")
    print("=" * 60)
    
    manager = LocalModelManager()
    
    # Test each failure scenario
    for scenario_name, scenario in TEST_SCENARIOS.items():
        print(f"\n🔬 Testing: {scenario['description']}")
        print(f"Scenario: {scenario_name}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            
            # Try with advanced retry enabled
            result = await manager.invoke_with_fallback(
                ModelType.REASONING,
                scenario["prompt"],
                use_advanced_retry=True
            )
            
            execution_time = time.time() - start_time
            print(f"✅ SUCCESS (in {execution_time:.2f}s)")
            print(f"Result: {result[:100]}{'...' if len(result) > 100 else ''}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ FAILED after {execution_time:.2f}s: {str(e)}")


async def compare_retry_strategies():
    """Compare different retry strategies performance."""
    print(f"\n{'='*60}")
    print("🔄 COMPARING RETRY STRATEGIES")
    print(f"{'='*60}")
    
    manager = LocalModelManager()
    test_prompt = "Explain quantum computing in exactly 50 words."
    
    strategies = [
        ("Basic Retry", False),
        ("Advanced Retry", True)
    ]
    
    results = {}
    
    for strategy_name, use_advanced in strategies:
        print(f"\n📊 Testing {strategy_name}...")
        
        start_time = time.time()
        attempts = 0
        success = False
        
        try:
            # Test multiple times to get average performance
            for i in range(3):
                await manager.invoke_with_fallback(
                    ModelType.STANDARD,
                    f"{test_prompt} (test {i+1})",
                    use_advanced_retry=use_advanced
                )
                attempts += 1
            
            success = True
            
        except Exception as e:
            print(f"Strategy failed: {e}")
        
        total_time = time.time() - start_time
        avg_time = total_time / 3 if success else total_time
        
        results[strategy_name] = {
            "success": success,
            "total_time": total_time,
            "avg_time_per_request": avg_time,
            "attempts": attempts
        }
        
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"Average time per request: {avg_time:.2f}s")
    
    # Compare results
    print(f"\n📈 STRATEGY COMPARISON:")
    for strategy, result in results.items():
        print(f"{strategy:<15}: {result['avg_time_per_request']:.2f}s avg, "
              f"{'✅' if result['success'] else '❌'}")


async def test_circuit_breaker():
    """Test circuit breaker functionality by forcing failures."""
    print(f"\n{'='*60}")
    print("⚡ TESTING CIRCUIT BREAKER")
    print(f"{'='*60}")
    
    manager = LocalModelManager()
    
    # Simulate repeated failures to trigger circuit breaker
    print("🔴 Forcing failures to trigger circuit breaker...")
    
    failure_count = 0
    for i in range(7):  # Try more than the failure threshold
        try:
            # Use a prompt that's likely to fail or timeout on smaller models
            await manager.invoke_with_fallback(
                ModelType.FAST,  # Use fast model which might struggle
                "Generate a perfect 10,000 word academic paper about quantum mechanics with citations",
                use_advanced_retry=True
            )
            print(f"Attempt {i+1}: ✅ Unexpected success")
        except Exception as e:
            failure_count += 1
            print(f"Attempt {i+1}: ❌ Failed ({type(e).__name__})")
            
            # Check circuit breaker status
            status = manager.get_circuit_status(ModelType.FAST)
            print(f"   Circuit status: {status['state']} "
                  f"(failures: {status['failure_count']})")
            
            if status['state'] == 'open':
                print("   🚨 CIRCUIT BREAKER OPENED!")
                break
        
        # Small delay between attempts
        await asyncio.sleep(0.5)
    
    # Show final circuit breaker status
    print(f"\n⚡ Final Circuit Breaker Status:")
    for model_type in ModelType:
        status = manager.get_circuit_status(model_type)
        print(f"   {model_type.value}: {status}")


async def analyze_retry_patterns():
    """Analyze retry patterns and statistics."""
    print(f"\n{'='*60}")
    print("📊 RETRY PATTERN ANALYSIS")
    print(f"{'='*60}")
    
    manager = LocalModelManager()
    
    # Run several operations to generate retry data
    test_prompts = [
        "What is the capital of France?",
        "Explain machine learning briefly.",
        "Calculate 15 * 23",
        "What is the meaning of life?",
        "Describe the color blue."
    ]
    
    for i, prompt in enumerate(test_prompts):
        try:
            await manager.invoke_with_fallback(
                ModelType.STANDARD,
                prompt,
                use_advanced_retry=True
            )
            print(f"✓ Completed prompt {i+1}")
        except Exception as e:
            print(f"✗ Failed prompt {i+1}: {e}")
    
    # Get and display retry statistics
    print(f"\n📈 RETRY STATISTICS:")
    
    all_stats = manager.get_retry_stats()
    if all_stats:
        for model_type, stats in all_stats.items():
            print(f"\n{model_type.upper()} Model:")
            print(f"   Total operations: {stats['total_operations']}")
            print(f"   Success rate: {stats['success_rate']:.2%}")
            print(f"   Avg execution time: {stats['avg_execution_time']:.2f}s")
            
            if stats.get('retry_distribution'):
                print(f"   Retry distribution: {stats['retry_distribution']}")
    else:
        print("   No retry statistics available yet")
    
    # Show circuit breaker states
    print(f"\n⚡ CIRCUIT BREAKER STATES:")
    for model_type in ModelType:
        if manager.is_model_available(model_type):
            status = manager.get_circuit_status(model_type)
            state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}.get(status.get('state'), "⚪")
            print(f"   {model_type.value}: {state_emoji} {status.get('state', 'unknown')}")


async def demonstrate_exponential_backoff():
    """Demonstrate exponential backoff behavior."""
    print(f"\n{'='*60}")
    print("⏱️  DEMONSTRATING EXPONENTIAL BACKOFF")
    print(f"{'='*60}")
    
    from src.utils.retry_handler import AdvancedRetryHandler, RetryConfig, RetryStrategy
    
    # Create retry handler with visible backoff
    retry_handler = AdvancedRetryHandler()
    
    async def failing_operation():
        """Operation that always fails to show retry timing."""
        await asyncio.sleep(0.1)  # Simulate some work
        raise RetryableError("Simulated failure for backoff demo")
    
    config = RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_multiplier=2.0,
        jitter=False  # Disable jitter for predictable timing
    )
    
    print("🕐 Starting operation that will fail with exponential backoff...")
    print("Watch the delay between attempts increase exponentially:")
    
    start_time = time.time()
    try:
        await retry_handler.execute_with_retry(
            failing_operation,
            "demo_exponential_backoff",
            config
        )
    except Exception as e:
        total_time = time.time() - start_time
        print(f"\n💥 All retries exhausted after {total_time:.1f}s")
        print(f"Expected delays were: 1s, 2s, 4s, 8s (exponential: base * 2^attempt)")


async def main():
    """Main test function for Phase 4."""
    print("🚀 Phase 4: Advanced Retry Mechanisms & Circuit Breakers")
    print("This demonstrates sophisticated failure recovery patterns")
    print("Make sure Ollama is running with the required models!\n")
    
    # Run all retry mechanism tests
    await simulate_model_failures()
    await compare_retry_strategies()
    await test_circuit_breaker()
    await analyze_retry_patterns()
    await demonstrate_exponential_backoff()
    
    print(f"\n{'='*60}")
    print("✅ PHASE 4 COMPLETE!")
    print("Key Features Demonstrated:")
    print("  • Exponential backoff with jitter")
    print("  • Circuit breaker patterns (closed/open/half-open)")
    print("  • Intelligent retry conditions")
    print("  • Different retry strategies per model type")
    print("  • Comprehensive retry statistics")
    print("  • Automatic recovery mechanisms")
    print("\nNext: Phase 5 will add sophisticated fallback strategies")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())