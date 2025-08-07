"""Advanced retry mechanisms with exponential backoff and circuit breakers."""
import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Different retry strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff" 
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open (failing fast)
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Specific retry conditions
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_on_parse_error: bool = True
    retry_on_empty_response: bool = True
    
    # Circuit breaker settings
    enable_circuit_breaker: bool = True
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    success_threshold: int = 2  # For half-open state


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None


class RetryableError(Exception):
    """Base class for errors that should trigger retries."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class NonRetryableError(Exception):
    """Base class for errors that should NOT trigger retries."""
    pass


class AdvancedRetryHandler:
    """Advanced retry handler with circuit breakers and intelligent backoff."""
    
    def __init__(self, default_config: RetryConfig = None):
        self.default_config = default_config or RetryConfig()
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.retry_history: List[Dict[str, Any]] = []
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_id: str,
        config: Optional[RetryConfig] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with advanced retry logic.
        
        Args:
            operation: Async function to execute
            operation_id: Unique identifier for circuit breaker
            config: Retry configuration (uses default if None)
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If all retries are exhausted
        """
        config = config or self.default_config
        
        # Check circuit breaker
        if config.enable_circuit_breaker:
            if not self._can_execute(operation_id, config):
                raise NonRetryableError(f"Circuit breaker OPEN for {operation_id}")
        
        last_exception = None
        attempt = 0
        
        while attempt < config.max_attempts:
            attempt += 1
            
            try:
                start_time = time.time()
                
                # Execute the operation
                result = await operation(*args, **kwargs)
                
                # Record success
                execution_time = time.time() - start_time
                self._record_success(operation_id, config, attempt, execution_time)
                
                return result
                
            except Exception as e:
                last_exception = e
                execution_time = time.time() - start_time
                
                # Determine if this error should trigger retry
                should_retry = self._should_retry(e, attempt, config)
                
                logger.warning(
                    f"Attempt {attempt}/{config.max_attempts} failed for {operation_id}: "
                    f"{type(e).__name__}: {str(e)} (will_retry: {should_retry})"
                )
                
                # Record failure
                self._record_failure(operation_id, config, attempt, execution_time, e)
                
                if not should_retry or attempt >= config.max_attempts:
                    break
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt, config, e)
                if delay > 0:
                    logger.info(f"Waiting {delay:.2f}s before retry {attempt + 1}")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(f"All retries exhausted for {operation_id}")
        raise last_exception
    
    def _can_execute(self, operation_id: str, config: RetryConfig) -> bool:
        """Check if circuit breaker allows execution."""
        if operation_id not in self.circuit_breakers:
            self.circuit_breakers[operation_id] = CircuitBreakerState()
        
        breaker = self.circuit_breakers[operation_id]
        now = datetime.now()
        
        if breaker.state == CircuitState.CLOSED:
            return True
        
        elif breaker.state == CircuitState.OPEN:
            # Check if we should try again
            if (breaker.next_attempt_time and now >= breaker.next_attempt_time):
                breaker.state = CircuitState.HALF_OPEN
                breaker.success_count = 0
                logger.info(f"Circuit breaker for {operation_id} moving to HALF_OPEN")
                return True
            return False
        
        elif breaker.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def _should_retry(self, exception: Exception, attempt: int, config: RetryConfig) -> bool:
        """Determine if an exception should trigger a retry."""
        # Never retry NonRetryableError
        if isinstance(exception, NonRetryableError):
            return False
        
        # Always retry RetryableError
        if isinstance(exception, RetryableError):
            return True
        
        # Check specific error types
        error_name = type(exception).__name__.lower()
        
        if 'timeout' in error_name and config.retry_on_timeout:
            return True
        
        if any(term in error_name for term in ['connection', 'network']) and config.retry_on_connection_error:
            return True
        
        if any(term in str(exception).lower() for term in ['parse', 'json', 'format']) and config.retry_on_parse_error:
            return True
        
        if 'empty' in str(exception).lower() and config.retry_on_empty_response:
            return True
        
        # Default: retry on most exceptions, but not on specific non-retryable ones
        non_retryable_types = ['ValueError', 'TypeError', 'AttributeError']
        if type(exception).__name__ in non_retryable_types:
            return False
        
        return True
    
    def _calculate_delay(self, attempt: int, config: RetryConfig, exception: Exception) -> float:
        """Calculate delay before next retry."""
        # Check if exception specifies retry delay
        if isinstance(exception, RetryableError) and exception.retry_after:
            return exception.retry_after
        
        if config.strategy == RetryStrategy.IMMEDIATE:
            return 0
        
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt
        
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))
        
        else:
            delay = config.base_delay
        
        # Apply max delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter if enabled
        if config.jitter:
            import random
            jitter_factor = 0.1  # ±10% jitter
            jitter = delay * jitter_factor * (random.random() * 2 - 1)
            delay += jitter
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def _record_success(self, operation_id: str, config: RetryConfig, attempt: int, execution_time: float):
        """Record successful execution."""
        self.retry_history.append({
            "timestamp": datetime.now().isoformat(),
            "operation_id": operation_id,
            "result": "success",
            "attempt": attempt,
            "execution_time": execution_time
        })
        
        # Update circuit breaker
        if config.enable_circuit_breaker and operation_id in self.circuit_breakers:
            breaker = self.circuit_breakers[operation_id]
            
            if breaker.state == CircuitState.HALF_OPEN:
                breaker.success_count += 1
                if breaker.success_count >= config.success_threshold:
                    breaker.state = CircuitState.CLOSED
                    breaker.failure_count = 0
                    logger.info(f"Circuit breaker for {operation_id} reset to CLOSED")
            elif breaker.state == CircuitState.CLOSED:
                breaker.failure_count = 0  # Reset failure count on success
    
    def _record_failure(self, operation_id: str, config: RetryConfig, attempt: int, execution_time: float, exception: Exception):
        """Record failed execution."""
        self.retry_history.append({
            "timestamp": datetime.now().isoformat(),
            "operation_id": operation_id,
            "result": "failure",
            "attempt": attempt,
            "execution_time": execution_time,
            "error": str(exception),
            "error_type": type(exception).__name__
        })
        
        # Update circuit breaker
        if config.enable_circuit_breaker:
            if operation_id not in self.circuit_breakers:
                self.circuit_breakers[operation_id] = CircuitBreakerState()
            
            breaker = self.circuit_breakers[operation_id]
            breaker.failure_count += 1
            breaker.last_failure_time = datetime.now()
            
            # Check if we should open the circuit
            if (breaker.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN] and 
                breaker.failure_count >= config.failure_threshold):
                
                breaker.state = CircuitState.OPEN
                breaker.next_attempt_time = datetime.now() + timedelta(seconds=config.recovery_timeout)
                
                logger.warning(
                    f"Circuit breaker OPENED for {operation_id} "
                    f"(failures: {breaker.failure_count}/{config.failure_threshold})"
                )
    
    def get_circuit_status(self, operation_id: str) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        if operation_id not in self.circuit_breakers:
            return {"state": "not_initialized"}
        
        breaker = self.circuit_breakers[operation_id]
        return {
            "state": breaker.state.value,
            "failure_count": breaker.failure_count,
            "success_count": breaker.success_count,
            "last_failure": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
            "next_attempt": breaker.next_attempt_time.isoformat() if breaker.next_attempt_time else None
        }
    
    def get_retry_stats(self, operation_id: Optional[str] = None) -> Dict[str, Any]:
        """Get retry statistics."""
        history = self.retry_history
        if operation_id:
            history = [h for h in history if h["operation_id"] == operation_id]
        
        if not history:
            return {"total_operations": 0}
        
        total_ops = len(history)
        successes = len([h for h in history if h["result"] == "success"])
        failures = len([h for h in history if h["result"] == "failure"])
        
        # Calculate retry patterns
        retry_counts = {}
        for h in history:
            attempt = h["attempt"]
            if attempt > 1:  # Only count actual retries
                retry_counts[attempt] = retry_counts.get(attempt, 0) + 1
        
        avg_execution_time = sum(h["execution_time"] for h in history) / len(history)
        
        return {
            "total_operations": total_ops,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total_ops if total_ops > 0 else 0,
            "retry_distribution": retry_counts,
            "avg_execution_time": avg_execution_time,
            "operation_id": operation_id
        }