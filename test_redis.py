import os
import asyncio
from dotenv import load_dotenv
import redis.asyncio as redis

# Carrega o .env manualmente
load_dotenv()

async def main():
    url = os.environ.get("REDIS_URL")

    if not url:
        print("REDIS_URL não definido")
        return

    r = redis.from_url(url)

    await r.set("chat_test_key", "ok")
    value = await r.get("chat_test_key")

    print("Redis respondeu:", value)

    await r.delete("chat_test_key")
    await r.close()
    await r.connection_pool.disconnect()

if __name__ == "__main__":
    asyncio.run(main())