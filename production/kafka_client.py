"""
TechCorp FTE Kafka Client
Producer and Consumer for message queue handling using aiokafka
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Callable, Any, Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka topics configuration
TOPICS = {
    "tickets_incoming": "fte.tickets.incoming",
    "email_inbound": "fte.channels.email.inbound",
    "whatsapp_inbound": "fte.channels.whatsapp.inbound",
    "webform_inbound": "fte.channels.webform.inbound",
    "escalations": "fte.escalations",
    "metrics": "fte.metrics",
    "dlq": "fte.dlq",
}

class FTEKafkaProducer:
    """Async Kafka producer for TechCorp FTE system"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka producer
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False
    
    async def start(self) -> None:
        """Start the Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas to acknowledge
                enable_idempotence=True,
            )
            await self.producer.start()
            self._started = True
            logger.info("✅ Kafka producer started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka producer: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the Kafka producer"""
        if self.producer and self._started:
            try:
                await self.producer.stop()
                self._started = False
                logger.info("🔒 Kafka producer stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping Kafka producer: {e}")
    
    async def publish(self, topic: str, event: Dict, key: Optional[str] = None) -> bool:
        """
        Publish event to Kafka topic
        
        Args:
            topic: Topic name (can be either key from TOPICS or full topic name)
            event: Event data to publish
            key: Optional message key for partitioning
            
        Returns:
            bool: True if published successfully, False if sent to DLQ
        """
        if not self._started or not self.producer:
            logger.error("❌ Producer not started. Call start() first.")
            return False
        
        # Resolve topic name
        topic_name = TOPICS.get(topic, topic)
        
        # Add timestamp to event
        event_with_timestamp = event.copy()
        event_with_timestamp['timestamp'] = datetime.now(timezone.utc).isoformat()
        event_with_timestamp['producer_id'] = 'fte_producer'
        
        try:
            # Send message
            await self.producer.send_and_wait(
                topic=topic_name,
                value=event_with_timestamp,
                key=key
            )
            logger.debug(f"📤 Published to {topic_name}: {key}")
            return True
            
        except KafkaError as e:
            logger.warning(f"⚠️ Failed to publish to {topic_name}: {e}. Retrying once...")
            
            try:
                # Retry once
                await self.producer.send_and_wait(
                    topic=topic_name,
                    value=event_with_timestamp,
                    key=key
                )
                logger.info(f"📤 Retry successful for {topic_name}: {key}")
                return True
                
            except KafkaError as retry_error:
                logger.error(f"❌ Retry failed for {topic_name}: {retry_error}. Sending to DLQ...")
                
                # Send to DLQ
                await self._send_to_dlq(topic_name, event_with_timestamp, key, str(retry_error))
                return False
        
        except Exception as e:
            logger.error(f"❌ Unexpected error publishing to {topic_name}: {e}")
            await self._send_to_dlq(topic_name, event_with_timestamp, key, str(e))
            return False
    
    async def _send_to_dlq(self, original_topic: str, event: Dict, key: Optional[str], error_reason: str) -> None:
        """
        Send failed message to Dead Letter Queue
        
        Args:
            original_topic: Original topic that failed
            event: Original event data
            key: Original message key
            error_reason: Reason for failure
        """
        dlq_event = {
            '_original_topic': original_topic,
            '_original_key': key,
            '_dlq_reason': error_reason,
            '_dlq_timestamp': datetime.now(timezone.utc).isoformat(),
            '_retry_count': 1,
            'original_event': event
        }
        
        try:
            await self.producer.send_and_wait(
                topic=TOPICS['dlq'],
                value=dlq_event,
                key=f"failed_{original_topic}_{key}" if key else f"failed_{original_topic}"
            )
            logger.warning(f"📨 Sent to DLQ from {original_topic}: {error_reason}")
            
        except Exception as dlq_error:
            logger.error(f"❌ Failed to send to DLQ: {dlq_error}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check producer health
        
        Returns:
            Dict: Health status information
        """
        return {
            'started': self._started,
            'bootstrap_servers': self.bootstrap_servers,
            'producer_config': {
                'acks': 'all',
                'retries': 1,
                'enable_idempotence': True
            }
        }

class FTEKafkaConsumer:
    """Async Kafka consumer for TechCorp FTE system"""
    
    def __init__(self, topics: List[str], group_id: str, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka consumer
        
        Args:
            topics: List of topic names (can be keys from TOPICS or full names)
            group_id: Consumer group ID
            bootstrap_servers: Kafka bootstrap servers
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._started = False
        self._running = False
        
        # Resolve topic names
        self.topic_names = [TOPICS.get(topic, topic) for topic in topics]
    
    async def start(self) -> None:
        """Start the Kafka consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topic_names,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
            )
            await self.consumer.start()
            self._started = True
            logger.info(f"✅ Kafka consumer started for group: {self.group_id}")
            logger.info(f"📋 Subscribed to topics: {', '.join(self.topic_names)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the Kafka consumer"""
        self._running = False
        if self.consumer and self._started:
            try:
                await self.consumer.stop()
                self._started = False
                logger.info("🔒 Kafka consumer stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping Kafka consumer: {e}")
    
    async def consume(self, handler: Callable[[str, Dict, Optional[str]], None]) -> None:
        """
        Consume messages from subscribed topics
        
        Args:
            handler: Async function to handle each message (topic, message, key)
        """
        if not self._started or not self.consumer:
            logger.error("❌ Consumer not started. Call start() first.")
            return
        
        self._running = True
        logger.info("🔄 Starting message consumption...")
        
        try:
            async for message in self.consumer:
                if not self._running:
                    break
                
                try:
                    # Extract message data
                    topic = message.topic
                    key = message.key
                    value = message.value
                    
                    logger.debug(f"📨 Received from {topic}: {key}")
                    
                    # Call handler
                    await handler(topic, value, key)
                    
                except Exception as handler_error:
                    logger.error(f"❌ Error handling message from {message.topic}: {handler_error}")
                    logger.error(f"📄 Message: {message.value}")
                    logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                    
                    # Continue to next message
                    continue
                    
        except Exception as consume_error:
            logger.error(f"❌ Error in consumer loop: {consume_error}")
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
        
        finally:
            logger.info("⏹️ Message consumption stopped")
    
    async def pause(self) -> None:
        """Pause message consumption"""
        if self.consumer:
            self.consumer.pause(*self.consumer.subscription())
            logger.info("⏸️ Consumer paused")
    
    async def resume(self) -> None:
        """Resume message consumption"""
        if self.consumer:
            self.consumer.resume(*self.consumer.subscription())
            logger.info("▶️ Consumer resumed")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check consumer health
        
        Returns:
            Dict: Health status information
        """
        subscription = list(self.consumer.subscription()) if self.consumer else []
        
        return {
            'started': self._started,
            'running': self._running,
            'group_id': self.group_id,
            'subscribed_topics': subscription,
            'bootstrap_servers': self.bootstrap_servers
        }

# Global producer and consumer instances for convenience
_producer: Optional[FTEKafkaProducer] = None
_consumers: Dict[str, FTEKafkaConsumer] = {}

async def get_producer() -> FTEKafkaProducer:
    """Get or create global producer instance"""
    global _producer
    if _producer is None:
        _producer = FTEKafkaProducer()
        await _producer.start()
    return _producer

async def get_consumer(topics: List[str], group_id: str) -> FTEKafkaConsumer:
    """Get or create consumer instance"""
    key = f"{group_id}:{','.join(topics)}"
    if key not in _consumers:
        _consumers[key] = FTEKafkaConsumer(topics, group_id)
        await _consumers[key].start()
    return _consumers[key]

async def publish_event(topic: str, event: Dict, key: Optional[str] = None) -> bool:
    """
    Convenience function to publish event
    
    Args:
        topic: Topic name
        event: Event data
        key: Optional message key
        
    Returns:
        bool: True if published successfully
    """
    producer = await get_producer()
    return await producer.publish(topic, event, key)

async def shutdown_kafka() -> None:
    """Shutdown all Kafka connections"""
    global _producer, _consumers
    
    # Stop all consumers
    for consumer in _consumers.values():
        await consumer.stop()
    _consumers.clear()
    
    # Stop producer
    if _producer:
        await _producer.stop()
        _producer = None
    
    logger.info("🔒 All Kafka connections shutdown")

# Example usage
if __name__ == "__main__":
    async def example_handler(topic: str, message: Dict, key: Optional[str]) -> None:
        """Example message handler"""
        print(f"Received from {topic} (key: {key}): {message}")
    
    async def example_producer():
        """Example producer usage"""
        producer = FTEKafkaProducer()
        await producer.start()
        
        # Publish test message
        await producer.publish("tickets_incoming", {
            "customer_id": "test-123",
            "message": "Test message",
            "channel": "email"
        }, key="test-123")
        
        await producer.stop()
    
    async def example_consumer():
        """Example consumer usage"""
        consumer = FTEKafkaConsumer(["tickets_incoming"], "test-group")
        await consumer.start()
        
        # Consume for 30 seconds
        await asyncio.wait_for(consumer.consume(example_handler), timeout=30)
        
        await consumer.stop()
    
    async def main():
        """Run example"""
        try:
            # Start producer and send message
            await example_producer()
            
            # Start consumer and receive message
            await example_consumer()
            
        except KeyboardInterrupt:
            print("\n⏹️ Shutting down...")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    asyncio.run(main())
