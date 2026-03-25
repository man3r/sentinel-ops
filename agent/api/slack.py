
@@ -50,7 +50,7 @@ def _verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bo
     # Sort keys for deterministic JSON serialization
     payload_str = json.dumps(payload, sort_keys=True)
 
-    # Pipe-separated attributes
-    raw = f"{prev_hash or ''}|{event_type}|{actor or ''}|{payload_str}|{incident_id or ''}"
+    # Pipe-separated attributes
+    raw = f"{prev_hash or ''}|{event_type}|{actor or ''}|{payload_str}"