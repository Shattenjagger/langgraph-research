"""Local model configurations for different use cases."""
from enum import Enum
from pydantic import BaseModel
from typing import Dict, Any, Optional


class ModelType(Enum):
    """Model types for different processing needs."""
    FAST = "fast"
    STANDARD = "standard" 
    REASONING = "reasoning"


class ModelConfig(BaseModel):
    """Configuration for a local model."""
    name: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30
    description: str = ""
    

class LocalModelConfigs:
    """Central configuration for all local models."""
    
    MODELS: Dict[ModelType, ModelConfig] = {
        ModelType.FAST: ModelConfig(
            name="Fast Processing",
            model_id="llama3.2:1b",
            temperature=0.3,
            max_tokens=2048,
            timeout=15,
            description="Quick decisions and simple tasks"
        ),
        ModelType.STANDARD: ModelConfig(
            name="Standard Processing", 
            model_id="llama3.2:3b",
            temperature=0.7,
            max_tokens=4096,
            timeout=30,
            description="General purpose processing"
        ),
        ModelType.REASONING: ModelConfig(
            name="Complex Reasoning",
            model_id="llama3.1:8b", 
            temperature=0.5,
            max_tokens=8192,
            timeout=60,
            description="Complex analysis and reasoning tasks"
        )
    }
    
    @classmethod
    def get_config(cls, model_type: ModelType) -> ModelConfig:
        """Get configuration for a specific model type."""
        return cls.MODELS[model_type]
    
    @classmethod
    def get_fallback_chain(cls, primary: ModelType) -> list[ModelType]:
        """Get fallback chain for a given primary model."""
        fallback_chains = {
            ModelType.REASONING: [ModelType.STANDARD, ModelType.FAST],
            ModelType.STANDARD: [ModelType.FAST],
            ModelType.FAST: []
        }
        return fallback_chains.get(primary, [])