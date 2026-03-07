"""
TechCorp FTE Database Connection Manager
AsyncPG connection pool management for PostgreSQL
"""

import os
import asyncio
from typing import Optional
import asyncpg
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseManager:
    """Manages AsyncPG connection pool for the TechCorp FTE database"""
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'fte_db'),
            'user': os.getenv('POSTGRES_USER', 'fte_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'changeme123'),
            'min_size': 5,
            'max_size': 20,
            'timeout': 30,
            'command_timeout': 60
        }
    
    async def init_db_pool(self) -> asyncpg.Pool:
        """
        Initialize the database connection pool
        
        Returns:
            asyncpg.Pool: The created connection pool
            
        Raises:
            asyncpg.PostgresError: If connection fails
        """
        if self._pool is not None:
            return self._pool
        
        try:
            # Create connection pool with configuration
            self._pool = await asyncpg.create_pool(
                host=self._config['host'],
                port=self._config['port'],
                database=self._config['database'],
                user=self._config['user'],
                password=self._config['password'],
                min_size=self._config['min_size'],
                max_size=self._config['max_size'],
                timeout=self._config['timeout'],
                command_timeout=self._config['command_timeout']
            )
            
            print(f"✅ Database connection pool initialized: {self._config['host']}:{self._config['port']}/{self._config['database']}")
            return self._pool
            
        except asyncpg.PostgresError as e:
            print(f"❌ Failed to initialize database pool: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error initializing database pool: {e}")
            raise
    
    async def get_db_pool(self) -> asyncpg.Pool:
        """
        Get existing database pool or create new one
        
        Returns:
            asyncpg.Pool: Database connection pool
        """
        if self._pool is None:
            await self.init_db_pool()
        return self._pool
    
    async def close_db_pool(self) -> None:
        """Close the database connection pool"""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            print("🔒 Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Async context manager for getting a database connection
        
        Yields:
            asyncpg.Connection: Database connection
        """
        pool = await self.get_db_pool()
        connection = None
        
        try:
            connection = await pool.acquire()
            yield connection
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise
        finally:
            if connection is not None:
                await pool.release(connection)
    
    async def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            bool: True if connection is successful
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    async def get_pool_info(self) -> dict:
        """
        Get connection pool information
        
        Returns:
            dict: Pool statistics and configuration
        """
        pool = await self.get_db_pool()
        
        return {
            'config': self._config,
            'size': pool.get_size(),
            'idle': pool.get_idle_size(),
            'max_size': pool.get_max_size(),
            'min_size': pool.get_min_size()
        }
    
    async def execute_query(self, query: str, *args) -> str:
        """
        Execute a simple query and return result
        
        Args:
            query: SQL query to execute
            *args: Query parameters
            
        Returns:
            str: Query result
        """
        async with self.get_connection() as conn:
            if query.strip().upper().startswith('SELECT'):
                result = await conn.fetchval(query, *args)
                return str(result)
            else:
                result = await conn.execute(query, *args)
                return result
    
    async def health_check(self) -> dict:
        """
        Perform comprehensive database health check
        
        Returns:
            dict: Health check results
        """
        health_status = {
            'database_connected': False,
            'pool_info': None,
            'table_count': 0,
            'extensions': [],
            'error': None
        }
        
        try:
            # Test basic connection
            health_status['database_connected'] = await self.test_connection()
            
            if health_status['database_connected']:
                # Get pool info
                health_status['pool_info'] = await self.get_pool_info()
                
                # Count tables
                async with self.get_connection() as conn:
                    tables = await conn.fetch(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                    health_status['table_count'] = tables[0]['count']
                    
                    # Check extensions
                    extensions = await conn.fetch(
                        "SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector', 'pg_trgm')"
                    )
                    health_status['extensions'] = [ext['extname'] for ext in extensions]
            
        except Exception as e:
            health_status['error'] = str(e)
        
        return health_status

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
async def init_db_pool() -> asyncpg.Pool:
    """Initialize database connection pool"""
    return await db_manager.init_db_pool()

async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    return await db_manager.get_db_pool()

async def close_db_pool() -> None:
    """Close database connection pool"""
    await db_manager.close_db_pool()

@asynccontextmanager
async def get_connection():
    """Get database connection context manager"""
    async with db_manager.get_connection() as conn:
        yield conn

# Example usage and testing
if __name__ == "__main__":
    async def test_database():
        """Test database connection and basic operations"""
        try:
            # Initialize pool
            pool = await init_db_pool()
            print("✅ Database pool initialized successfully")
            
            # Test connection
            async with get_connection() as conn:
                result = await conn.fetchval("SELECT version()")
                print(f"📊 PostgreSQL version: {result[:50]}...")
            
            # Health check
            health = await db_manager.health_check()
            print("🏥 Health Check Results:")
            for key, value in health.items():
                print(f"   {key}: {value}")
            
            # Pool info
            pool_info = await db_manager.get_pool_info()
            print("🔗 Pool Info:")
            for key, value in pool_info.items():
                print(f"   {key}: {value}")
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
        finally:
            await close_db_pool()
            print("🔒 Database pool closed")
    
    # Run test
    asyncio.run(test_database())
