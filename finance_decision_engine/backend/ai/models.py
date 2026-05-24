from dataclasses import dataclass


@dataclass
class InsightResult:
    insight: str
    suggestion: str