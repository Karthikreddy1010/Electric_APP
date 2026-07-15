"""
Metadata container for LLM generation results.
Every LLM response tracks model, provider, prompt_version, generated_at, validated, cache_hit, fallback_used, latency_ms.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

@dataclass
class LLMResponseMetadata:
    model: str
    provider: str
    prompt_version: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validated: bool = True
    cache_hit: bool = False
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    latency_ms: float = 0.0
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
