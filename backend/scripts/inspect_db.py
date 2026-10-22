import asyncio
from sqlalchemy import text
from app.db.session import engine

async def inspect_schema():
    async with engine.connect() as conn:
        # Check alembic revision
        rev = await conn.execute(text("SELECT version_num FROM alembic_version"))
        print("Current Alembic Revision:", rev.scalar())
        
        # Check tables
        tables = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        ))
        print("Tables:", [r[0] for r in tables.fetchall()])
        
        # Check users columns
        users_cols = await conn.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position"
        ))
        print("Users columns:")
        for r in users_cols.fetchall():
            print(f"  - {r[0]}: {r[1]} (nullable: {r[2]})")
        
        # Check companies constraints
        companies_fks = await conn.execute(text("""
            SELECT tc.constraint_name, tc.constraint_type, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'companies'
        """))
        print("Companies constraints:")
        for r in companies_fks.fetchall():
            print(f"  - {r[0]} ({r[1]}): {r[2]} -> {r[3]}.{r[4]}")
            
        # Check documents constraints
        docs_fks = await conn.execute(text("""
            SELECT tc.constraint_name, tc.constraint_type, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'documents'
        """))
        print("Documents constraints:")
        for r in docs_fks.fetchall():
            print(f"  - {r[0]} ({r[1]}): {r[2]} -> {r[3]}.{r[4]}")
            
        # Check indexes
        indexes = await conn.execute(text("""
            SELECT tablename, indexname, indexdef 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            ORDER BY tablename, indexname
        """))
        print("Indexes:")
        for r in indexes.fetchall():
            print(f"  - {r[0]} :: {r[1]}")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
