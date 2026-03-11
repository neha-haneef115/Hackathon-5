#!/usr/bin/env python3
"""
Standalone API runner without Kafka dependencies for testing
"""

import asyncio
import uvicorn
import os
import sys

# Add production directory to Python path
sys.path.insert(0, '.')

# Mock Kafka functions to avoid connection issues
class MockKafkaProducer:
    async def start(self):
        pass
    async def stop(self):
        pass
    async def send_and_wait(self, *args, **kwargs):
        pass

async def mock_get_producer():
    return MockKafkaProducer()

# Mock the kafka_client module
import production.api.main
production.api.main.get_producer = mock_get_producer

# Import the FastAPI app
from production.api.main import app

async def main():
    """Run FastAPI application without Kafka dependencies"""
    print("🚀 Starting TechCorp FTE API (Standalone Mode)...")
    print(f"📊 Database: {os.getenv('POSTGRES_HOST', 'localhost')}")
    print(f"🤖 AI: Google Gemini configured")
    print("🌐 API will be available at: http://localhost:8000")
    print("📝 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("✅ Running without Kafka dependencies for testing")
    
    # Run FastAPI app
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
    
    await uvicorn.Server(config).serve()

if __name__ == "__main__":
    asyncio.run(main())
