"""
Locust load test for TechCorp FTE System
Tests system performance under concurrent user load
"""

from locust import HttpUser, task, between, events
import json
import random
import string

class WebFormUser(HttpUser):
    """
    Simulates users interacting with the web form
    Weight: 3 (higher priority)
    """
    wait_time = between(2, 8)
    weight = 3
    
    def on_start(self):
        """Called when a user starts running"""
        self.email = f"user{random.randint(1000, 9999)}@example.com"
        self.name = self._generate_random_name()
    
    def _generate_random_name(self):
        """Generate a random name"""
        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa"]
        last_names = ["Smith", "Johnson", "Brown", "Davis", "Wilson", "Moore", "Taylor", "Anderson"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def _generate_random_message(self, min_length=50, max_length=500):
        """Generate a random message"""
        topics = [
            "login issue",
            "password reset",
            "API integration",
            "billing question",
            "feature request",
            "bug report",
            "account management",
            "technical support",
            "general inquiry"
        ]
        
        topic = random.choice(topics)
        base_message = f"I need help with {topic}. "
        
        # Add random details
        details = [
            "This is urgent and I need assistance as soon as possible.",
            "I've tried troubleshooting myself but nothing seems to work.",
            "This has been happening for the past few days.",
            "I'm not sure what to do next, please advise.",
            "This is blocking my work and needs immediate attention."
        ]
        
        message = base_message + random.choice(details)
        
        # Add random filler if needed
        while len(message) < min_length:
            filler = f" Additional context: {' '.join(random.choices(['The system', 'My application', 'Our team', 'The platform'], k=3)}. "
            message += filler
        
        return message[:max_length]
    
    @task
    def submit_form(self):
        """Submit a support form"""
        categories = ["general", "technical", "billing", "feedback", "bug_report"]
        priorities = ["low", "medium", "high"]
        
        submission_data = {
            "name": self.name,
            "email": self.email,
            "subject": f"Support Request - {random.choice(['Login Issue', 'API Question', 'Billing Inquiry'])}",
            "category": random.choice(categories),
            "priority": random.choice(priorities),
            "message": self._generate_random_message()
        }
        
        with self.client.post("/api/support/submit", json=submission_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                # Store ticket ID for potential use in other tasks
                self.ticket_id = data.get("ticket_id")
                events.request_success.fire()
                self.environment.stats["successful_submissions"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_submissions"] += 1
    
    @task
    def check_health(self):
        """Check system health endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    events.request_success.fire()
                    self.environment.stats["healthy_checks"] += 1
                else:
                    events.request_failure.fire()
                    self.environment.stats["degraded_checks"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_health_checks"] += 1
    
    @task
    def get_form_config(self):
        """Get form configuration"""
        with self.client.get("/api/support/form-config", catch_response=True) as response:
            if response.status_code == 200:
                events.request_success.fire()
                self.environment.stats["config_checks"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_config_checks"] += 1
    
    @task
    def check_ticket_status(self):
        """Check ticket status (if ticket_id exists)"""
        if hasattr(self, 'ticket_id') and self.ticket_id:
            with self.client.get(f"/api/support/ticket/{self.ticket_id}", catch_response=True) as response:
                if response.status_code == 200:
                    events.request_success.fire()
                    self.environment.stats["status_checks"] += 1
                else:
                    events.request_failure.fire()
                    self.environment.stats["failed_status_checks"] += 1

class MetricsUser(HttpUser):
    """
    Simulates users checking metrics and admin endpoints
    Weight: 1 (lower priority)
    """
    wait_time = between(10, 30)
    weight = 1
    
    @task
    def check_metrics(self):
        """Check channel metrics"""
        hours = random.choice([1, 6, 24, 72])
        
        with self.client.get(f"/api/metrics/channels?hours={hours}", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                events.request_success.fire()
                self.environment.stats["metrics_checks"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_metrics_checks"] += 1
    
    @task
    def check_overview(self):
        """Check admin overview"""
        with self.client.get("/api/admin/overview", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                events.request_success.fire()
                self.environment.stats["overview_checks"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_overview_checks"] += 1
    
    @task
    def check_daily_metrics(self):
        """Check daily metrics"""
        # Check metrics for random recent date
        from datetime import date, timedelta
        days_ago = random.randint(0, 7)
        target_date = (date.today() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        with self.client.get(f"/api/metrics/daily/{target_date}", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                events.request_success.fire()
                self.environment.stats["daily_metrics_checks"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_daily_metrics"] += 1
    
    @task
    def check_health(self):
        """Check system health"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    events.request_success.fire()
                    self.environment.stats["healthy_checks"] += 1
                else:
                    events.request_failure.fire()
                    self.environment.stats["degraded_checks"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_health_checks"] += 1

class WhatsAppUser(HttpUser):
    """
    Simulates WhatsApp webhook interactions
    Weight: 1 (lower priority)
    """
    wait_time = between(5, 15)
    weight = 1
    
    def on_start(self):
        """Initialize WhatsApp user"""
        self.phone_number = f"923001234567"
    
    @task
    def test_webhook_verification(self):
        """Test WhatsApp webhook verification"""
        params = {
            "hub.mode": "subscribe",
            "hub.challenge": "test_challenge_" + str(random.randint(1000, 9999)),
            "hub.verify_token": "any_random_string_you_choose"
        }
        
        with self.client.get("/webhooks/whatsapp", params=params, catch_response=True) as response:
            if response.status_code == 200:
                events.request_success.fire()
                self.environment.stats["webhook_verifications"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_webhook_verifications"] += 1
    
    @task
    def test_webhook_message(self):
        """Test WhatsApp webhook with message"""
        payload = {
            "entry": [{
                "id": f"webhook_{random.randint(1000, 9999)}",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": self.phone_number
                        },
                        "messages": [{
                            "from": self.phone_number,
                            "id": f"msg_{random.randint(1000, 9999)}",
                            "timestamp": str(int(time.time())),
                            "text": {
                                "body": f"Test message {random.randint(1, 100)}"
                            },
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
        
        with self.client.post("/webhooks/whatsapp", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                events.request_success.fire()
                self.environment.stats["webhook_messages"] += 1
            else:
                events.request_failure.fire()
                self.environment.stats["failed_webhook_messages"] += 1

# Custom event listeners for statistics
def on_locust_init(environment, runner, **kwargs):
    """Initialize statistics tracking"""
    environment.stats = {
        "successful_submissions": 0,
        "failed_submissions": 0,
        "healthy_checks": 0,
        "degraded_checks": 0,
        "failed_health_checks": 0,
        "metrics_checks": 0,
        "failed_metrics_checks": 0,
        "overview_checks": 0,
        "failed_overview_checks": 0,
        "daily_metrics_checks": 0,
        "failed_daily_metrics_checks": 0,
        "config_checks": 0,
        "failed_config_checks": 0,
        "status_checks": 0,
        "failed_status_checks": 0,
        "webhook_verifications": 0,
        "failed_webhook_verifications": 0,
        "webhook_messages": 0,
        "failed_webhook_messages": 0
    }
    
    # Add request type statistics
    environment.request_type_stats = {}
    
    def on_request_start(request_type, **kwargs):
        """Track request start"""
        environment.request_type_stats[request_type] = environment.request_type_stats.get(request_type, 0) + 1
    
    def on_request_success(self, request_type, **kwargs):
        """Track successful request"""
        environment.request_type_stats[request_type] = environment.request_type_stats.get(request_type, 0) + 1
    
    def on_request_failure(self, request_type, **kwargs):
        """Track failed request"""
        environment.request_type_stats[request_type] = environment.request_type_stats.get(request_type, 0) + 1

# Performance targets
class PerformanceTargets:
    """Define performance targets for the load test"""
    
    TARGET_CONCURRENT_USERS = 50
    TARGET_P95_RESPONSE_TIME = 3000  # milliseconds
    TARGET_ERROR_RATE = 5.0  # percentage
    TARGET_SUCCESS_RATE = 95.0  # percentage
    
    @staticmethod
    def check_performance(stats):
        """Check if performance meets targets"""
        total_requests = stats.total_requests
        if total_requests == 0:
            return True, "No requests made"
        
        error_rate = (stats.num_requests - stats.num_requests) / total_requests * 100
        success_rate = 100 - error_rate
        
        p95_response_time = stats.get_response_time_percentile(95)
        
        meets_concurrent = stats.num_users >= PerformanceTargets.TARGET_CONCURRENT_USERS
        meets_response_time = p95_response_time <= PerformanceTargets.TARGET_P95_RESPONSE_TIME
        meets_error_rate = error_rate <= PerformanceTargets.TARGET_ERROR_RATE
        meets_success_rate = success_rate >= PerformanceTargets.TARGET_SUCCESS_RATE
        
        return (
            meets_concurrent and 
            meets_response_time and 
            meets_error_rate and 
            meets_success_rate
        ), f"Users: {stats.num_users}, P95: {p95_response_time:.0f}ms, Error Rate: {error_rate:.1f}%"

# Test scenarios
class TestScenarios:
    """Define specific test scenarios"""
    
    @staticmethod
    def steady_state_test():
        """Steady state load test"""
        return {
            "user_classes": [WebFormUser, MetricsUser],
            "spawn_rate": "5 users per second",
            "run_time": "10 minutes",
            "target_users": 50
        }
    
    @staticmethod
    def stress_test():
        """Stress test with high load"""
        return {
            "user_classes": [WebFormUser],
            "spawn_rate": "20 users per second",
            "run_time": "5 minutes",
            "target_users": 100
        }
    
    @staticmethod
    def spike_test():
        """Spike test with sudden load increase"""
        return {
            "user_classes": [WebFormUser],
            "spawn_rate": "50 users per second",
            "run_time": "2 minutes",
            "target_users": 200
        }

# Configuration
class TestConfig:
    """Test configuration"""
    
    HOST = "http://localhost:8000"
    TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    # Load test configuration
    LOAD_TEST_DURATION = "10m"
    TARGET_USERS = 50
    SPAWN_RATE = "5/s"
    
    # Performance targets
    P95_RESPONSE_TIME = 3000
    ERROR_RATE_THRESHOLD = 5.0
    SUCCESS_RATE_THRESHOLD = 95.0

if __name__ == "__main__":
    import time
    import os
    
    # Set environment for testing
    os.environ["LOCUST_HOST"] = TestConfig.HOST
    os.environ["LOCUST_TIMEOUT"] = str(TestConfig.TIMEOUT)
    
    # Run the load test
    print(f"Starting TechCorp FTE Load Test")
    print(f"Target: {TestConfig.TARGET_USERS} concurrent users")
    print(f"P95 Response Time Target: {TestConfig.P95_RESPONSE_TIME}ms")
    print(f"Error Rate Threshold: {TestConfig.ERROR_RATE_THRESHOLD}%")
    print(f"Success Rate Threshold: {TestConfig.SUCCESS_RATE_THRESHOLD}%")
    print("=" * 50)
    
    # This would typically be run with:
    # locust -f load_test.py --host http://localhost:8000 --users 50 --spawn-rate 5 --run-time 10m --html report.html
