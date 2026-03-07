#!/usr/bin/env python3
"""
TechCorp FTE Kafka Topics Setup Script
Creates all required Kafka topics on first run
"""

import sys
import logging
from kafka import KafkaAdminClient, KafkaException
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError
from production.kafka_client import TOPICS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_topics(bootstrap_servers: str = "localhost:9092"):
    """
    Create all Kafka topics defined in TOPICS dict
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
    """
    try:
        # Create admin client
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='fte_topic_setup'
        )
        
        logger.info(f"🔗 Connected to Kafka: {bootstrap_servers}")
        
        # Prepare topic configurations
        topic_configs = {
            'num_partitions': 3,
            'replication_factor': 1,
            'retention_ms': 7 * 24 * 60 * 60 * 1000,  # 7 days retention
            'cleanup_policy': 'delete'
        }
        
        # Create NewTopic objects for each topic
        new_topics = []
        for topic_key, topic_name in TOPICS.items():
            # Special configurations for specific topics
            topic_config = topic_configs.copy()
            
            if topic_key == 'dlq':
                # DLQ needs longer retention
                topic_config['retention_ms'] = 30 * 24 * 60 * 60 * 1000  # 30 days
                topic_config['num_partitions'] = 1  # Single partition for DLQ
            
            elif topic_key == 'metrics':
                # Metrics topic can have more partitions for better throughput
                topic_config['num_partitions'] = 6
            
            new_topics.append(NewTopic(
                name=topic_name,
                num_partitions=topic_config['num_partitions'],
                replication_factor=topic_config['replication_factor'],
                topic_configs={
                    'retention.ms': str(topic_config['retention_ms']),
                    'cleanup.policy': topic_config['cleanup_policy']
                }
            ))
        
        logger.info(f"📋 Creating {len(new_topics)} topics...")
        
        # Create topics
        result = admin_client.create_topics(new_topics, validate_only=False)
        
        # Check results
        for topic_future in result.values():
            try:
                topic_result = topic_future.result()
                logger.info(f"✅ Created topic: {topic_result}")
            except TopicAlreadyExistsError:
                logger.info(f"⏭️  Topic already exists: {topic_future.topic}")
            except KafkaException as e:
                logger.error(f"❌ Failed to create topic {topic_future.topic}: {e}")
        
        # List all topics to verify
        logger.info("📋 Verifying topic creation...")
        existing_topics = admin_client.list_topics()
        
        logger.info(f"📊 Current topics ({len(existing_topics)}):")
        for topic in sorted(existing_topics):
            status = "✅" if topic in TOPICS.values() else "ℹ️"
            logger.info(f"   {status} {topic}")
        
        # Check if all our topics exist
        missing_topics = set(TOPICS.values()) - set(existing_topics)
        if missing_topics:
            logger.warning(f"⚠️  Missing topics: {missing_topics}")
        else:
            logger.info("✅ All required topics created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup Kafka topics: {e}")
        sys.exit(1)
    
    finally:
        try:
            admin_client.close()
            logger.info("🔒 Admin client closed")
        except:
            pass

def check_kafka_connection(bootstrap_servers: str = "localhost:9092") -> bool:
    """
    Check if Kafka is accessible
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        
    Returns:
        bool: True if Kafka is accessible
    """
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=5000
        )
        
        # Try to list topics
        topics = admin_client.list_topics()
        admin_client.close()
        
        logger.info(f"✅ Kafka connection successful. Found {len(topics)} existing topics")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cannot connect to Kafka: {e}")
        logger.error("   Make sure Kafka is running and accessible")
        return False

def main():
    """Main setup function"""
    logger.info("🚀 TechCorp FTE Kafka Topics Setup")
    logger.info("=" * 50)
    
    bootstrap_servers = "localhost:9092"
    
    # Check Kafka connection first
    logger.info("🔍 Checking Kafka connection...")
    if not check_kafka_connection(bootstrap_servers):
        logger.error("❌ Kafka is not accessible. Please check your Kafka setup.")
        logger.info("💡 If using Docker Compose, run: docker-compose up -d kafka zookeeper")
        sys.exit(1)
    
    # Create topics
    create_topics(bootstrap_servers)
    
    logger.info("\n🎉 Kafka topics setup completed!")
    logger.info("📋 Topics created:")
    for key, name in TOPICS.items():
        logger.info(f"   {key}: {name}")
    
    logger.info("\n🚀 You can now start the FTE services!")

if __name__ == "__main__":
    main()
