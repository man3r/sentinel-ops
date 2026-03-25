import requests
import uuid
from datetime import datetime, timezone

def trigger():
    incident_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    payload = {
        "incident_id": incident_id,
        "severity": "SEV1_CRITICAL",
        "affected_service": "mortgage-application-gateway",
        "confidence": 0.98,
        "error_pattern": "ConnectionPoolTimeout: Exceeded maximum wait time of 5000ms",
        "error_rate_pct": 4.25,
        "window_start": now,
        "window_end": now,
        "sanitized_trace": "at com.lending.mortgage.Gateway.submit(Gateway.java:152)"
    }
    
    url = "http://localhost:8000/internal/incident"
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger()
