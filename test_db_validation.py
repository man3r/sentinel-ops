import asyncio
import socket
from urllib.parse import urlparse

async def test_db_logic(uri):
    print(f"Testing URI: {uri}")
    parsed = urlparse(uri)
    host = parsed.hostname
    port = parsed.port if parsed.port else (5432 if "postgres" in uri or "postgresql" in uri else 3306 if "mysql" in uri else 1521)
    
    print(f"Host: {host}, Port: {port}")
    if not host:
        print("Failure: No host in URI")
        return

    try:
        # Physically attempt a raw TCP socket connection
        # Important: asyncio.open_connection will try to resolve DNS
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
        writer.close()
        await writer.wait_closed()
        print("Success: Connection opened")
    except asyncio.TimeoutError:
        print(f"Failure: Connection Timeout for {host}:{port}")
    except socket.gaierror as e:
        print(f"Failure: DNS resolution failed for {host}: {e}")
    except Exception as e:
        print(f"Failure: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_db_logic("postgresql://junk.db.com:5432"))
    asyncio.run(test_db_logic("postgresql://localhost:5432")) # Assuming nothing is there
    asyncio.run(test_db_logic("junk-bad-string"))
