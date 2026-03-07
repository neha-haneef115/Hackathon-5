"""
TechCorp Customer Success FTE API
Main FastAPI application with all endpoints
"""

import os
import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import google.generativeai as genai

from ..database.connection import init_db_pool, close_db_pool, get_connection
from ..kafka_client import get_producer, publish_event, TOPICS
from ..database import queries
from ..channels.gmail_handler import get_gmail_handler
from ..channels.whatsapp_handler import get_whatsapp_handler
from .web_form_handler import router as web_form_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Global variables
kafka_producer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global kafka_producer
    
    # Startup
    logger.info("🚀 Starting TechCorp FTE API...")
    
    try:
        # Initialize database pool
        await init_db_pool()
        logger.info("✅ Database pool initialized")
        
        # Initialize Kafka producer
        kafka_producer = await get_producer()
        logger.info("✅ Kafka producer initialized")
        
        # Test connections
        db_status = await test_database_connection()
        kafka_status = await test_kafka_connection()
        
        logger.info(f"📊 Startup health - DB: {db_status}, Kafka: {kafka_status}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down TechCorp FTE API...")
    
    try:
        await close_db_pool()
        if kafka_producer:
            await kafka_producer.stop()
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

# Create FastAPI app
app = FastAPI(
    title="TechCorp Customer Success FTE API",
    description="AI-powered customer support automation for TechCorp",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(web_form_router)

# Utility functions
async def test_database_connection() -> str:
    """Test database connection"""
    try:
        async with get_connection() as conn:
            await conn.fetchval("SELECT 1")
        return "connected"
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return "error"

async def test_kafka_connection() -> str:
    """Test Kafka connection"""
    try:
        if kafka_producer:
            health = await kafka_producer.health_check()
            return "connected" if health['started'] else "error"
        return "error"
    except Exception as e:
        logger.error(f"❌ Kafka connection failed: {e}")
        return "error"

# Health and readiness endpoints
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check
    
    Returns:
        Dict: Health status of all services
    """
    try:
        # Test database
        db_status = await test_database_connection()
        
        # Test Kafka
        kafka_status = await test_kafka_connection()
        
        # Test channel handlers
        gmail_handler = get_gmail_handler()
        whatsapp_handler = get_whatsapp_handler()
        
        gmail_active = await gmail_handler.test_connection()
        whatsapp_active = await whatsapp_handler.test_connection()
        
        overall_status = "healthy"
        if db_status == "error" or kafka_status == "error":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": db_status,
                "kafka": kafka_status
            },
            "channels": {
                "email": "active" if gmail_active else "error",
                "whatsapp": "active" if whatsapp_active else "error",
                "web_form": "active"  # Always active (part of API)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }

@app.get("/ready")
async def readiness_check() -> Response:
    """
    Readiness check for Kubernetes
    
    Returns:
        Response: 200 if ready, 503 if not ready
    """
    try:
        db_status = await test_database_connection()
        kafka_status = await test_kafka_connection()
        
        if db_status == "connected" and kafka_status == "connected":
            return Response(
                content=json.dumps({"status": "ready"}),
                status_code=200,
                media_type="application/json"
            )
        else:
            return Response(
                content=json.dumps({
                    "status": "not_ready",
                    "database": db_status,
                    "kafka": kafka_status
                }),
                status_code=503,
                media_type="application/json"
            )
            
    except Exception as e:
        logger.error(f"❌ Readiness check failed: {e}")
        return Response(
            content=json.dumps({"status": "error", "error": str(e)}),
            status_code=503,
            media_type="application/json"
        )

# Webhook endpoints
@app.post("/webhooks/gmail")
async def gmail_webhook(request: Request) -> Dict[str, Any]:
    """
    Gmail Pub/Sub webhook handler
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict: Processing result
    """
    try:
        # Parse webhook payload
        body = await request.json()
        
        # Extract base64 data
        message_data = body.get("message", {}).get("data", "")
        if not message_data:
            logger.warning("⚠️ No message data in Gmail webhook")
            return {"status": "no_data"}
        
        # Decode base64 data
        decoded_data = base64.b64decode(message_data).decode('utf-8')
        pubsub_message = json.loads(decoded_data)
        
        logger.info(f"📧 Received Gmail webhook: {pubsub_message.get('messageId', 'unknown')}")
        
        # Poll Gmail inbox
        gmail_handler = get_gmail_handler()
        messages = await gmail_handler.poll_inbox()
        
        # Publish messages to Kafka
        processed_count = 0
        for msg in messages:
            try:
                await publish_event(
                    topic=TOPICS["tickets_incoming"],
                    event=msg,
                    key=msg.get("channel_message_id")
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"❌ Error publishing Gmail message: {e}")
        
        logger.info(f"✅ Processed {processed_count} Gmail messages")
        
        return {
            "status": "processed",
            "count": processed_count
        }
        
    except Exception as e:
        logger.error(f"❌ Gmail webhook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process Gmail webhook")

@app.get("/webhooks/whatsapp")
@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    """
    WhatsApp webhook handler (GET for verification, POST for messages)
    
    Args:
        request: FastAPI request object
        
    Returns:
        Response: Verification challenge or processing result
    """
    try:
        if request.method == "GET":
            # Webhook verification
            mode = request.query_params.get("hub.mode")
            token = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")
            
            whatsapp_handler = get_whatsapp_handler()
            result = whatsapp_handler.verify_webhook(mode, token, challenge)
            
            if result:
                logger.info("✅ WhatsApp webhook verified")
                return PlainTextResponse(content=result)
            else:
                logger.warning("⚠️ WhatsApp webhook verification failed")
                raise HTTPException(status_code=403, detail="Verification failed")
        
        elif request.method == "POST":
            # Incoming messages
            body = await request.json()
            
            logger.info("📱 Received WhatsApp webhook")
            
            whatsapp_handler = get_whatsapp_handler()
            messages = whatsapp_handler.process_webhook(body)
            
            # Publish messages to Kafka
            for msg in messages:
                try:
                    await publish_event(
                        topic=TOPICS["tickets_incoming"],
                        event=msg,
                        key=msg.get("channel_message_id")
                    )
                except Exception as e:
                    logger.error(f"❌ Error publishing WhatsApp message: {e}")
            
            logger.info(f"✅ Processed {len(messages)} WhatsApp messages")
            
            return Response(
                content=json.dumps({"status": "received"}),
                status_code=200,
                media_type="application/json"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ WhatsApp webhook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process WhatsApp webhook")

# Conversation and customer endpoints
@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Get conversation details and messages
    
    Args:
        conversation_id: Conversation UUID
        
    Returns:
        Dict: Conversation details and messages
    """
    try:
        # Get conversation messages
        messages = await queries.get_conversation_messages(conversation_id)
        
        if not messages:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get conversation details from first message
        first_msg = messages[0]
        
        return {
            "conversation_id": conversation_id,
            "customer_id": first_msg.get("customer_id"),
            "channel": first_msg.get("channel"),
            "status": "active",  # TODO: Get from conversations table
            "messages": messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")

@app.get("/customers/lookup")
async def lookup_customer(
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Lookup customer by email or phone
    
    Args:
        email: Customer email
        phone: Customer phone
        
    Returns:
        Dict: Customer information and recent conversations
    """
    try:
        if not email and not phone:
            raise HTTPException(status_code=400, detail="Either email or phone must be provided")
        
        customer = None
        if email:
            customer = await queries.get_customer_by_identifier("email", email)
        elif phone:
            customer = await queries.get_customer_by_identifier("phone", phone)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get recent conversations
        recent_conversations = await queries.get_customer_all_channels_history(
            customer_id=customer["id"],
            limit=10
        )
        
        # Group by conversation
        conversations = {}
        for msg in recent_conversations:
            conv_id = msg["conversation_id"]
            if conv_id not in conversations:
                conversations[conv_id] = {
                    "conversation_id": conv_id,
                    "channel": msg.get("conversation_channel"),
                    "last_message": msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"],
                    "last_message_at": msg["created_at"],
                    "message_count": 0
                }
            conversations[conv_id]["message_count"] += 1
        
        return {
            "customer": customer,
            "recent_conversations": list(conversations.values())[:5]  # Return last 5 conversations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error looking up customer: {e}")
        raise HTTPException(status_code=500, detail="Failed to lookup customer")

# Metrics endpoints
@app.get("/metrics/channels")
async def get_channel_metrics(hours: int = Query(24, ge=1, le=168)) -> Dict[str, Any]:
    """
    Get channel performance metrics
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        Dict: Channel metrics breakdown
    """
    try:
        metrics = await queries.get_channel_metrics(hours)
        
        return {
            "timeframe_hours": hours,
            "metrics": metrics,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting channel metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve channel metrics")

@app.get("/metrics/daily/{date}")
async def get_daily_metrics(date: str) -> Dict[str, Any]:
    """
    Get daily metrics for specific date
    
    Args:
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dict: Daily metrics
    """
    try:
        # Parse date
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Try to get from daily_reports table
        async with get_connection() as conn:
            report = await conn.fetchrow(
                "SELECT * FROM daily_reports WHERE report_date = $1",
                target_date
            )
        
        if report:
            return {
                "date": date,
                "metrics": dict(report),
                "source": "cached"
            }
        else:
            # Generate on-demand
            metrics = await queries.get_daily_metrics(target_date)
            return {
                "date": date,
                "metrics": metrics,
                "source": "generated"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting daily metrics for {date}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve daily metrics")

# Admin endpoints
@app.get("/admin/overview")
async def get_admin_overview() -> Dict[str, Any]:
    """
    Get administrative overview
    
    Returns:
        Dict: System overview statistics
    """
    try:
        # Get total customers
        async with get_connection() as conn:
            total_customers = await conn.fetchval("SELECT COUNT(*) FROM customers")
            
            # Get today's tickets
            today = datetime.now(timezone.utc).date()
            total_tickets_today = await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE DATE(created_at) = $1",
                today
            )
            
            # Get tickets by status
            tickets_by_status = await conn.fetch(
                """
                SELECT status, COUNT(*) as count
                FROM tickets
                WHERE DATE(created_at) = $1
                GROUP BY status
                """,
                today
            )
            
            # Get escalation rate
            escalated_today = await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE DATE(created_at) = $1 AND status = 'escalated'",
                today
            )
            escalation_rate = (escalated_today / total_tickets_today * 100) if total_tickets_today > 0 else 0
            
            # Get average response time
            avg_response_time = await conn.fetchval(
                """
                SELECT AVG(latency_ms)
                FROM messages m
                JOIN tickets t ON m.conversation_id = t.conversation_id
                WHERE DATE(t.created_at) = $1 AND m.role = 'agent' AND m.latency_ms IS NOT NULL
                """,
                today
            )
        
        return {
            "overview_date": today.isoformat(),
            "total_customers": total_customers,
            "total_tickets_today": total_tickets_today,
            "tickets_by_status": {row["status"]: row["count"] for row in tickets_by_status},
            "escalation_rate": round(escalation_rate, 2),
            "avg_response_time_ms": int(avg_response_time) if avg_response_time else 0,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting admin overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve admin overview")

@app.post("/admin/seed-knowledge-base")
async def seed_knowledge_base() -> Dict[str, Any]:
    """
    Seed knowledge base from product documentation
    
    Returns:
        Dict: Seeding result
    """
    try:
        # Read product documentation
        try:
            with open("context/product-docs.md", "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Product documentation file not found")
        
        # Split by sections
        sections = content.split("## ")
        entries_created = 0
        
        for section in sections[1:]:  # Skip first empty split
            if not section.strip():
                continue
            
            # Extract title and content
            lines = section.split("\n", 1)
            if len(lines) < 2:
                continue
            
            title = lines[0].strip()
            content_body = lines[1].strip()
            
            if not title or not content_body:
                continue
            
            # Generate embedding
            try:
                embedding_response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=content_body,
                    task_type="retrieval_document"
                )
                embedding = embedding_response["embedding"]
            except Exception as e:
                logger.error(f"❌ Error generating embedding for {title}: {e}")
                continue
            
            # Insert into knowledge base
            try:
                await queries.insert_knowledge_entry(
                    title=title,
                    content=content_body,
                    category="documentation",
                    embedding=embedding
                )
                entries_created += 1
            except Exception as e:
                logger.error(f"❌ Error inserting knowledge entry {title}: {e}")
                continue
        
        logger.info(f"✅ Seeded {entries_created} knowledge base entries")
        
        return {
            "status": "seeded",
            "entries_created": entries_created,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error seeding knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to seed knowledge base")

# Additional utility endpoints
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {
        "service": "TechCorp Customer Success FTE API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/version")
async def get_version() -> Dict[str, str]:
    """Get API version"""
    return {
        "version": "2.0.0",
        "name": "TechCorp Customer Success FTE API",
        "build_date": "2024-03-07"
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return Response(
        content=json.dumps({"error": "Endpoint not found", "path": request.url.path}),
        status_code=404,
        media_type="application/json"
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors"""
    logger.error(f"❌ Internal server error: {exc}")
    return Response(
        content=json.dumps({"error": "Internal server error"}),
        status_code=500,
        media_type="application/json"
    )

if __name__ == "__main__":
    import uvicorn
    
    # Run the app
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
