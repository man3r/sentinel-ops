import json
import argparse
import time
import uuid
from datetime import datetime, timezone, timedelta
import urllib.request
from typing import Dict, Any

from agent.modules.perception.pii_sanitizer import PIISanitizer

def generate_mock_payload(sev: str) -> Dict[str, Any]:
    """Generates a mock payload structure simulating Perception Engine output."""
    now = datetime.now(timezone.utc)
    
    if sev == "SEV1":
        raw_trace = (
            "Exception in thread \"main\" java.sql.SQLException: Connection refused. "
            "User email: john.doe@example.com SSN: 123-45-6789. "
            "Attempting to process transaction APP-X987654321 failed. "
            "AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE"
        )
        sanitized_trace = PIISanitizer.sanitize(raw_trace)
        
        return {
            "incident_id": str(uuid.uuid4()),
            "severity": "SEV1_CRITICAL",
            "affected_service": "transaction-processing-service",
            "confidence": 0.98,
            "error_pattern": "Database Connection Refused",
            "error_rate_pct": 12.5,
            "window_start": (now - timedelta(minutes=5)).isoformat(),
            "window_end": now.isoformat(),
            "sanitized_trace": sanitized_trace
        }
    
    elif sev == "SEV2":
        return {
            "incident_id": str(uuid.uuid4()),
            "severity": "SEV2_HIGH",
            "affected_service": "payment-gateway",
            "confidence": 0.85,
            "error_pattern": "502 Bad Gateway to 3rd Party",
            "error_rate_pct": 2.1,
            "window_start": (now - timedelta(minutes=5)).isoformat(),
            "window_end": now.isoformat(),
            "sanitized_trace": PIISanitizer.sanitize("Received 502 from external API for user jane@example.com")
        }

    else:
        return {
            "incident_id": str(uuid.uuid4()),
            "severity": "SEV3_LOW",
            "affected_service": "user-profile-service",
            "confidence": 0.60,
            "error_pattern": "Slow Query Response",
            "error_rate_pct": 0.5,
            "window_start": (now - timedelta(minutes=15)).isoformat(),
            "window_end": now.isoformat(),
            "sanitized_trace": "Query took 5.2s for fetching profile data."
        }

def send_payload(payload: Dict[str, Any], url: str = "http://localhost:8000/internal/incident"):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            print(f"✅ Success: {response.status}")
            print(response.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ Failed to trigger incident: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelOps Mock Incident Generator")
    parser.add_argument("--severity", choices=["SEV1", "SEV2", "SEV3"], default="SEV1", help="Target severity level")
    parser.add_argument("--url", default="http://localhost:8000/internal/incident", help="Target Agent Controller URL")
    
    args = parser.parse_args()
    
    print(f"Generating mock {args.severity} incident...")
    payload = generate_mock_payload(args.severity)
    print(json.dumps(payload, indent=2))
    
    print(f"\nSending to {args.url}...")
    send_payload(payload, args.url)
