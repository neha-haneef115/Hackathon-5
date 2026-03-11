#!/usr/bin/env python3
"""
Simple API runner without Kafka dependency for testing
"""

import asyncio
import uvicorn
import os
from production.api.main import app

async def main():
    """Run the FastAPI application without Kafka dependencies"""
    print("🚀 Starting TechCorp FTE API (Simple Mode)...")
    print(f"📊 Database: {os.getenv('POSTGRES_HOST', 'localhost')}")
    print(f"🤖 AI: Google Gemini configured")
    print("🌐 API will be available at: http://localhost:8000")
    print("📝 API Documentation: http://localhost:8000/docs")
    
    # Run the FastAPI app
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
