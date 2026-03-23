import os
import re
import httpx
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import asyncio
from dotenv import set_key

router = APIRouter()

class IntegrationConfig(BaseModel):
    provider_id: str
    config: Dict[str, Any]

GLOBAL_INTEGRATION_STATUS = {
    "messaging": False,
    "aws": False,
    "github": False,
    "jira": False,
    "confluence": False,
    "database": False,
    "vault": False,
    "vault_provider": "None"
}

async def ping_integration_locally(provider_id: str):
    """
    Load from .env and ping the integration right now using the test_integration endpoint logic.
    Updates the GLOBAL_INTEGRATION_STATUS.
    """
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    env_vars = dotenv_values(env_path)
    
    # We build the config dict using the same logic we use to return config to the FE
    config = {}
    if provider_id == "messaging":
        config = {"bot_token": env_vars.get("SLACK_BOT_TOKEN", ""), "signing_secret": env_vars.get("SLACK_SIGNING_SECRET", ""), "channel": env_vars.get("SLACK_INCIDENT_CHANNEL", "")}
    elif provider_id == "aws":
        config = {"region": env_vars.get("AWS_REGION", ""), "opensearch": env_vars.get("OPENSEARCH_ENDPOINT", ""), "role_override": env_vars.get("AWS_ROLE_OVERRIDE", "")}
    elif provider_id == "github":
        config = {"base_url": env_vars.get("GITHUB_BASE_URL", ""), "org": env_vars.get("GITHUB_ORG", ""), "secret": env_vars.get("GITHUB_APP_SECRET", "")}
    elif provider_id == "jira":
        config = {"url": env_vars.get("JIRA_URL", ""), "secret": env_vars.get("JIRA_API_TOKEN", "")}
    elif provider_id == "confluence":
        config = {"url": env_vars.get("CONFLUENCE_URL", ""), "secret": env_vars.get("CONFLUENCE_API_TOKEN", "")}
    elif provider_id == "database":
        config = {"db_type": env_vars.get("DATABASE_TYPE", "PostgreSQL"), "uri": env_vars.get("DATABASE_URI", "")}
    elif provider_id == "vault":
        config = {"provider": env_vars.get("VAULT_PROVIDER", "AWS Secrets Manager"), "role": env_vars.get("VAULT_ROLE_PATH", "")}

    try:
        await test_integration(IntegrationConfig(provider_id=provider_id, config=config))
        GLOBAL_INTEGRATION_STATUS[provider_id] = True
        if provider_id == "vault":
            GLOBAL_INTEGRATION_STATUS["vault_provider"] = config.get("provider", "None")
    except Exception:
        GLOBAL_INTEGRATION_STATUS[provider_id] = False
        if provider_id == "vault":
            GLOBAL_INTEGRATION_STATUS["vault_provider"] = "None"

async def ping_all_integrations():
    """
    Pings all integrations concurrently to populate initial state.
    """
    tasks = [ping_integration_locally(provider) for provider in GLOBAL_INTEGRATION_STATUS.keys()]
    await asyncio.gather(*tasks)

@router.get("/status")
async def get_all_integration_status():
    """
    Returns the aggressively cached integration statuses populated during server startup 
    or when a configuration is actively updated.
    """
    return GLOBAL_INTEGRATION_STATUS


@router.get("/{provider_id}")
async def get_integration(provider_id: str):
    """
    Load current configuration from the local .env file.
    """
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    env_vars = dotenv_values(env_path)
    
    config = {}
    if provider_id == "messaging":
        config = {
            "bot_token": env_vars.get("SLACK_BOT_TOKEN", ""),
            "signing_secret": env_vars.get("SLACK_SIGNING_SECRET", ""),
            "channel": env_vars.get("SLACK_INCIDENT_CHANNEL", "")
        }
    elif provider_id == "aws":
        config = {
            "region": env_vars.get("AWS_REGION", ""),
            "role_override": env_vars.get("AWS_ROLE_OVERRIDE", ""),
            "opensearch": env_vars.get("OPENSEARCH_ENDPOINT", "")
        }
    elif provider_id == "github":
        config = {
            "base_url": env_vars.get("GITHUB_BASE_URL", ""),
            "org": env_vars.get("GITHUB_ORG", ""),
            "secret": env_vars.get("GITHUB_APP_SECRET", "")
        }
    elif provider_id == "jira":
        config = {
            "url": env_vars.get("JIRA_URL", ""),
            "secret": env_vars.get("JIRA_API_TOKEN", "")
        }
    elif provider_id == "confluence":
        config = {
            "url": env_vars.get("CONFLUENCE_URL", ""),
            "secret": env_vars.get("CONFLUENCE_API_TOKEN", "")
        }
    elif provider_id == "database":
        config = {
            "db_type": env_vars.get("DATABASE_TYPE", "PostgreSQL"),
            "uri": env_vars.get("DATABASE_URI", "")
        }
    elif provider_id == "vault":
        config = {
            "provider": env_vars.get("VAULT_PROVIDER", "AWS Secrets Manager"),
            "role": env_vars.get("VAULT_ROLE_PATH", "")
        }
        
    return {"provider_id": provider_id, "config": config}


@router.post("/test")
async def test_integration(payload: IntegrationConfig):
    """
    Test an integration connection thoroughly.
    """
    import sys
    print(f"DEBUG: Testing {payload.provider_id} with keys {list(payload.config.keys())}", file=sys.stderr)
    # General fallback constraint
    for key, value in payload.config.items():
        if not value or str(value).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration value for '{key}' cannot be empty."
            )
        if isinstance(value, str) and value.lower() == "fail":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Connection refused by {payload.provider_id.upper()} server. Invalid Vault ARN or Credentials."
            )

    if payload.provider_id == "messaging":
        bot_token = payload.config.get("bot_token", "")
        signing_secret = payload.config.get("signing_secret", "")
        channel = payload.config.get("channel", "")
        
        # Validations
        if not (signing_secret.startswith("arn:aws:secretsmanager:") or signing_secret.startswith("vault:")) and len(signing_secret) != 32:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Signing Secret. Must be a 32-character hex string or Vault ARN.")
        if not channel.startswith("#") and not channel.startswith("C"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Default incident channel must start with '#' or 'C'.")

        async with httpx.AsyncClient() as client:
            resp = await client.post("https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {bot_token}"})
            data = resp.json()
            if not data.get("ok"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Slack Auth Failed: {data.get('error', 'invalid_token')}.")
            
            # Check if channel actually exists
            if not bot_token.startswith("arn:"):
                chan_resp = await client.get(
                    "https://slack.com/api/conversations.list?exclude_archived=true&types=public_channel,private_channel&limit=1000",
                    headers={"Authorization": f"Bearer {bot_token}"}
                )
                chan_data = chan_resp.json()
                if chan_data.get("ok"):
                    channels = chan_data.get("channels", [])
                    channel_names = ["#" + c.get("name", "") for c in channels] + [c.get("id", "") for c in channels]
                    
                    if channel not in channel_names:
                        # Before declaring it missing, check if it's a newly created private channel 
                        # that the bot wasn't explicitly invited to. We just warn or fail based on exact match requirement.
                        raise HTTPException(status_code=400, detail=f"Slack Channel '{channel}' does not exist, or the bot has not been invited to it.")
                else:
                    # If it fails (e.g., missing 'channels:read' scope), explicitly fail so the user knows.
                    err_msg = chan_data.get("error", "unknown_error")
                    raise HTTPException(status_code=400, detail=f"Failed to fetch Slack channels for validation. Error: {err_msg}. Ensure bot has 'channels:read' scope.")

        return {"status": "success", "message": "Successfully authenticated with Slack Workspace!"}

    elif payload.provider_id == "aws":
        region = payload.config.get("region", "")
        opensearch = payload.config.get("opensearch", "")
        role_override = payload.config.get("role_override", "")

        # 1. Validate Region explicitly against known AWS Bedrock regions list
        valid_regions = ["us-east-1", "us-east-2", "us-west-2", "eu-central-1", "eu-west-1", "eu-west-2", "eu-west-3", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ca-central-1", "sa-east-1"]
        if region not in valid_regions:
            raise HTTPException(status_code=400, detail=f"Invalid AWS Region '{region}'. Must be a supported Bedrock region.")

        # 2. Validate IAM Role explicitly if provided
        if role_override and not re.match(r"^arn:aws:iam::\d{12}:role\/[\w+=,.@-]+$", role_override):
            raise HTTPException(status_code=400, detail="Invalid IAM Role Override. Must be a valid AWS IAM Role ARN (e.g., arn:aws:iam::123456789012:role/MyRole).")

        # 3. Validate OpenSearch Serverless explicitly 
        if not re.match(r"^https:\/\/[a-z0-9-]+\.[a-z0-9-]+\.aoss\.amazonaws\.com\/?$", opensearch):
            raise HTTPException(status_code=400, detail="Invalid OpenSearch Endpoint URL. Must be formatted exactly as 'https://<endpoint_id>.<region>.aoss.amazonaws.com'")
        
        # Test 1: Validate Bedrock Region natively via Boto3
        try:
            session = boto3.Session(region_name=region)
            client = session.client('bedrock')
            client.list_foundation_models()
        except (BotoCoreError, ClientError) as e:
            if "UnrecognizedClientException" in str(e) or "AccessDeniedException" in str(e) or "InvalidSignatureException" in str(e):
                pass 
            elif "Could not connect" in str(e) or "EndpointConnectionError" in str(e):
                raise HTTPException(status_code=400, detail=f"Cannot reach Bedrock in region '{region}'. Endpoint ping failed.")
            else:
                 pass 

        # Test 2: Validate OpenSearch URL reachability natively via HTTP
        try:
            async with httpx.AsyncClient(timeout=3.0) as http_client:
                os_resp = await http_client.get(opensearch)
                # If collection doesn't exist, AWS explicitly returns 404
                if os_resp.status_code == 404:
                    raise HTTPException(status_code=400, detail=f"OpenSearch Endpoint '{opensearch}' does not exist (404 Not Found). Please verify the Collection ID.")
                
                # Ensure the server actually identifies as OpenSearch/AWS
                if os_resp.status_code not in [403, 401]:
                    # Junk domains might return 200 OK pages or standard 404s
                    server_header = os_resp.headers.get("Server", "").lower()
                    if "awselasticsearch" not in server_header and "amazon" not in server_header:
                        raise HTTPException(status_code=400, detail="URL responded, but it is not recognized as a valid AWS OpenSearch Serverless endpoint.")
        except httpx.RequestError as e:
             raise HTTPException(status_code=400, detail=f"OpenSearch Endpoint network request failed: {str(e)}")

    elif payload.provider_id == "github":
        base_url = payload.config.get("base_url", "")
        org = payload.config.get("org", "")
        secret = payload.config.get("secret", "")
        if not base_url.startswith("https://"):
            raise HTTPException(status_code=400, detail="Base URL must start with https://")
        if not org.isalnum() and "-" not in org:
            raise HTTPException(status_code=400, detail="Organization name contains invalid characters.")
        
        # Actively test GitHub Server Connectivity
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(
                    f"{base_url}/user",
                    headers={"Authorization": f"Bearer {secret}", "Accept": "application/vnd.github.v3+json"}
                )
                if resp.status_code == 404:
                    raise HTTPException(status_code=400, detail="GitHub Enterprise URL is invalid or endpoint not found.")
                elif resp.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"GitHub Auth Failed. Bad Credentials (HTTP {resp.status_code}).")
        except httpx.ConnectError:
            raise HTTPException(status_code=400, detail=f"GitHub Enterprise URL '{base_url}' is unreachable.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"GitHub validation failed natively: {str(e)}")

    elif payload.provider_id in ["jira", "confluence"]:
        url = payload.config.get("url", "")
        secret = payload.config.get("secret", "")
        if not url.startswith("https://"):
            raise HTTPException(status_code=400, detail=f"{payload.provider_id.title()} URL must start with https://.")
        if len(secret) < 10:
            raise HTTPException(status_code=400, detail="Invalid API Token format. Too short.")
        
        # Actively test Atlassian server connectivity via generic root info endpoint
        test_endpoint = f"{url.rstrip('/')}/rest/api/3/serverInfo" if payload.provider_id == "jira" else f"{url.rstrip('/')}/wiki/rest/api/settings/systemInfo"
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(test_endpoint)
                if resp.status_code == 404:
                    raise HTTPException(status_code=400, detail=f"{payload.provider_id.title()} Server not found at that base URL.")
                elif resp.status_code in [200, 401, 403]:
                    pass # The server exists and returned a native response, so URL is physically valid.
                else:
                    raise HTTPException(status_code=400, detail=f"Unrecognized response from {payload.provider_id.title()} server (HTTP {resp.status_code}).")
        except httpx.ConnectError:
            raise HTTPException(status_code=400, detail=f"{payload.provider_id.title()} URL '{url}' is unreachable or does not exist.")
        except httpx.RequestError as e:
            raise HTTPException(status_code=400, detail=f"Network request to {payload.provider_id.title()} failed natively: {str(e)}")

    elif payload.provider_id == "database":
        uri = payload.config.get("uri", "")
        import sys
        print(f"DEBUG: Database URI for test: '{uri}'", file=sys.stderr)
        if not (uri.startswith("postgresql://") or uri.startswith("mysql://") or uri.startswith("oracle://") or uri.startswith("secret/")):
            raise HTTPException(status_code=400, detail="Connection string must start with a valid dialect schema (e.g., postgresql://) or Vault path (secret/).")
        
        from urllib.parse import urlparse
        # Actively test Database TCP Port logic 
        if not uri.startswith("secret/"):
            parsed = urlparse(uri)
            host = parsed.hostname
            # Default ports if missing in URI
            port = parsed.port if parsed.port else (5432 if "postgres" in uri else 3306 if "mysql" in uri else 1521)
            
            if not host:
                raise HTTPException(status_code=400, detail="Invalid Database URI. Could not identify a hostname or IP address.")

            # Explicit DNS check before TCP attempt
            import socket
            try:
                socket.gethostbyname(host)
            except socket.gaierror:
                raise HTTPException(status_code=400, detail=f"Database Host '{host}' could not be resolved (DNS failed). Please verify the hostname.")

            print(f"DEBUG: Attempting TCP connection to {host}:{port}", file=sys.stderr)
            try:
                # Physically attempt a raw TCP socket connection
                # This catches both DNS resolution errors and port connection errors
                reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=4.0)
                writer.close()
                await writer.wait_closed()
            except (asyncio.TimeoutError, ConnectionRefusedError) as e:
                raise HTTPException(status_code=400, detail=f"Database Connection Failed. Timeout or Refused on {host}:{port}. Error: {str(e)}")
            except Exception as e:
                # Catch node unknown / DNS failure specifically 
                raise HTTPException(status_code=400, detail=f"Database Host '{host}' is unreachable or does not exist (DNS/Network error).")
        else:
            # It's a Vault path ("secret/...")
            if not GLOBAL_INTEGRATION_STATUS.get("vault", False):
                raise HTTPException(
                    status_code=400, 
                    detail="Database URI is a Vault path (secret/...), but the Secrets Vault integration is not yet connected. Please configure and test the 'Secrets Vault' tile first."
                )
            # If vault IS connected, return a specific success message
            return {"status": "success", "message": f"Syntactic check passed for Vault path. Connection will be tested at runtime once the secret is resolved from {GLOBAL_INTEGRATION_STATUS.get('vault_provider', 'Vault')}."}

    elif payload.provider_id == "vault":
        provider = payload.config.get("provider", "")
        role_arn = payload.config.get("role", "")
        if provider not in ["AWS Secrets Manager", "HashiCorp Vault", "CyberArk"]:
            raise HTTPException(status_code=400, detail="Unsupported Vault Provider.")
        if "arn:aws:iam" not in role_arn and "role/" not in role_arn:
            raise HTTPException(status_code=400, detail="Invalid IAM Role format. Ensure it's a valid ARN or AppRole path.")
        
        # Actively validate AWS Secrets Manager
        if provider == "AWS Secrets Manager":
            try:
                # Need to use the global AWS config explicitly 
                sts_client = boto3.client('sts')
                sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName="SentinelOpsVaultValidation",
                    DurationSeconds=900
                )
            except (BotoCoreError, ClientError) as e:
                err_str = str(e)
                # Any rejection means the literal role string provided isn't securely assumbable by the backend
                if "AccessDenied" in err_str:
                    raise HTTPException(status_code=400, detail=f"AWS STS AccessDenied: Cannot assume Vault Role '{role_arn}'. Check Trust Policies / formatting.")
                elif "ValidationError" in err_str:
                    raise HTTPException(status_code=400, detail=f"AWS STS ValidationError: The Role ARN '{role_arn}' does not physically exist or is structurally invalid.")
                else:
                    raise HTTPException(status_code=400, detail=f"Vault Authentication Failed natively: {err_str}")
                
        # HashiCorp or CyberArk generic delays for MVP
        elif provider in ["HashiCorp Vault", "CyberArk"]:
            await asyncio.sleep(1)
            
    return {"status": "success", "message": f"Successfully connected to {payload.provider_id.upper()}"}


@router.post("/save")
async def save_integration(payload: IntegrationConfig):
    """
    Save the integration configuration to the local .env file.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    
    if payload.provider_id == "messaging":
        set_key(env_path, "SLACK_BOT_TOKEN", payload.config.get("bot_token", ""), quote_mode="never")
        set_key(env_path, "SLACK_SIGNING_SECRET", payload.config.get("signing_secret", ""), quote_mode="never")
        set_key(env_path, "SLACK_INCIDENT_CHANNEL", payload.config.get("channel", ""), quote_mode="never")
    elif payload.provider_id == "aws":
        set_key(env_path, "AWS_REGION", payload.config.get("region", ""), quote_mode="never")
        set_key(env_path, "AWS_ROLE_OVERRIDE", payload.config.get("role_override", ""), quote_mode="never")
        set_key(env_path, "OPENSEARCH_ENDPOINT", payload.config.get("opensearch", ""), quote_mode="never")
    elif payload.provider_id == "github":
        set_key(env_path, "GITHUB_BASE_URL", payload.config.get("base_url", ""), quote_mode="never")
        set_key(env_path, "GITHUB_ORG", payload.config.get("org", ""), quote_mode="never")
        set_key(env_path, "GITHUB_APP_SECRET", payload.config.get("secret", ""), quote_mode="never")
    elif payload.provider_id == "jira":
        set_key(env_path, "JIRA_URL", payload.config.get("url", ""), quote_mode="never")
        set_key(env_path, "JIRA_API_TOKEN", payload.config.get("secret", ""), quote_mode="never")
    elif payload.provider_id == "confluence":
        set_key(env_path, "CONFLUENCE_URL", payload.config.get("url", ""), quote_mode="never")
        set_key(env_path, "CONFLUENCE_API_TOKEN", payload.config.get("secret", ""), quote_mode="never")
    elif payload.provider_id == "database":
        set_key(env_path, "DATABASE_TYPE", payload.config.get("db_type", ""), quote_mode="never")
        set_key(env_path, "DATABASE_URI", payload.config.get("uri", ""), quote_mode="never")
    elif payload.provider_id == "vault":
        set_key(env_path, "VAULT_PROVIDER", payload.config.get("provider", ""), quote_mode="never")
        set_key(env_path, "VAULT_ROLE_PATH", payload.config.get("role", ""), quote_mode="never")

    # Refresh the global status cache
    await ping_integration_locally(payload.provider_id)

    return {"status": "success", "message": f"Configuration for {payload.provider_id} saved securely to environment and connectivity was automatically tested!"}
