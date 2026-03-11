#!/usr/bin/env python3
"""
Simple database setup script for TechCorp FTE
"""

import asyncio
import asyncpg
import os
import sys

# Add production directory to Python path
sys.path.insert(0, '.')

async def setup_database():
    """Create database tables"""
    try:
        # Connect to Neon PostgreSQL
        conn = await asyncpg.connect(
            host=os.getenv('POSTGRES_HOST', 'ep-delicate-mouse-a41l0gny.us-east-1.aws.neon.tech'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'neondb'),
            user=os.getenv('POSTGRES_USER', 'neondb_owner'),
            password=os.getenv('POSTGRES_PASSWORD', 'npg_rqVKZS9j4Ivk')
        )
        
        print("✅ Connected to Neon PostgreSQL")
        
        # Read and execute schema
        with open('production/database/schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # Split into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                try:
                    await conn.execute(statement)
                    print(f"✅ Executed: {statement[:50]}...")
                except Exception as e:
                    if "already exists" not in str(e):
                        print(f"⚠️ Error: {e}")
        
        print("✅ Database setup completed")
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(setup_database())
