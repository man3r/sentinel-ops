import re
from typing import Dict, Pattern

class PIISanitizer:
    """
    Scans raw log tracing and replaces sensitive lending/payment PII
    with standard masks (e.g. <SSN_REDACTED>) before it leaves the VPC.
    """
    
    # Pre-compiled Regex patterns for high performance log scanning
    PATTERNS: Dict[str, Pattern] = {
        "SSN": re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
        "CREDIT_CARD": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'),
        "PHONE": re.compile(r'\b\+?\d{1,3}[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b'),
        "LOAN_APP_ID": re.compile(r'\bLA-[A-Z0-9]{8,12}\b'), # Proprietary loan app id format
        "AUTH_BEARER": re.compile(r'Bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*'),
        "AWS_KEY": re.compile(r'(?i)aws_access_key_id\s*[:=]\s*[A-Z0-9]{20}'),
    }

    @classmethod
    def sanitize(cls, raw_log: str) -> str:
        """
        Takes a raw log string and returns an aggressively sanitized version.
        Runs recursively on the patterns list.
        """
        if not raw_log:
            return raw_log
            
        sanitized = raw_log
        for pii_type, pattern in cls.PATTERNS.items():
            sanitized = pattern.sub(f"<{pii_type}_REDACTED>", sanitized)
            
        return sanitized
