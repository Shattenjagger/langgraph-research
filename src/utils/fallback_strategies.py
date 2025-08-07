"""Sophisticated fallback strategies with caching, human handoff, and graceful degradation."""
import asyncio
import logging
import json
import hashlib
import sqlite3
import time
from typing import Dict, Any, Optional, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class FallbackLevel(Enum):
    """Levels of fallback degradation."""
    FULL_SERVICE = "full_service"          # All models working normally
    DEGRADED_SERVICE = "degraded_service"  # Some models down, using fallbacks
    MINIMAL_SERVICE = "minimal_service"    # Only basic functionality
    CACHE_ONLY = "cache_only"             # Using cached responses only
    HUMAN_HANDOFF = "human_handoff"       # Requiring human intervention
    SERVICE_DOWN = "service_down"         # Complete service failure


class CacheStrategy(Enum):
    """Cache lookup strategies."""
    EXACT_MATCH = "exact_match"           # Exact prompt match
    SEMANTIC_MATCH = "semantic_match"     # Similar meaning match
    PARTIAL_MATCH = "partial_match"       # Partial prompt match
    TEMPLATE_MATCH = "template_match"     # Template-based match


@dataclass
class CachedResponse:
    """Cached response entry."""
    prompt_hash: str
    original_prompt: str
    response: str
    model_type: str
    timestamp: datetime
    success_count: int = 0
    failure_count: int = 0
    confidence_score: float = 1.0
    tags: List[str] = field(default_factory=list)


@dataclass
class HumanHandoffRequest:
    """Request for human intervention."""
    request_id: str
    original_prompt: str
    failure_reason: str
    attempted_fallbacks: List[str]
    timestamp: datetime
    priority: int = 1  # 1=low, 5=critical
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, assigned, completed, cancelled


class ResponseCache:
    """Intelligent response caching system."""
    
    def __init__(self, db_path: str = "response_cache.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for caching."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cached_responses (
                    prompt_hash TEXT PRIMARY KEY,
                    original_prompt TEXT,
                    response TEXT,
                    model_type TEXT,
                    timestamp TEXT,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    confidence_score REAL DEFAULT 1.0,
                    tags TEXT
                )
            """)
            conn.commit()
    
    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash for prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    async def get_cached_response(
        self, 
        prompt: str, 
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH
    ) -> Optional[CachedResponse]:
        """Get cached response using specified strategy."""
        
        if strategy == CacheStrategy.EXACT_MATCH:
            return await self._get_exact_match(prompt)
        elif strategy == CacheStrategy.SEMANTIC_MATCH:
            return await self._get_semantic_match(prompt)
        elif strategy == CacheStrategy.PARTIAL_MATCH:
            return await self._get_partial_match(prompt)
        elif strategy == CacheStrategy.TEMPLATE_MATCH:
            return await self._get_template_match(prompt)
        
        return None
    
    async def _get_exact_match(self, prompt: str) -> Optional[CachedResponse]:
        """Get exact prompt match."""
        prompt_hash = self._hash_prompt(prompt)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM cached_responses WHERE prompt_hash = ?",
                (prompt_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                return CachedResponse(
                    prompt_hash=row['prompt_hash'],
                    original_prompt=row['original_prompt'],
                    response=row['response'],
                    model_type=row['model_type'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    success_count=row['success_count'],
                    failure_count=row['failure_count'],
                    confidence_score=row['confidence_score'],
                    tags=json.loads(row['tags']) if row['tags'] else []
                )
        
        return None
    
    async def _get_semantic_match(self, prompt: str) -> Optional[CachedResponse]:
        """Get semantically similar response (simplified version)."""
        # For this demo, we'll use keyword matching
        # In production, you'd use embedding similarity
        
        prompt_words = set(prompt.lower().split())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM cached_responses")
            
            best_match = None
            best_score = 0
            
            for row in cursor:
                cached_words = set(row['original_prompt'].lower().split())
                intersection = prompt_words.intersection(cached_words)
                union = prompt_words.union(cached_words)
                
                # Jaccard similarity
                score = len(intersection) / len(union) if union else 0
                
                if score > 0.6 and score > best_score:  # Threshold for semantic match
                    best_score = score
                    best_match = CachedResponse(
                        prompt_hash=row['prompt_hash'],
                        original_prompt=row['original_prompt'],
                        response=row['response'],
                        model_type=row['model_type'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        success_count=row['success_count'],
                        failure_count=row['failure_count'],
                        confidence_score=row['confidence_score'] * score,  # Adjust confidence
                        tags=json.loads(row['tags']) if row['tags'] else []
                    )
        
        return best_match
    
    async def _get_partial_match(self, prompt: str) -> Optional[CachedResponse]:
        """Get partial prompt match."""
        # Simple substring matching for demo
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM cached_responses WHERE original_prompt LIKE ? LIMIT 1",
                (f"%{prompt[:50]}%",)
            )
            row = cursor.fetchone()
            
            if row:
                return CachedResponse(
                    prompt_hash=row['prompt_hash'],
                    original_prompt=row['original_prompt'],
                    response=row['response'],
                    model_type=row['model_type'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    success_count=row['success_count'],
                    failure_count=row['failure_count'],
                    confidence_score=row['confidence_score'] * 0.7,  # Lower confidence for partial
                    tags=json.loads(row['tags']) if row['tags'] else []
                )
        
        return None
    
    async def _get_template_match(self, prompt: str) -> Optional[CachedResponse]:
        """Get template-based match for common patterns."""
        # Identify common prompt templates
        templates = [
            ("what is", "definition"),
            ("how to", "instruction"),
            ("explain", "explanation"),
            ("calculate", "calculation"),
            ("translate", "translation")
        ]
        
        prompt_lower = prompt.lower()
        for template_key, tag in templates:
            if template_key in prompt_lower:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM cached_responses WHERE tags LIKE ? LIMIT 1",
                        (f'%"{tag}"%',)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return CachedResponse(
                            prompt_hash=row['prompt_hash'],
                            original_prompt=row['original_prompt'],
                            response=row['response'],
                            model_type=row['model_type'],
                            timestamp=datetime.fromisoformat(row['timestamp']),
                            success_count=row['success_count'],
                            failure_count=row['failure_count'],
                            confidence_score=row['confidence_score'] * 0.5,  # Lower confidence
                            tags=json.loads(row['tags']) if row['tags'] else []
                        )
        
        return None
    
    async def cache_response(
        self, 
        prompt: str, 
        response: str, 
        model_type: str,
        tags: List[str] = None
    ):
        """Cache a response."""
        prompt_hash = self._hash_prompt(prompt)
        tags = tags or []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cached_responses 
                (prompt_hash, original_prompt, response, model_type, timestamp, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                prompt_hash,
                prompt,
                response,
                model_type,
                datetime.now().isoformat(),
                json.dumps(tags)
            ))
            conn.commit()
    
    async def update_cache_stats(self, prompt_hash: str, success: bool):
        """Update cache hit statistics."""
        with sqlite3.connect(self.db_path) as conn:
            if success:
                conn.execute(
                    "UPDATE cached_responses SET success_count = success_count + 1 WHERE prompt_hash = ?",
                    (prompt_hash,)
                )
            else:
                conn.execute(
                    "UPDATE cached_responses SET failure_count = failure_count + 1 WHERE prompt_hash = ?",
                    (prompt_hash,)
                )
            conn.commit()


class HumanHandoffQueue:
    """Queue for requests requiring human intervention."""
    
    def __init__(self, db_path: str = "handoff_queue.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for handoff queue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS handoff_requests (
                    request_id TEXT PRIMARY KEY,
                    original_prompt TEXT,
                    failure_reason TEXT,
                    attempted_fallbacks TEXT,
                    timestamp TEXT,
                    priority INTEGER DEFAULT 1,
                    context TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.commit()
    
    async def add_request(self, request: HumanHandoffRequest):
        """Add request to handoff queue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO handoff_requests 
                (request_id, original_prompt, failure_reason, attempted_fallbacks, 
                 timestamp, priority, context, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                request.original_prompt,
                request.failure_reason,
                json.dumps(request.attempted_fallbacks),
                request.timestamp.isoformat(),
                request.priority,
                json.dumps(request.context),
                request.status
            ))
            conn.commit()
        
        logger.info(f"Added handoff request {request.request_id} to queue (priority: {request.priority})")
    
    async def get_pending_requests(self, limit: int = 10) -> List[HumanHandoffRequest]:
        """Get pending requests ordered by priority."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM handoff_requests 
                WHERE status = 'pending' 
                ORDER BY priority DESC, timestamp ASC 
                LIMIT ?
            """, (limit,))
            
            requests = []
            for row in cursor:
                requests.append(HumanHandoffRequest(
                    request_id=row['request_id'],
                    original_prompt=row['original_prompt'],
                    failure_reason=row['failure_reason'],
                    attempted_fallbacks=json.loads(row['attempted_fallbacks']),
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    priority=row['priority'],
                    context=json.loads(row['context']),
                    status=row['status']
                ))
            
            return requests


class FallbackStrategyManager:
    """Manages sophisticated fallback strategies."""
    
    def __init__(self):
        self.cache = ResponseCache()
        self.handoff_queue = HumanHandoffQueue()
        self.current_service_level = FallbackLevel.FULL_SERVICE
        self.fallback_history: List[Dict[str, Any]] = []
    
    async def execute_with_fallbacks(
        self,
        primary_operation: Callable,
        operation_id: str,
        prompt: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute operation with comprehensive fallback strategies.
        
        Returns:
            Dict with keys: success, result, fallback_level, source, confidence
        """
        context = context or {}
        attempted_fallbacks = []
        
        # Level 1: Try primary operation
        try:
            logger.info(f"Attempting primary operation: {operation_id}")
            result = await primary_operation()
            
            # Cache successful response
            await self.cache.cache_response(
                prompt, 
                str(result), 
                context.get('model_type', 'unknown')
            )
            
            return {
                "success": True,
                "result": result,
                "fallback_level": FallbackLevel.FULL_SERVICE,
                "source": "primary",
                "confidence": 1.0
            }
            
        except Exception as primary_error:
            logger.warning(f"Primary operation failed: {primary_error}")
            attempted_fallbacks.append(f"primary: {str(primary_error)}")
        
        # Level 2: Try exact cache match
        try:
            cached = await self.cache.get_cached_response(prompt, CacheStrategy.EXACT_MATCH)
            if cached and cached.confidence_score > 0.8:
                logger.info(f"Using exact cache match for {operation_id}")
                await self.cache.update_cache_stats(cached.prompt_hash, True)
                
                return {
                    "success": True,
                    "result": cached.response,
                    "fallback_level": FallbackLevel.DEGRADED_SERVICE,
                    "source": "cache_exact",
                    "confidence": cached.confidence_score
                }
        except Exception as cache_error:
            attempted_fallbacks.append(f"exact_cache: {str(cache_error)}")
        
        # Level 3: Try semantic cache match
        try:
            cached = await self.cache.get_cached_response(prompt, CacheStrategy.SEMANTIC_MATCH)
            if cached and cached.confidence_score > 0.6:
                logger.info(f"Using semantic cache match for {operation_id}")
                await self.cache.update_cache_stats(cached.prompt_hash, True)
                
                return {
                    "success": True,
                    "result": f"[Similar response] {cached.response}",
                    "fallback_level": FallbackLevel.MINIMAL_SERVICE,
                    "source": "cache_semantic",
                    "confidence": cached.confidence_score
                }
        except Exception as semantic_error:
            attempted_fallbacks.append(f"semantic_cache: {str(semantic_error)}")
        
        # Level 4: Try template-based response
        try:
            template_response = await self._generate_template_response(prompt)
            if template_response:
                logger.info(f"Using template response for {operation_id}")
                
                return {
                    "success": True,
                    "result": template_response,
                    "fallback_level": FallbackLevel.MINIMAL_SERVICE,
                    "source": "template",
                    "confidence": 0.3
                }
        except Exception as template_error:
            attempted_fallbacks.append(f"template: {str(template_error)}")
        
        # Level 5: Human handoff
        try:
            handoff_request = HumanHandoffRequest(
                request_id=f"{operation_id}_{int(time.time())}",
                original_prompt=prompt,
                failure_reason=f"All fallbacks failed: {attempted_fallbacks}",
                attempted_fallbacks=attempted_fallbacks,
                timestamp=datetime.now(),
                priority=self._determine_priority(context),
                context=context
            )
            
            await self.handoff_queue.add_request(handoff_request)
            
            return {
                "success": False,
                "result": f"Request queued for human review (ID: {handoff_request.request_id})",
                "fallback_level": FallbackLevel.HUMAN_HANDOFF,
                "source": "human_queue",
                "confidence": 0.0,
                "handoff_id": handoff_request.request_id
            }
            
        except Exception as handoff_error:
            attempted_fallbacks.append(f"human_handoff: {str(handoff_error)}")
        
        # Complete failure
        self._record_failure(operation_id, prompt, attempted_fallbacks)
        
        return {
            "success": False,
            "result": "All fallback strategies failed",
            "fallback_level": FallbackLevel.SERVICE_DOWN,
            "source": "failure",
            "confidence": 0.0,
            "attempted_fallbacks": attempted_fallbacks
        }
    
    async def _generate_template_response(self, prompt: str) -> Optional[str]:
        """Generate template-based response for common patterns."""
        prompt_lower = prompt.lower()
        
        # Simple template responses
        if any(word in prompt_lower for word in ['hello', 'hi', 'greeting']):
            return "Hello! I'm currently experiencing technical difficulties. Please try again later or contact support."
        
        elif any(word in prompt_lower for word in ['help', 'support']):
            return "For immediate assistance, please contact our support team. We apologize for the inconvenience."
        
        elif any(word in prompt_lower for word in ['what is', 'define']):
            return "I'm unable to process your request at the moment. Please try rephrasing your question or contact support."
        
        elif any(word in prompt_lower for word in ['calculate', 'compute']):
            return "Our calculation services are temporarily unavailable. Please try again later."
        
        else:
            return "I'm currently experiencing technical difficulties. Your request has been noted and will be processed as soon as possible."
    
    def _determine_priority(self, context: Dict[str, Any]) -> int:
        """Determine priority for human handoff."""
        priority = 1  # Default low priority
        
        # Increase priority based on context
        if context.get('document_type') == 'contract':
            priority = max(priority, 3)
        
        if context.get('user_tier') == 'premium':
            priority = max(priority, 4)
        
        if context.get('urgent', False):
            priority = 5
        
        return priority
    
    def _record_failure(self, operation_id: str, prompt: str, attempted_fallbacks: List[str]):
        """Record complete failure for analysis."""
        self.fallback_history.append({
            "timestamp": datetime.now().isoformat(),
            "operation_id": operation_id,
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "attempted_fallbacks": attempted_fallbacks,
            "result": "complete_failure"
        })
        
        logger.error(f"Complete fallback failure for {operation_id}")
    
    def get_service_level(self) -> FallbackLevel:
        """Get current service level."""
        return self.current_service_level
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get fallback usage statistics."""
        if not self.fallback_history:
            return {"total_operations": 0}
        
        total = len(self.fallback_history)
        failures = len([h for h in self.fallback_history if h["result"] == "complete_failure"])
        
        return {
            "total_operations": total,
            "complete_failures": failures,
            "failure_rate": failures / total if total > 0 else 0,
            "recent_failures": self.fallback_history[-5:]  # Last 5 failures
        }