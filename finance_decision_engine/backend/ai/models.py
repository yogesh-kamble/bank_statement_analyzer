from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InsightResult:
    insight: str
    suggestion: str


@dataclass
class Explanation:
    """Plain-language explanation of results the engine already computed."""

    summary: str
    key_points: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    source: str = "fallback"  # "ai" | "fallback"
    model: Optional[str] = None
