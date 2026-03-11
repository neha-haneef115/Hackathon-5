#!/usr/bin/env python3
"""
Complete standalone API runner without Kafka dependencies for testing
"""

import asyncio
import uvicorn
import os
import sys
import json

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

# Mock all Kafka-related functions
def mock_publish_event(*args, **kwargs):
    pass

def mock_get_consumer(*args, **kwargs):
    return None

# Mock the kafka_client module completely
import production.kafka_client
production.kafka_client.get_producer = mock_get_producer
production.kafka_client.publish_event = mock_publish_event
production.kafka_client.get_consumer = mock_get_consumer

# Mock the web_form_handler Kafka calls
import production.channels.web_form_handler
production.channels.web_form_handler.publish_event = mock_publish_event

# Import the FastAPI app
from production.api.main import app

async def main():
    """Run FastAPI application without Kafka dependencies"""
    print("🚀 Starting TechCorp FTE API (Complete Standalone Mode)...")
    print(f"📊 Database: {os.getenv('POSTGRES_HOST', 'localhost')}")
    print(f"🤖 AI: Google Gemini configured")
    print("🌐 API will be available at: http://localhost:8000")
    print("📝 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("✅ Running without Kafka dependencies for testing")
    print("📝 Support Form: http://localhost:8000/support/submit")
    
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
