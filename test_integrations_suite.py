import asyncio
import httpx
import re
import socket
from urllib.parse import urlparse

# Mocking the validation logic from integrations.py
async def validate_integration(provider_id, config):
    print(f"\n--- Testing provider: {provider_id} ---")
    print(f"Config: {config}")
    
    try:
        if provider_id == "aws":
            region = config.get("region", "")
            opensearch = config.get("opensearch", "")
            
            # Region list
            valid_regions = ["us-east-1", "us-east-2", "us-west-2", "eu-central-1", "eu-west-1", "eu-west-2", "eu-west-3", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ca-central-1", "sa-east-1"]
            if region not in valid_regions:
                 print(f"FAIL: Invalid Region {region}")
                 return

            if not re.match(r"^https:\/\/[a-z0-9-]+\.[a-z0-9-]+\.aoss\.amazonaws\.com\/?$", opensearch):
                print(f"FAIL: Invalid OpenSearch URL {opensearch}")
                return
            
            async with httpx.AsyncClient(timeout=3.0) as client:
                try:
                    resp = await client.get(opensearch)
                    if resp.status_code == 404:
                         print(f"FAIL: AOSS Collection not found (404)")
                         return
                    print(f"PASS: AWS (Status {resp.status_code})")
                except Exception as e:
                    print(f"FAIL: AWS Network Error: {e}")

        elif provider_id == "database":
            uri = config.get("uri", "")
            if not (uri.startswith("postgresql://") or uri.startswith("mysql://") or uri.startswith("oracle://")):
                print("FAIL: Invalid schema")
                return
            
            parsed = urlparse(uri)
            host = parsed.hostname
            port = parsed.port if parsed.port else 5432
            
            if not host:
                print("FAIL: No host identified")
                return

            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2.0)
                writer.close()
                await writer.wait_closed()
                print(f"PASS: Database connected to {host}:{port}")
            except Exception as e:
                print(f"FAIL: Database connection failed: {e}")

        elif provider_id == "github":
             base_url = config.get("base_url", "")
             if not base_url.startswith("https://"):
                 print("FAIL: Bad URL")
                 return
             
             try:
                 async with httpx.AsyncClient(timeout=2.0) as client:
                     resp = await client.get(f"{base_url}/user")
                     if resp.status_code == 404:
                         print("FAIL: GitHub GHES 404")
                     elif resp.status_code == 200:
                         print("PASS: GitHub 200")
                     else:
                         print(f"PASS/FAIL (Auth required): {resp.status_code}")
             except Exception as e:
                 print(f"FAIL: GitHub Network error: {e}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

async def run_suite():
    # Database Negative
    await validate_integration("database", {"uri": "postgresql://junk.db.com:5432"})
    # Database Happy (assuming localhost or something reachable)
    await validate_integration("database", {"uri": "postgresql://127.0.0.1:5432"})
    
    # AWS Negative (URL pattern)
    await validate_integration("aws", {"region": "us-east-1", "opensearch": "https://junk.com"})
    # AWS Negative (Region)
    await validate_integration("aws", {"region": "us-junk-9", "opensearch": "https://abc.us-east-1.aoss.amazonaws.com"})
    # AWS Negative (404)
    await validate_integration("aws", {"region": "us-east-1", "opensearch": "https://abc.us-east-1.aoss.amazonaws.com"})

    # GitHub Negative
    await validate_integration("github", {"base_url": "https://fake-github.com", "secret": "abc"})

run_suite = asyncio.run(run_suite())
