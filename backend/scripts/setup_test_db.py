import asyncio
import asyncpg
from app.core.config import get_settings

async def ensure_test_database():
    settings = get_settings()
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'tender_platform_test'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE tender_platform_test OWNER tender_app;")
            print("Successfully created isolated test database: tender_platform_test")
        else:
            print("Isolated test database already exists: tender_platform_test")
    except Exception as e:
        print(f"Error checking/creating test database: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(ensure_test_database())
