"""Enhanced fallback chain integrating advanced strategies with model management."""
import logging
from typing import Dict, Any, Optional, Callable
from ..models.local_model_manager import LocalModelManager
from ..models.model_configs import ModelType
from ..utils.fallback_strategies import FallbackStrategyManager, FallbackLevel

logger = logging.getLogger(__name__)


class EnhancedModelFallbackChain:
    """Enhanced model fallback chain with advanced strategies."""
    
    def __init__(self, model_manager: LocalModelManager):
        self.model_manager = model_manager
        self.fallback_manager = FallbackStrategyManager()
        self.operation_counter = 0
    
    async def invoke_with_comprehensive_fallbacks(
        self,
        model_type: ModelType,
        prompt: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Invoke model with comprehensive fallback strategies.
        
        Args:
            model_type: Primary model to try
            prompt: Input prompt
            context: Additional context for fallback decisions
            
        Returns:
            Dict with result, fallback info, and metadata
        """
        self.operation_counter += 1
        operation_id = f"model_op_{self.operation_counter}"
        
        # Add model info to context
        context = context or {}
        context.update({
            'model_type': model_type.value,
            'primary_model': model_type.value
        })
        
        # Define the primary operation
        async def primary_operation():
            """Primary model operation."""
            return await self.model_manager.invoke_with_fallback(
                model_type, 
                prompt, 
                use_advanced_retry=True
            )
        
        # Execute with comprehensive fallbacks
        result = await self.fallback_manager.execute_with_fallbacks(
            primary_operation,
            operation_id,
            prompt,
            context
        )
        
        # Add additional metadata
        result.update({
            'operation_id': operation_id,
            'primary_model': model_type.value,
            'available_models': [m.value for m in self.model_manager.get_available_models()],
            'circuit_status': {
                m.value: self.model_manager.get_circuit_status(m)
                for m in ModelType if self.model_manager.is_model_available(m)
            }
        })
        
        return result
    
    async def invoke_with_model_voting(
        self,
        prompt: str,
        models: list[ModelType],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Use multiple models and vote on the best response.
        Falls back to single model if voting fails.
        """
        context = context or {}
        context['operation_type'] = 'model_voting'
        
        voting_results = []
        successful_responses = []
        
        # Try each model
        for model_type in models:
            try:
                result = await self.invoke_with_comprehensive_fallbacks(
                    model_type, 
                    prompt, 
                    context
                )
                
                if result['success']:
                    successful_responses.append({
                        'model': model_type.value,
                        'response': result['result'],
                        'confidence': result['confidence'],
                        'source': result['source']
                    })
                
                voting_results.append(result)
                
            except Exception as e:
                logger.warning(f"Model {model_type.value} failed in voting: {e}")
                voting_results.append({
                    'success': False,
                    'model': model_type.value,
                    'error': str(e)
                })
        
        # Analyze voting results
        if successful_responses:
            # Simple voting: pick response with highest confidence
            best_response = max(successful_responses, key=lambda x: x['confidence'])
            
            return {
                'success': True,
                'result': best_response['response'],
                'fallback_level': FallbackLevel.FULL_SERVICE,
                'source': 'model_voting',
                'confidence': best_response['confidence'],
                'voting_results': voting_results,
                'winner': best_response['model'],
                'total_votes': len(successful_responses)
            }
        
        # If voting completely failed, try comprehensive fallbacks with best available model
        logger.warning("All models failed in voting, falling back to single model strategy")
        
        # Use the most capable available model as fallback
        fallback_models = [ModelType.REASONING, ModelType.STANDARD, ModelType.FAST]
        for fallback_model in fallback_models:
            if self.model_manager.is_model_available(fallback_model):
                fallback_result = await self.invoke_with_comprehensive_fallbacks(
                    fallback_model,
                    prompt,
                    context
                )
                
                fallback_result.update({
                    'voting_failed': True,
                    'voting_results': voting_results,
                    'fallback_model': fallback_model.value
                })
                
                return fallback_result
        
        # Complete failure
        return {
            'success': False,
            'result': 'All models and fallback strategies failed',
            'fallback_level': FallbackLevel.SERVICE_DOWN,
            'source': 'complete_failure',
            'confidence': 0.0,
            'voting_results': voting_results
        }
    
    async def invoke_with_progressive_degradation(
        self,
        prompt: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Progressive degradation: try models from most to least capable.
        Each level provides increasingly simple responses.
        """
        context = context or {}
        context['operation_type'] = 'progressive_degradation'
        
        # Define progressive model chain with adapted prompts
        degradation_levels = [
            {
                'model': ModelType.REASONING,
                'prompt': prompt,
                'level': FallbackLevel.FULL_SERVICE,
                'description': 'Full reasoning capability'
            },
            {
                'model': ModelType.STANDARD,
                'prompt': f"Provide a concise answer: {prompt}",
                'level': FallbackLevel.DEGRADED_SERVICE,
                'description': 'Standard processing with simplified prompt'
            },
            {
                'model': ModelType.FAST,
                'prompt': f"Brief answer only: {prompt}",
                'level': FallbackLevel.MINIMAL_SERVICE,
                'description': 'Fast processing with minimal prompt'
            }
        ]
        
        attempted_levels = []
        
        for level in degradation_levels:
            if not self.model_manager.is_model_available(level['model']):
                attempted_levels.append({
                    'model': level['model'].value,
                    'result': 'model_unavailable',
                    'level': level['level']
                })
                continue
            
            try:
                logger.info(f"Trying progressive degradation level: {level['description']}")
                
                result = await self.invoke_with_comprehensive_fallbacks(
                    level['model'],
                    level['prompt'],
                    context
                )
                
                attempted_levels.append({
                    'model': level['model'].value,
                    'result': 'success' if result['success'] else 'failed',
                    'level': level['level'],
                    'confidence': result.get('confidence', 0.0)
                })
                
                if result['success']:
                    result.update({
                        'degradation_level': level['level'],
                        'degradation_description': level['description'],
                        'attempted_levels': attempted_levels
                    })
                    return result
                    
            except Exception as e:
                logger.warning(f"Progressive degradation level failed: {e}")
                attempted_levels.append({
                    'model': level['model'].value,
                    'result': f'error: {str(e)}',
                    'level': level['level']
                })
        
        # All progressive levels failed, use comprehensive fallbacks
        logger.warning("All progressive degradation levels failed, using comprehensive fallbacks")
        
        fallback_result = await self.fallback_manager.execute_with_fallbacks(
            lambda: None,  # Dummy operation since models already failed
            f"progressive_fallback_{self.operation_counter}",
            prompt,
            context
        )
        
        fallback_result.update({
            'progressive_degradation_failed': True,
            'attempted_levels': attempted_levels
        })
        
        return fallback_result
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all fallback systems."""
        return {
            'service_level': self.fallback_manager.get_service_level().value,
            'model_stats': self.model_manager.get_retry_stats(),
            'fallback_stats': self.fallback_manager.get_fallback_stats(),
            'circuit_breakers': {
                model.value: self.model_manager.get_circuit_status(model)
                for model in ModelType 
                if self.model_manager.is_model_available(model)
            },
            'available_models': [m.value for m in self.model_manager.get_available_models()],
            'operations_count': self.operation_counter
        }