import asyncio
from urllib.parse import urlparse

async def test_db():
    uri = "postgresql://junk.db.com:5432"
    parsed = urlparse(uri)
    host = parsed.hostname
    port = parsed.port if parsed.port else (5432 if "postgres" in uri else 3306 if "mysql" in uri else 1521)
    print(f"Host: {host}, Port: {port}")
    if host:
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2.0)
            writer.close()
            await writer.wait_closed()
            print("Success")
        except asyncio.TimeoutError:
            print("Timeout")
        except Exception as e:
            print(f"Exception: {str(e)}")

asyncio.run(test_db())
