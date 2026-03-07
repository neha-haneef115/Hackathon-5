"""
TechCorp FTE Message Processor
Unified message processing worker for all channels
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from ..database.connection import init_db_pool, close_db_pool
from ..database import queries
from ..kafka_client import get_producer, get_consumer, publish_event, TOPICS
from ..agent.customer_success_agent import run_agent
from ..channels.gmail_handler import get_gmail_handler
from ..channels.whatsapp_handler import get_whatsapp_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedMessageProcessor:
    """Unified message processor for all customer support channels"""
    
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.running = False
    
    async def start(self):
        """Start the message processor"""
        try:
            logger.info("🚀 Starting Unified Message Processor...")
            
            # Initialize database pool
            await init_db_pool()
            logger.info("✅ Database pool initialized")
            
            # Start Kafka producer
            self.producer = await get_producer()
            logger.info("✅ Kafka producer started")
            
            # Start Kafka consumer
            self.consumer = await get_consumer(
                topics=[TOPICS["tickets_incoming"]],
                group_id="fte-processor"
            )
            logger.info("✅ Kafka consumer started")
            
            self.running = True
            logger.info("📧 Message processor started, listening on fte.tickets.incoming")
            
            # Start consuming messages
            await self.consumer.consume(self.process_message)
            
        except Exception as e:
            logger.error(f"❌ Failed to start message processor: {e}")
            raise
    
    async def stop(self):
        """Stop the message processor"""
        logger.info("🛑 Stopping Unified Message Processor...")
        
        self.running = False
        
        if self.consumer:
            await self.consumer.stop()
        
        if self.producer:
            await self.producer.stop()
        
        await close_db_pool()
        
        logger.info("✅ Message processor stopped")
    
    async def process_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None):
        """
        Process incoming message from any channel
        
        Args:
            topic: Kafka topic
            message: Message data
            key: Message key
        """
        if not self.running:
            return
        
        try:
            # Extract channel information
            channel = message.get("channel", "unknown")
            logger.info(f"📨 Processing {channel} message: {key}")
            
            # Resolve customer
            customer_id = await self.resolve_customer(message)
            logger.debug(f"👤 Resolved customer: {customer_id}")
            
            # Get or create conversation
            conversation_id = await self.get_or_create_conversation(customer_id, channel)
            logger.debug(f"💬 Conversation: {conversation_id}")
            
            # Store inbound message
            await self.store_inbound_message(conversation_id, message)
            
            # Get conversation history
            history = await self.get_conversation_history(conversation_id)
            
            # Build context for agent
            context = self.build_context(message, customer_id, conversation_id, history)
            
            # Run agent
            result = await run_agent(message["content"], context)
            
            # Store outbound message
            await self.store_outbound_message(conversation_id, message, result)
            
            # Publish metrics
            await self.publish_processing_metrics(message, result)
            
            # Log completion
            latency_ms = result.get("latency_ms", 0)
            escalated = result.get("escalated", False)
            tool_calls_count = len(result.get("tool_calls", []))
            
            logger.info(
                f"✅ Processed {channel} message in {latency_ms:.0f}ms | "
                f"escalated={escalated} | tools={tool_calls_count}"
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            logger.error(f"📄 Message: {message}")
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            
            await self.handle_error(message, e)
    
    async def resolve_customer(self, message: Dict[str, Any]) -> str:
        """
        Resolve or create customer from message
        
        Args:
            message: Message data
            
        Returns:
            str: Customer ID
        """
        try:
            # Try different identifiers in order of preference
            email = message.get("customer_email")
            phone = message.get("customer_phone")
            whatsapp_id = message.get("customer_phone")  # WhatsApp uses phone
            name = message.get("customer_name", "")
            
            # Try email first
            if email:
                customer = await queries.get_customer_by_identifier("email", email)
                if customer:
                    return customer["id"]
            
            # Try phone
            if phone:
                customer = await queries.get_customer_by_identifier("phone", phone)
                if customer:
                    return customer["id"]
            
            # Try whatsapp_id
            if whatsapp_id and whatsapp_id != phone:
                customer = await queries.get_customer_by_identifier("whatsapp", whatsapp_id)
                if customer:
                    return customer["id"]
            
            # Create new customer
            customer_id = await queries.create_or_get_customer(
                email=email,
                phone=phone,
                whatsapp_id=whatsapp_id,
                name=name
            )
            
            logger.info(f"👤 Created new customer: {customer_id}")
            return customer_id
            
        except Exception as e:
            logger.error(f"❌ Error resolving customer: {e}")
            raise
    
    async def get_or_create_conversation(self, customer_id: str, channel: str) -> str:
        """
        Get active conversation or create new one
        
        Args:
            customer_id: Customer ID
            channel: Channel type
            
        Returns:
            str: Conversation ID
        """
        try:
            # Check for active conversation within last 24 hours
            active_conversation = await queries.get_active_conversation(
                customer_id=customer_id,
                hours=24
            )
            
            if active_conversation:
                logger.debug(f"💬 Found active conversation: {active_conversation}")
                return active_conversation
            
            # Create new conversation
            conversation_id = await queries.create_conversation(
                customer_id=customer_id,
                channel=channel
            )
            
            logger.debug(f"💬 Created new conversation: {conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"❌ Error getting/creating conversation: {e}")
            raise
    
    async def store_inbound_message(self, conversation_id: str, message: Dict[str, Any]) -> None:
        """
        Store inbound message in database
        
        Args:
            conversation_id: Conversation ID
            message: Message data
        """
        try:
            await queries.store_message(
                conversation_id=conversation_id,
                channel=message["channel"],
                direction="inbound",
                role="customer",
                content=message["content"],
                channel_message_id=message.get("channel_message_id")
            )
            
        except Exception as e:
            logger.error(f"❌ Error storing inbound message: {e}")
            raise
    
    async def get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Get formatted conversation history
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List[Dict]: Formatted history
        """
        try:
            messages = await queries.get_conversation_messages(conversation_id)
            
            # Format for agent context
            history = []
            for msg in messages:
                history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"❌ Error getting conversation history: {e}")
            return []
    
    def build_context(
        self, 
        message: Dict[str, Any], 
        customer_id: str, 
        conversation_id: str, 
        history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Build context for agent
        
        Args:
            message: Message data
            customer_id: Customer ID
            conversation_id: Conversation ID
            history: Conversation history
            
        Returns:
            Dict: Agent context
        """
        return {
            "customer_id": customer_id,
            "conversation_id": conversation_id,
            "channel": message["channel"],
            "ticket_subject": message.get("subject", "Support Request"),
            "metadata": message.get("metadata", {}),
            "history": history,
            "priority": message.get("priority", "medium"),
            "category": message.get("category", "general")
        }
    
    async def store_outbound_message(
        self, 
        conversation_id: str, 
        original_message: Dict[str, Any], 
        result: Dict[str, Any]
    ) -> None:
        """
        Store outbound message in database
        
        Args:
            conversation_id: Conversation ID
            original_message: Original inbound message
            result: Agent processing result
        """
        try:
            await queries.store_message(
                conversation_id=conversation_id,
                channel=original_message["channel"],
                direction="outbound",
                role="agent",
                content=result["output"],
                latency_ms=result.get("latency_ms"),
                tool_calls=result.get("tool_calls", [])
            )
            
        except Exception as e:
            logger.error(f"❌ Error storing outbound message: {e}")
            # Don't raise - we don't want to fail the whole processing
    
    async def publish_processing_metrics(
        self, 
        original_message: Dict[str, Any], 
        result: Dict[str, Any]
    ) -> None:
        """
        Publish processing metrics to Kafka
        
        Args:
            original_message: Original inbound message
            result: Agent processing result
        """
        try:
            metrics_event = {
                "event_type": "message_processed",
                "channel": original_message["channel"],
                "latency_ms": result.get("latency_ms", 0),
                "escalated": result.get("escalated", False),
                "tool_calls_count": len(result.get("tool_calls", [])),
                "success": result.get("success", True),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await publish_event(
                topic=TOPICS["metrics"],
                event=metrics_event,
                key=f"metrics_{original_message['channel']}"
            )
            
        except Exception as e:
            logger.error(f"❌ Error publishing metrics: {e}")
            # Don't raise - metrics failure shouldn't stop processing
    
    async def handle_error(self, message: Dict[str, Any], error: Exception) -> None:
        """
        Handle processing errors
        
        Args:
            message: Failed message
            error: Exception that occurred
        """
        try:
            # Log error details
            logger.error(f"🔥 Processing error details:")
            logger.error(f"   Channel: {message.get('channel', 'unknown')}")
            logger.error(f"   Customer: {message.get('customer_email', message.get('customer_phone', 'unknown'))}")
            logger.error(f"   Error: {str(error)}")
            
            # Try to send apology message
            await self.send_apology_message(message)
            
            # Publish to DLQ
            await self.publish_to_dlq(message, error)
            
        except Exception as e:
            logger.error(f"❌ Error in error handler: {e}")
    
    async def send_apology_message(self, message: Dict[str, Any]) -> None:
        """
        Send apology message via appropriate channel
        
        Args:
            message: Original message that failed
        """
        try:
            channel = message.get("channel", "unknown")
            apology = "Sorry, we're experiencing technical difficulties. A human agent will follow up shortly."
            
            if channel == "email":
                gmail_handler = get_gmail_handler()
                customer_email = message.get("customer_email")
                if customer_email:
                    await gmail_handler.send_message(customer_email, apology)
                    logger.info(f"📧 Sent apology email to {customer_email}")
            
            elif channel == "whatsapp":
                whatsapp_handler = get_whatsapp_handler()
                customer_phone = message.get("customer_phone")
                if customer_phone:
                    await whatsapp_handler.send_message(customer_phone, apology)
                    logger.info(f"📱 Sent apology WhatsApp to {customer_phone}")
            
            elif channel == "web_form":
                # Web form doesn't support outbound messages directly
                logger.info(f"🌐 Web form error noted - customer will see status on ticket page")
            
        except Exception as e:
            logger.error(f"❌ Failed to send apology message: {e}")
    
    async def publish_to_dlq(self, message: Dict[str, Any], error: Exception) -> None:
        """
        Publish failed message to Dead Letter Queue
        
        Args:
            message: Failed message
            error: Exception that occurred
        """
        try:
            dlq_event = {
                "original_message": message,
                "error": str(error),
                "error_traceback": traceback.format_exc(),
                "requires_human": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processor_id": "unified_message_processor"
            }
            
            await publish_event(
                topic=TOPICS["dlq"],
                event=dlq_event,
                key=f"dlq_{message.get('channel', 'unknown')}"
            )
            
            logger.info(f"📨 Published to DLQ: {message.get('channel', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish to DLQ: {e}")

# Global processor instance
_processor: Optional[UnifiedMessageProcessor] = None

async def get_message_processor() -> UnifiedMessageProcessor:
    """Get or create message processor instance"""
    global _processor
    if _processor is None:
        _processor = UnifiedMessageProcessor()
    return _processor

# Graceful shutdown handler
async def shutdown_processor():
    """Shutdown the message processor gracefully"""
    global _processor
    if _processor:
        await _processor.stop()
        _processor = None

if __name__ == "__main__":
    import signal
    import sys
    
    processor = None
    
    async def run_processor():
        """Run the message processor"""
        global processor
        processor = UnifiedMessageProcessor()
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, shutting down...")
            asyncio.create_task(processor.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            await processor.start()
        except KeyboardInterrupt:
            logger.info("⏹️ Received interrupt signal")
        except Exception as e:
            logger.error(f"❌ Processor error: {e}")
        finally:
            if processor:
                await processor.stop()
    
    # Run the processor
    asyncio.run(run_processor())
