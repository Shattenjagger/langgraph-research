"""Phase 5 example: Sophisticated fallback strategies with caching and human handoff."""
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
from src.models.fallback_chain import EnhancedModelFallbackChain
from src.utils.fallback_strategies import FallbackLevel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Test scenarios for different fallback strategies
FALLBACK_TEST_SCENARIOS = {
    "normal_operation": {
        "prompt": "What is the capital of France?",
        "description": "Normal operation - should succeed with primary model",
        "context": {"user_tier": "standard"}
    },
    
    "cache_favorable": {
        "prompt": "What is 2+2?",
        "description": "Simple question likely to have cached responses",
        "context": {"operation_type": "calculation"}
    },
    
    "complex_reasoning": {
        "prompt": """
        Analyze the following business scenario and provide strategic recommendations:
        A manufacturing company has seen a 15% decrease in sales over the past 6 months, 
        but customer satisfaction scores have increased by 20%. Market research shows that 
        competitors have lowered prices by an average of 25%. The company's profit margins 
        are currently at 18%, down from 22% last year. What should be the strategic response?
        """,
        "description": "Complex reasoning that may require fallbacks",
        "context": {"document_type": "business_analysis", "urgent": True}
    },
    
    "timeout_prone": {
        "prompt": """
        Write a comprehensive 5000-word analysis of quantum computing applications in 
        financial services, including technical implementation details, regulatory 
        considerations, risk assessments, and ROI projections. Include specific examples 
        and cite recent research papers.
        """,
        "description": "Very long request likely to timeout",
        "context": {"user_tier": "premium", "timeout_expected": True}
    },
    
    "semantic_cache_test": {
        "prompt": "What is the capital city of France?",
        "description": "Similar to cached question but different wording",
        "context": {"cache_test": "semantic"}
    },
    
    "human_handoff_trigger": {
        "prompt": "I need immediate help with a critical contract worth $2 million that expires today",
        "description": "High-priority request that should trigger human handoff if models fail",
        "context": {"urgent": True, "user_tier": "premium", "document_type": "contract"}
    }
}


async def test_single_fallback_scenario(chain: EnhancedModelFallbackChain, scenario_name: str, scenario: dict):
    """Test a single fallback scenario."""
    print(f"\n{'='*80}")
    print(f"🧪 TESTING SCENARIO: {scenario_name.upper()}")
    print(f"📝 Description: {scenario['description']}")
    print(f"{'='*80}")
    
    try:
        start_time = time.time()
        
        # Execute with comprehensive fallbacks
        result = await chain.invoke_with_comprehensive_fallbacks(
            ModelType.REASONING,  # Start with most capable model
            scenario["prompt"],
            scenario["context"]
        )
        
        execution_time = time.time() - start_time
        
        # Display results
        success_indicator = "✅" if result['success'] else "❌"
        print(f"\n{success_indicator} RESULT:")
        print(f"   Success: {result['success']}")
        print(f"   Execution Time: {execution_time:.2f}s")
        print(f"   Fallback Level: {result['fallback_level'].value}")
        print(f"   Source: {result['source']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        
        if 'handoff_id' in result:
            print(f"   🚨 Human Handoff ID: {result['handoff_id']}")
        
        # Show response (truncated)
        response = str(result['result'])
        if len(response) > 200:
            print(f"   Response: {response[:200]}...")
        else:
            print(f"   Response: {response}")
        
        # Show circuit breaker status if available
        if 'circuit_status' in result:
            print(f"\n⚡ Circuit Breaker Status:")
            for model, status in result['circuit_status'].items():
                state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}.get(status.get('state'), "⚪")
                print(f"   {model}: {state_emoji} {status.get('state', 'unknown')}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ SCENARIO FAILED after {execution_time:.2f}s: {str(e)}")
        return None


async def test_model_voting():
    """Test model voting strategy."""
    print(f"\n{'='*80}")
    print("🗳️  TESTING MODEL VOTING STRATEGY")
    print(f"{'='*80}")
    
    manager = LocalModelManager()
    chain = EnhancedModelFallbackChain(manager)
    
    test_prompt = "Explain the concept of machine learning in simple terms."
    available_models = manager.get_available_models()
    
    if len(available_models) < 2:
        print("❌ Need at least 2 models for voting test")
        return
    
    print(f"📊 Using models: {[m.value for m in available_models]}")
    
    try:
        start_time = time.time()
        
        result = await chain.invoke_with_model_voting(
            test_prompt,
            available_models,
            {"operation_type": "voting_test"}
        )
        
        execution_time = time.time() - start_time
        
        success_indicator = "✅" if result['success'] else "❌"
        print(f"\n{success_indicator} VOTING RESULT:")
        print(f"   Success: {result['success']}")
        print(f"   Execution Time: {execution_time:.2f}s")
        print(f"   Source: {result['source']}")
        
        if result['success']:
            print(f"   Winner: {result.get('winner', 'unknown')}")
            print(f"   Total Votes: {result.get('total_votes', 0)}")
            print(f"   Confidence: {result['confidence']:.2f}")
            
            print(f"\n🗳️  Voting Breakdown:")
            for vote_result in result.get('voting_results', []):
                if isinstance(vote_result, dict) and 'success' in vote_result:
                    status = "✅" if vote_result['success'] else "❌"
                    model = vote_result.get('primary_model', 'unknown')
                    confidence = vote_result.get('confidence', 0.0)
                    print(f"   {model}: {status} (confidence: {confidence:.2f})")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ VOTING TEST FAILED after {execution_time:.2f}s: {str(e)}")
        return None


async def test_progressive_degradation():
    """Test progressive degradation strategy."""
    print(f"\n{'='*80}")
    print("📉 TESTING PROGRESSIVE DEGRADATION")
    print(f"{'='*80}")
    
    manager = LocalModelManager()
    chain = EnhancedModelFallbackChain(manager)
    
    test_prompt = "Provide a detailed analysis of renewable energy trends."
    
    try:
        start_time = time.time()
        
        result = await chain.invoke_with_progressive_degradation(
            test_prompt,
            {"test_type": "progressive_degradation"}
        )
        
        execution_time = time.time() - start_time
        
        success_indicator = "✅" if result['success'] else "❌"
        print(f"\n{success_indicator} DEGRADATION RESULT:")
        print(f"   Success: {result['success']}")
        print(f"   Execution Time: {execution_time:.2f}s")
        
        if 'degradation_level' in result:
            print(f"   Degradation Level: {result['degradation_level'].value}")
            print(f"   Description: {result['degradation_description']}")
        
        if 'attempted_levels' in result:
            print(f"\n📉 Degradation Attempts:")
            for level in result['attempted_levels']:
                status_emoji = {"success": "✅", "failed": "❌", "model_unavailable": "⚪"}.get(level.get('result', ''), "❓")
                print(f"   {level['model']}: {status_emoji} {level['result']} "
                      f"(level: {level['level'].value})")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ PROGRESSIVE DEGRADATION FAILED after {execution_time:.2f}s: {str(e)}")
        return None


async def analyze_cache_performance():
    """Analyze cache hit rates and performance."""
    print(f"\n{'='*80}")
    print("💾 CACHE PERFORMANCE ANALYSIS")
    print(f"{'='*80}")
    
    manager = LocalModelManager()
    chain = EnhancedModelFallbackChain(manager)
    
    # First, populate cache with some responses
    print("🔄 Populating cache...")
    
    base_prompts = [
        "What is 2+2?",
        "What is the capital of France?",
        "Explain machine learning briefly.",
        "How does photosynthesis work?",
        "What is the speed of light?"
    ]
    
    cache_results = []
    
    for prompt in base_prompts:
        try:
            result = await chain.invoke_with_comprehensive_fallbacks(
                ModelType.FAST,
                prompt,
                {"cache_population": True}
            )
            cache_results.append({
                "prompt": prompt,
                "cached": result['source'].startswith('cache'),
                "source": result['source']
            })
        except Exception as e:
            print(f"Failed to process: {prompt} - {e}")
    
    # Now test cache hits with similar prompts
    print(f"\n🎯 Testing cache hits with similar prompts...")
    
    similar_prompts = [
        "What is two plus two?",  # Similar to "What is 2+2?"
        "What is the capital city of France?",  # Similar to capital question
        "Briefly explain machine learning.",  # Similar to ML question
    ]
    
    cache_hit_results = []
    
    for prompt in similar_prompts:
        try:
            result = await chain.invoke_with_comprehensive_fallbacks(
                ModelType.REASONING,
                prompt,
                {"cache_test": True}
            )
            
            cache_hit_results.append({
                "prompt": prompt,
                "source": result['source'],
                "is_cache_hit": result['source'].startswith('cache'),
                "confidence": result['confidence']
            })
            
        except Exception as e:
            print(f"Cache test failed for: {prompt} - {e}")
    
    # Display cache analysis
    print(f"\n💾 CACHE ANALYSIS RESULTS:")
    print(f"Base prompts processed: {len(cache_results)}")
    
    cache_hits = [r for r in cache_hit_results if r['is_cache_hit']]
    print(f"Cache hits from similar prompts: {len(cache_hits)}/{len(cache_hit_results)}")
    
    if cache_hit_results:
        avg_confidence = sum(r['confidence'] for r in cache_hit_results) / len(cache_hit_results)
        print(f"Average confidence for cache tests: {avg_confidence:.2f}")
        
        print(f"\n📊 Cache Hit Details:")
        for result in cache_hit_results:
            hit_emoji = "🎯" if result['is_cache_hit'] else "❌"
            print(f"   {hit_emoji} {result['source']}: {result['prompt'][:50]}...")


async def show_human_handoff_queue():
    """Show current human handoff queue status."""
    print(f"\n{'='*80}")
    print("👤 HUMAN HANDOFF QUEUE STATUS")
    print(f"{'='*80}")
    
    manager = LocalModelManager()
    chain = EnhancedModelFallbackChain(manager)
    
    # Get pending requests
    pending_requests = await chain.fallback_manager.handoff_queue.get_pending_requests()
    
    if not pending_requests:
        print("📭 No pending human handoff requests")
        return
    
    print(f"📮 {len(pending_requests)} pending requests:")
    
    for request in pending_requests:
        priority_emoji = {1: "🔵", 2: "🟡", 3: "🟠", 4: "🔴", 5: "🚨"}.get(request.priority, "⚪")
        
        print(f"\n{priority_emoji} Request ID: {request.request_id}")
        print(f"   Priority: {request.priority}")
        print(f"   Timestamp: {request.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Prompt: {request.original_prompt[:100]}...")
        print(f"   Failure Reason: {request.failure_reason[:100]}...")
        print(f"   Status: {request.status}")


async def comprehensive_fallback_demonstration():
    """Run comprehensive demonstration of all fallback strategies."""
    print("🚀 Phase 5: Sophisticated Fallback Strategies Demonstration")
    print("This shows advanced failure recovery with caching and human handoff")
    print("Make sure Ollama is running with the required models!\n")
    
    manager = LocalModelManager()
    chain = EnhancedModelFallbackChain(manager)
    
    # Test all scenarios
    results = []
    for scenario_name, scenario in FALLBACK_TEST_SCENARIOS.items():
        result = await test_single_fallback_scenario(chain, scenario_name, scenario)
        if result:
            results.append({
                "scenario": scenario_name,
                "success": result['success'],
                "fallback_level": result['fallback_level'].value,
                "source": result['source'],
                "confidence": result['confidence']
            })
    
    # Test advanced strategies
    await test_model_voting()
    await test_progressive_degradation()
    await analyze_cache_performance()
    await show_human_handoff_queue()
    
    # Show comprehensive system status
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE SYSTEM STATUS")
    print(f"{'='*80}")
    
    status = chain.get_comprehensive_status()
    
    print(f"🎛️  Service Level: {status['service_level']}")
    print(f"🔢 Total Operations: {status['operations_count']}")
    
    if status.get('fallback_stats', {}).get('total_operations', 0) > 0:
        fallback_stats = status['fallback_stats']
        print(f"📈 Fallback Success Rate: {(1 - fallback_stats['failure_rate']):.2%}")
        print(f"❌ Complete Failures: {fallback_stats['complete_failures']}")
    
    print(f"\n🤖 Available Models: {', '.join(status['available_models'])}")
    
    # Summary of test results
    if results:
        print(f"\n📋 TEST SCENARIO SUMMARY:")
        success_count = sum(1 for r in results if r['success'])
        print(f"   Successful scenarios: {success_count}/{len(results)}")
        
        fallback_levels = {}
        for r in results:
            level = r['fallback_level']
            fallback_levels[level] = fallback_levels.get(level, 0) + 1
        
        print(f"   Fallback level distribution:")
        for level, count in fallback_levels.items():
            print(f"     {level}: {count}")


async def main():
    """Main test function for Phase 5."""
    await comprehensive_fallback_demonstration()
    
    print(f"\n{'='*80}")
    print("✅ PHASE 5 COMPLETE!")
    print("Key Features Demonstrated:")
    print("  • Multi-level fallback strategies (5 levels)")
    print("  • Intelligent response caching (exact, semantic, template)")
    print("  • Human handoff queue with priority management")
    print("  • Model voting and consensus mechanisms")
    print("  • Progressive degradation with adapted prompts")
    print("  • Circuit breaker integration")
    print("  • Comprehensive failure recovery")
    print("\nNext: Phase 6 will create a complex multi-model workflow")
    print("combining all learned patterns into a real business scenario")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())