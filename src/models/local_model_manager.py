"""Manager for local Ollama models with retry and fallback logic."""
import asyncio
import logging
from typing import Optional, Dict, Any
from langchain_ollama import OllamaLLM
from .model_configs import ModelType, LocalModelConfigs
from ..utils.retry_handler import AdvancedRetryHandler, RetryConfig, RetryStrategy, RetryableError

logger = logging.getLogger(__name__)


class LocalModelManager:
    """Manages local model instances and provides retry/fallback capabilities."""
    
    def __init__(self):
        self._models: Dict[ModelType, OllamaLLM] = {}
        self.retry_handler = AdvancedRetryHandler()
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize all configured models."""
        for model_type, config in LocalModelConfigs.MODELS.items():
            try:
                self._models[model_type] = OllamaLLM(
                    model=config.model_id,
                    temperature=config.temperature,
                    timeout=config.timeout
                )
                logger.info(f"Initialized {model_type.value} model: {config.model_id}")
            except Exception as e:
                logger.error(f"Failed to initialize {model_type.value} model: {e}")
    
    async def invoke_with_fallback(
        self, 
        model_type: ModelType,
        prompt: str,
        max_retries: int = 2,
        use_advanced_retry: bool = True
    ) -> str:
        """
        Invoke a model with automatic fallback to simpler models if needed.
        
        Args:
            model_type: Primary model type to try
            prompt: Input prompt
            max_retries: Maximum retry attempts per model
            use_advanced_retry: Whether to use advanced retry mechanisms
            
        Returns:
            Model response string
        """
        if use_advanced_retry:
            return await self._invoke_with_advanced_retry(model_type, prompt)
        else:
            return await self._invoke_with_basic_retry(model_type, prompt, max_retries)
    
    async def _invoke_with_advanced_retry(self, model_type: ModelType, prompt: str) -> str:
        """Invoke with advanced retry and circuit breaker logic."""
        # Configure retry behavior based on model type
        config = self._get_retry_config(model_type)
        
        # Try primary model with advanced retry
        try:
            result = await self.retry_handler.execute_with_retry(
                self._invoke_single_model,
                f"model_{model_type.value}",
                config,
                model_type,
                prompt
            )
            return result
        except Exception as primary_error:
            logger.warning(f"Primary model {model_type.value} failed: {primary_error}")
        
        # Try fallback models
        fallback_chain = LocalModelConfigs.get_fallback_chain(model_type)
        for fallback_type in fallback_chain:
            logger.info(f"Trying fallback model: {fallback_type.value}")
            try:
                fallback_config = self._get_retry_config(fallback_type)
                result = await self.retry_handler.execute_with_retry(
                    self._invoke_single_model,
                    f"model_{fallback_type.value}",
                    fallback_config,
                    fallback_type,
                    prompt
                )
                return result
            except Exception as fallback_error:
                logger.warning(f"Fallback model {fallback_type.value} failed: {fallback_error}")
        
        raise RuntimeError("All models failed to generate response after advanced retry")
    
    async def _invoke_with_basic_retry(self, model_type: ModelType, prompt: str, max_retries: int) -> str:
        """Original basic retry logic for comparison."""
        # Try primary model first
        result = await self._try_model(model_type, prompt, max_retries)
        if result:
            return result
            
        # Try fallback models
        fallback_chain = LocalModelConfigs.get_fallback_chain(model_type)
        for fallback_type in fallback_chain:
            logger.warning(f"Trying fallback model: {fallback_type.value}")
            result = await self._try_model(fallback_type, prompt, max_retries)
            if result:
                return result
        
        # All models failed
        raise RuntimeError("All models failed to generate response")
    
    async def _try_model(
        self, 
        model_type: ModelType, 
        prompt: str, 
        max_retries: int
    ) -> Optional[str]:
        """Try a specific model with retries."""
        if model_type not in self._models:
            logger.error(f"Model {model_type.value} not available")
            return None
            
        model = self._models[model_type]
        config = LocalModelConfigs.get_config(model_type)
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Attempting {model_type.value} model (attempt {attempt + 1})")
                
                # Use asyncio to run the sync model call with timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(model.invoke, prompt),
                    timeout=config.timeout
                )
                
                if result and result.strip():
                    logger.info(f"Success with {model_type.value} model")
                    return result.strip()
                    
            except asyncio.TimeoutError:
                logger.warning(f"{model_type.value} model timed out (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"{model_type.value} model error (attempt {attempt + 1}): {e}")
        
        logger.error(f"All attempts failed for {model_type.value} model")
        return None
    
    def get_available_models(self) -> list[ModelType]:
        """Get list of successfully initialized models."""
        return list(self._models.keys())
    
    def is_model_available(self, model_type: ModelType) -> bool:
        """Check if a specific model is available."""
        return model_type in self._models
    
    def _get_retry_config(self, model_type: ModelType) -> RetryConfig:
        """Get retry configuration based on model type."""
        config = LocalModelConfigs.get_config(model_type)
        
        # Configure retry based on model characteristics
        if model_type == ModelType.FAST:
            return RetryConfig(
                max_attempts=4,
                base_delay=0.5,
                max_delay=10.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                failure_threshold=3,
                recovery_timeout=15.0
            )
        elif model_type == ModelType.STANDARD:
            return RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                failure_threshold=4,
                recovery_timeout=30.0
            )
        else:  # REASONING model
            return RetryConfig(
                max_attempts=2,
                base_delay=2.0,
                max_delay=60.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                failure_threshold=2,
                recovery_timeout=45.0
            )
    
    async def _invoke_single_model(self, model_type: ModelType, prompt: str) -> str:
        """Invoke a single model - used by retry handler."""
        if model_type not in self._models:
            raise RetryableError(f"Model {model_type.value} not available")
        
        model = self._models[model_type]
        config = LocalModelConfigs.get_config(model_type)
        
        try:
            # Use asyncio to run the sync model call with timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(model.invoke, prompt),
                timeout=config.timeout
            )
            
            if not result or not result.strip():
                raise RetryableError("Model returned empty response")
            
            return result.strip()
            
        except asyncio.TimeoutError:
            raise RetryableError(f"Model {model_type.value} timed out", retry_after=2.0)
        except Exception as e:
            # Convert most exceptions to retryable errors
            error_msg = str(e).lower()
            if any(term in error_msg for term in ['connection', 'network', 'timeout', 'unavailable']):
                raise RetryableError(f"Model {model_type.value} connection error: {str(e)}")
            else:
                # Re-raise as is for non-retryable errors
                raise e
    
    def get_retry_stats(self, model_type: Optional[ModelType] = None) -> Dict[str, Any]:
        """Get retry statistics for models."""
        if model_type:
            operation_id = f"model_{model_type.value}"
            return self.retry_handler.get_retry_stats(operation_id)
        else:
            # Get stats for all models
            all_stats = {}
            for mt in ModelType:
                operation_id = f"model_{mt.value}"
                stats = self.retry_handler.get_retry_stats(operation_id)
                if stats.get("total_operations", 0) > 0:
                    all_stats[mt.value] = stats
            return all_stats
    
    def get_circuit_status(self, model_type: ModelType) -> Dict[str, Any]:
        """Get circuit breaker status for a model."""
        operation_id = f"model_{model_type.value}"
        return self.retry_handler.get_circuit_status(operation_id)