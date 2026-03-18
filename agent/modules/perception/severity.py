import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class SeverityResult:
    level: str  # SEV1_CRITICAL, SEV2_HIGH, SEV3_LOW
    confidence: float
    trigger_reason: str


class SeverityClassifier:
    """
    Rule-based severity classifier acting as a fast-path baseline for 
    incident routing. Used as a fallback if the Llama 3B model is hallucinating, 
    or to instantly escalate obvious critical errors.
    """
    
    # Keywords that automatically trigger a SEV 1 evaluation
    SEV1_KEYWORDS = [
        "Payment Gateway Timeout",
        "P0",
        "Out of Memory",
        "Deadlock",
        "Database Connection Refused",
        "OOMKilled"
    ]
    
    SEV2_KEYWORDS = [
        "API Rate Limit Exceeded",
        "Slow Query",
        "Circuit Breaker Open",
        "502 Bad Gateway"
    ]

    @classmethod
    def evaluate(cls, log_batch: str, error_rate_pct: Optional[float] = None) -> SeverityResult:
        """
        Evaluates a log batch and an optional metric (like error rate) to
        determine severity.
        """
        # 1. Hard Metrics Override
        if error_rate_pct is not None and error_rate_pct > 5.0:
            return SeverityResult(
                level="SEV1_CRITICAL",
                confidence=1.0,
                trigger_reason=f"Error rate {error_rate_pct}% exceeds 5% SEV1 threshold."
            )
            
        # 2. SEV1 Keyword Match
        for keyword in cls.SEV1_KEYWORDS:
            if re.search(re.escape(keyword), log_batch, re.IGNORECASE):
                return SeverityResult(
                    level="SEV1_CRITICAL",
                    confidence=0.9,
                    trigger_reason=f"Matched SEV1 critical keyword: {keyword}"
                )
                
        # 3. SEV2 Keyword Match
        for keyword in cls.SEV2_KEYWORDS:
            if re.search(re.escape(keyword), log_batch, re.IGNORECASE):
                return SeverityResult(
                    level="SEV2_HIGH",
                    confidence=0.8,
                    trigger_reason=f"Matched SEV2 high keyword: {keyword}"
                )
                
        # 4. Default to SEV3 for all other captured anomalies
        return SeverityResult(
            level="SEV3_LOW",
            confidence=0.5,
            trigger_reason="No critical thresholds or keywords matched. Default log anomaly."
        )
