"""
TechCorp FTE Metrics Collector
Background worker for collecting and storing system metrics
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from ..database.connection import init_db_pool, close_db_pool, get_connection
from ..database import queries
from ..kafka_client import publish_event, TOPICS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Background metrics collector for the FTE system"""
    
    def __init__(self):
        self.running = False
        self.collection_interval = 3600  # 1 hour in seconds
    
    async def start(self):
        """Start the metrics collector"""
        await init_db_pool()
        self.running = True
        logger.info("📊 Metrics collector started")
        
        try:
            await self.run()
        except Exception as e:
            logger.error(f"❌ Metrics collector error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the metrics collector"""
        self.running = False
        await close_db_pool()
        logger.info("📊 Metrics collector stopped")
    
    async def run(self):
        """Main collection loop"""
        while self.running:
            try:
                # Collect and store hourly metrics
                await self.collect_and_store_metrics()
                
                # Check if it's time to generate daily report (00:05)
                now = datetime.now(timezone.utc)
                if now.hour == 0 and now.minute >= 5 and now.minute < 10:
                    await self.generate_daily_report()
                
                # Wait for next collection
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                logger.info("📊 Metrics collector cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in metrics collection loop: {e}")
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def collect_and_store_metrics(self):
        """
        Collect and store metrics for the last hour
        
        Collects message counts, latency, escalation rates by channel
        """
        try:
            logger.info("📊 Collecting hourly metrics...")
            
            # Calculate time range (last hour)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            # Collect metrics from database
            metrics = await self.collect_hourly_metrics(start_time, end_time)
            
            # Publish to Kafka
            await self.publish_metrics_event(metrics)
            
            # Store in database
            await self.store_hourly_metrics(metrics)
            
            # Log summary
            await self.log_metrics_summary(metrics)
            
        except Exception as e:
            logger.error(f"❌ Error collecting hourly metrics: {e}")
    
    async def collect_hourly_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """
        Collect metrics for the specified time range
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dict: Collected metrics
        """
        metrics = {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_hours": 1
            },
            "channels": {},
            "totals": {
                "total_messages": 0,
                "total_tickets": 0,
                "avg_latency_ms": 0,
                "escalation_rate": 0,
                "success_rate": 0
            }
        }
        
        try:
            async with get_connection() as conn:
                # Get channel breakdown
                channel_metrics = await conn.fetch("""
                    SELECT 
                        m.channel,
                        COUNT(*) as message_count,
                        AVG(m.latency_ms) as avg_latency,
                        COUNT(CASE WHEN m.role = 'customer' THEN 1 END) as inbound_count,
                        COUNT(CASE WHEN m.role = 'agent' THEN 1 END) as outbound_count,
                        COUNT(CASE WHEN t.status = 'escalated' THEN 1 END) as escalated_count,
                        COUNT(CASE WHEN t.status = 'resolved' THEN 1 END) as resolved_count
                    FROM messages m
                    LEFT JOIN conversations c ON m.conversation_id = c.id
                    LEFT JOIN tickets t ON c.id = t.conversation_id
                    WHERE m.created_at >= $1 AND m.created_at < $2
                    GROUP BY m.channel
                """, start_time, end_time)
                
                total_messages = 0
                total_latency = 0
                total_escalated = 0
                total_resolved = 0
                total_success = 0
                
                for row in channel_metrics:
                    channel = row["channel"]
                    channel_data = {
                        "message_count": row["message_count"],
                        "avg_latency_ms": float(row["avg_latency"] or 0),
                        "inbound_count": row["inbound_count"],
                        "outbound_count": row["outbound_count"],
                        "escalated_count": row["escalated_count"],
                        "resolved_count": row["resolved_count"],
                        "escalation_rate": 0,
                        "success_rate": 0
                    }
                    
                    # Calculate rates
                    if row["message_count"] > 0:
                        channel_data["escalation_rate"] = (row["escalated_count"] / row["message_count"]) * 100
                        channel_data["success_rate"] = (row["resolved_count"] / row["message_count"]) * 100
                    
                    metrics["channels"][channel] = channel_data
                    
                    # Accumulate totals
                    total_messages += row["message_count"]
                    if row["avg_latency"]:
                        total_latency += row["avg_latency"] * row["message_count"]
                    total_escalated += row["escalated_count"]
                    total_resolved += row["resolved_count"]
                    total_success += row["resolved_count"]
                
                # Calculate totals
                metrics["totals"]["total_messages"] = total_messages
                metrics["totals"]["avg_latency_ms"] = total_latency / total_messages if total_messages > 0 else 0
                metrics["totals"]["escalation_rate"] = (total_escalated / total_messages * 100) if total_messages > 0 else 0
                metrics["totals"]["success_rate"] = (total_success / total_messages * 100) if total_messages > 0 else 0
                
                # Get ticket counts
                ticket_stats = await conn.fetch("""
                    SELECT 
                        COUNT(*) as total_tickets,
                        COUNT(CASE WHEN status = 'escalated' THEN 1 END) as escalated_tickets,
                        COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_tickets,
                        AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/60) as avg_resolution_minutes
                    FROM tickets
                    WHERE created_at >= $1 AND created_at < $2
                """, start_time, end_time)
                
                if ticket_stats:
                    row = ticket_stats[0]
                    metrics["totals"]["total_tickets"] = row["total_tickets"]
                    metrics["totals"]["avg_resolution_minutes"] = float(row["avg_resolution_minutes"] or 0)
                
        except Exception as e:
            logger.error(f"❌ Error collecting hourly metrics from DB: {e}")
        
        return metrics
    
    async def publish_metrics_event(self, metrics: Dict[str, Any]) -> None:
        """
        Publish metrics to Kafka
        
        Args:
            metrics: Metrics data
        """
        try:
            event = {
                "event_type": "hourly_metrics",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics
            }
            
            await publish_event(
                topic=TOPICS["metrics"],
                event=event,
                key="hourly_metrics"
            )
            
            logger.debug("📊 Published metrics to Kafka")
            
        except Exception as e:
            logger.error(f"❌ Error publishing metrics to Kafka: {e}")
    
    async def store_hourly_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Store hourly metrics in database
        
        Args:
            metrics: Metrics data
        """
        try:
            # Store individual channel metrics
            for channel, channel_metrics in metrics["channels"].items():
                await queries.store_agent_metric(
                    metric_name="hourly_channel_messages",
                    metric_value=float(channel_metrics["message_count"]),
                    channel=channel,
                    dimensions={
                        "avg_latency_ms": channel_metrics["avg_latency_ms"],
                        "escalation_rate": channel_metrics["escalation_rate"],
                        "success_rate": channel_metrics["success_rate"]
                    }
                )
                
                await queries.store_agent_metric(
                    metric_name="hourly_channel_latency",
                    metric_value=float(channel_metrics["avg_latency_ms"]),
                    channel=channel
                )
            
            # Store total metrics
            totals = metrics["totals"]
            await queries.store_agent_metric(
                metric_name="hourly_total_messages",
                metric_value=float(totals["total_messages"]),
                dimensions={
                    "avg_latency_ms": totals["avg_latency_ms"],
                    "escalation_rate": totals["escalation_rate"],
                    "success_rate": totals["success_rate"]
                }
            )
            
            logger.debug("📊 Stored hourly metrics in database")
            
        except Exception as e:
            logger.error(f"❌ Error storing hourly metrics: {e}")
    
    async def log_metrics_summary(self, metrics: Dict[str, Any]) -> None:
        """
        Log metrics summary
        
        Args:
            metrics: Metrics data
        """
        try:
            totals = metrics["totals"]
            
            logger.info(
                f"📊 Hourly Metrics Summary: "
                f"Messages: {totals['total_messages']} | "
                f"Avg Latency: {totals['avg_latency_ms']:.0f}ms | "
                f"Escalation Rate: {totals['escalation_rate']:.1f}% | "
                f"Success Rate: {totals['success_rate']:.1f}%"
            )
            
            # Log channel breakdown
            for channel, channel_metrics in metrics["channels"].items():
                logger.info(
                    f"   {channel.upper()}: {channel_metrics['message_count']} msgs | "
                    f"{channel_metrics['avg_latency_ms']:.0f}ms avg | "
                    f"{channel_metrics['escalation_rate']:.1f}% escalated"
                )
            
        except Exception as e:
            logger.error(f"❌ Error logging metrics summary: {e}")
    
    async def generate_daily_report(self, date: Optional[datetime] = None) -> None:
        """
        Generate daily report for specified date
        
        Args:
            date: Date to generate report for (defaults to yesterday)
        """
        try:
            if date is None:
                date = datetime.now(timezone.utc).date() - timedelta(days=1)
            
            logger.info(f"📊 Generating daily report for {date}")
            
            # Query all tickets for that date
            report_data = await self.collect_daily_report_data(date)
            
            # Upsert into daily_reports table
            await self.store_daily_report(date, report_data)
            
            logger.info(f"✅ Daily report generated for {date}")
            
        except Exception as e:
            logger.error(f"❌ Error generating daily report for {date}: {e}")
    
    async def collect_daily_report_data(self, date: datetime.date) -> Dict[str, Any]:
        """
        Collect daily report data
        
        Args:
            date: Date to collect data for
            
        Returns:
            Dict: Daily report data
        """
        report_data = {
            "total_tickets": 0,
            "resolved_tickets": 0,
            "escalated_tickets": 0,
            "avg_sentiment": 0,
            "avg_response_time_ms": 0,
            "channel_breakdown": {},
            "top_categories": {}
        }
        
        try:
            async with get_connection() as conn:
                # Get ticket statistics
                ticket_stats = await conn.fetch("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                        COUNT(CASE WHEN status = 'escalated' THEN 1 END) as escalated,
                        AVG(c.sentiment_score) as avg_sentiment,
                        AVG(m.latency_ms) as avg_response_time
                    FROM tickets t
                    LEFT JOIN conversations c ON t.conversation_id = c.id
                    LEFT JOIN messages m ON c.id = m.conversation_id AND m.role = 'agent'
                    WHERE DATE(t.created_at) = $1
                """, date)
                
                if ticket_stats:
                    row = ticket_stats[0]
                    report_data["total_tickets"] = row["total"]
                    report_data["resolved_tickets"] = row["resolved"]
                    report_data["escalated_tickets"] = row["escalated"]
                    report_data["avg_sentiment"] = float(row["avg_sentiment"] or 0)
                    report_data["avg_response_time_ms"] = int(row["avg_response_time"] or 0)
                
                # Get channel breakdown
                channel_stats = await conn.fetch("""
                    SELECT 
                        t.source_channel,
                        COUNT(*) as count,
                        COUNT(CASE WHEN t.status = 'resolved' THEN 1 END) as resolved,
                        COUNT(CASE WHEN t.status = 'escalated' THEN 1 END) as escalated
                    FROM tickets t
                    WHERE DATE(t.created_at) = $1
                    GROUP BY t.source_channel
                """, date)
                
                for row in channel_stats:
                    channel = row["source_channel"]
                    report_data["channel_breakdown"][channel] = {
                        "total": row["count"],
                        "resolved": row["resolved"],
                        "escalated": row["escalated"]
                    }
                
                # Get top categories
                category_stats = await conn.fetch("""
                    SELECT 
                        category,
                        COUNT(*) as count
                    FROM tickets
                    WHERE DATE(created_at) = $1 AND category IS NOT NULL
                    GROUP BY category
                    ORDER BY count DESC
                    LIMIT 5
                """, date)
                
                for row in category_stats:
                    report_data["top_categories"][row["category"]] = row["count"]
                
        except Exception as e:
            logger.error(f"❌ Error collecting daily report data: {e}")
        
        return report_data
    
    async def store_daily_report(self, date: datetime.date, report_data: Dict[str, Any]) -> None:
        """
        Store daily report in database
        
        Args:
            date: Report date
            report_data: Report data
        """
        try:
            async with get_connection() as conn:
                await conn.execute("""
                    INSERT INTO daily_reports (
                        report_date, total_tickets, resolved_tickets, escalated_tickets,
                        avg_sentiment, avg_response_time_ms, channel_breakdown, top_categories
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (report_date) DO UPDATE SET
                        total_tickets = EXCLUDED.total_tickets,
                        resolved_tickets = EXCLUDED.resolved_tickets,
                        escalated_tickets = EXCLUDED.escalated_tickets,
                        avg_sentiment = EXCLUDED.avg_sentiment,
                        avg_response_time_ms = EXCLUDED.avg_response_time_ms,
                        channel_breakdown = EXCLUDED.channel_breakdown,
                        top_categories = EXCLUDED.top_categories,
                        generated_at = NOW()
                """, date, report_data["total_tickets"], report_data["resolved_tickets"],
                    report_data["escalated_tickets"], report_data["avg_sentiment"],
                    report_data["avg_response_time_ms"], report_data["channel_breakdown"],
                    report_data["top_categories"])
            
            logger.debug(f"📊 Stored daily report for {date}")
            
        except Exception as e:
            logger.error(f"❌ Error storing daily report: {e}")

# Global collector instance
_collector: Optional[MetricsCollector] = None

async def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector instance"""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector

if __name__ == "__main__":
    import signal
    import sys
    
    collector = None
    
    async def run_collector():
        """Run the metrics collector"""
        global collector
        collector = MetricsCollector()
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, shutting down...")
            collector.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            await collector.start()
        except KeyboardInterrupt:
            logger.info("⏹️ Received interrupt signal")
        except Exception as e:
            logger.error(f"❌ Collector error: {e}")
        finally:
            if collector:
                await collector.stop()
    
    # Run the collector
    asyncio.run(run_collector())
