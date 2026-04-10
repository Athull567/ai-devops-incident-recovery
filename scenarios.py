"""
Scenario definitions for the DevOps Incident Recovery Environment.

Defines 5 tasks across 3 difficulty levels (easy, medium, hard).
Each scenario includes initial service states, metrics, logs, alerts,
the hidden root cause, and the expected resolution steps.
"""

import random
from typing import Any, Dict, List, Optional
from models import ServiceInfo, ServiceStatus, AlertInfo


# =============================================================================
# Service Dependency Graph
# =============================================================================

SERVICE_DEPENDENCIES = {
    "api-server": ["database", "cache", "auth-service"],
    "frontend": ["api-server"],
    "payment-service": ["api-server", "database"],
    "auth-service": ["database", "cache"],
    "database": [],
    "cache": [],
    "service-mesh": ["api-server", "frontend", "payment-service", "auth-service"],
}

ALL_SERVICES = list(SERVICE_DEPENDENCIES.keys())


def _healthy_service(name: str, uptime: int = 86400) -> ServiceInfo:
    """Create a healthy service with normal metrics."""
    return ServiceInfo(
        name=name,
        status=ServiceStatus.RUNNING,
        cpu_usage=round(random.uniform(5, 25), 1),
        memory_usage=round(random.uniform(20, 45), 1),
        latency_ms=round(random.uniform(5, 50), 1),
        error_rate=round(random.uniform(0.0, 0.5), 2),
        uptime_seconds=uptime,
        replicas=2,
    )


def _base_services(seed: Optional[int] = None) -> Dict[str, ServiceInfo]:
    """Generate a full set of healthy services."""
    if seed is not None:
        random.seed(seed)
    services = {}
    for name in ALL_SERVICES:
        services[name] = _healthy_service(name, uptime=random.randint(3600, 259200))
    return services


# =============================================================================
# Scenario Definitions
# =============================================================================

class Scenario:
    """A single incident scenario with all necessary configuration."""

    def __init__(
        self,
        task_id: str,
        difficulty: str,
        title: str,
        description: str,
        root_cause: str,
        root_cause_service: str,
        expected_actions: List[Dict[str, str]],
        optimal_steps: int,
    ):
        self.task_id = task_id
        self.difficulty = difficulty
        self.title = title
        self.description = description
        self.root_cause = root_cause
        self.root_cause_service = root_cause_service
        self.expected_actions = expected_actions  # ordered list of {action_type, target_service}
        self.optimal_steps = optimal_steps

    def generate_initial_state(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate the initial services, logs, and alerts for this scenario."""
        services = _base_services(seed)
        logs = []
        alerts = []

        # Apply scenario-specific modifications
        generator = SCENARIO_GENERATORS.get(self.task_id)
        if generator:
            services, logs, alerts = generator(services, seed)

        return {
            "services": services,
            "logs": logs,
            "alerts": alerts,
        }


# =============================================================================
# Scenario Generators (modify healthy baseline to inject failures)
# =============================================================================

def _gen_easy_1(services: Dict[str, ServiceInfo], seed: Optional[int] = None):
    """Easy Task 1: High CPU on api-server due to memory leak."""
    services["api-server"] = ServiceInfo(
        name="api-server",
        status=ServiceStatus.DEGRADED,
        cpu_usage=92.5,
        memory_usage=88.3,
        latency_ms=850.0,
        error_rate=12.5,
        uptime_seconds=172800,
        replicas=2,
    )

    logs = [
        "[2024-03-15 10:00:01] api-server: WARNING - Memory usage exceeding threshold: 88.3%",
        "[2024-03-15 10:00:15] api-server: ERROR - Request timeout after 800ms for /api/v1/users",
        "[2024-03-15 10:00:22] api-server: WARNING - CPU spike detected: 92.5%",
        "[2024-03-15 10:00:30] api-server: ERROR - GC overhead limit exceeded, possible memory leak",
        "[2024-03-15 10:00:45] api-server: WARNING - Response latency above SLA: 850ms > 200ms",
        "[2024-03-15 10:01:00] frontend: INFO - Increased error rate from upstream api-server",
        "[2024-03-15 10:01:05] database: INFO - All connections healthy, query performance normal",
        "[2024-03-15 10:01:10] cache: INFO - Cache hit ratio: 94.2%, status normal",
    ]

    alerts = [
        AlertInfo(
            severity="critical",
            service="api-server",
            message="CPU usage at 92.5% - exceeds critical threshold (80%)",
            timestamp="2024-03-15 10:00:22",
        ),
        AlertInfo(
            severity="warning",
            service="api-server",
            message="Memory usage at 88.3% - possible memory leak detected",
            timestamp="2024-03-15 10:00:01",
        ),
        AlertInfo(
            severity="warning",
            service="api-server",
            message="P99 latency 850ms exceeds SLA of 200ms",
            timestamp="2024-03-15 10:00:45",
        ),
    ]

    return services, logs, alerts


def _gen_easy_2(services: Dict[str, ServiceInfo], seed: Optional[int] = None):
    """Easy Task 2: Payment service crashed."""
    services["payment-service"] = ServiceInfo(
        name="payment-service",
        status=ServiceStatus.CRASHED,
        cpu_usage=0.0,
        memory_usage=0.0,
        latency_ms=0.0,
        error_rate=100.0,
        uptime_seconds=0,
        replicas=0,
    )

    logs = [
        "[2024-03-15 14:30:00] payment-service: FATAL - Unhandled exception in main thread",
        "[2024-03-15 14:30:01] payment-service: FATAL - Service terminated with exit code 1",
        "[2024-03-15 14:30:02] payment-service: INFO - All replicas down, health check failing",
        "[2024-03-15 14:30:10] api-server: ERROR - Connection refused from payment-service:8080",
        "[2024-03-15 14:30:15] api-server: WARNING - Payment endpoint returning 503 errors",
        "[2024-03-15 14:30:20] frontend: WARNING - Payment page showing error state",
        "[2024-03-15 14:30:25] database: INFO - Connection pool healthy, 12/50 connections used",
        "[2024-03-15 14:30:30] auth-service: INFO - All systems operational",
    ]

    alerts = [
        AlertInfo(
            severity="critical",
            service="payment-service",
            message="Service crashed - all replicas down, 0/2 healthy",
            timestamp="2024-03-15 14:30:02",
        ),
        AlertInfo(
            severity="warning",
            service="api-server",
            message="Upstream dependency payment-service unreachable",
            timestamp="2024-03-15 14:30:10",
        ),
    ]

    return services, logs, alerts


def _gen_medium_1(services: Dict[str, ServiceInfo], seed: Optional[int] = None):
    """Medium Task 1: Database connection exhaustion causing cascading failures."""
    services["database"] = ServiceInfo(
        name="database",
        status=ServiceStatus.DEGRADED,
        cpu_usage=78.0,
        memory_usage=82.5,
        latency_ms=1200.0,
        error_rate=25.0,
        uptime_seconds=604800,
        replicas=1,
    )
    services["api-server"] = ServiceInfo(
        name="api-server",
        status=ServiceStatus.DEGRADED,
        cpu_usage=65.0,
        memory_usage=55.0,
        latency_ms=2500.0,
        error_rate=35.0,
        uptime_seconds=86400,
        replicas=2,
    )
    services["payment-service"] = ServiceInfo(
        name="payment-service",
        status=ServiceStatus.DEGRADED,
        cpu_usage=45.0,
        memory_usage=50.0,
        latency_ms=3000.0,
        error_rate=40.0,
        uptime_seconds=86400,
        replicas=2,
    )

    logs = [
        "[2024-03-15 08:00:00] database: WARNING - Connection pool nearing limit: 48/50 connections",
        "[2024-03-15 08:00:10] database: ERROR - Slow query detected: SELECT * FROM orders (1200ms)",
        "[2024-03-15 08:00:15] database: WARNING - Connection pool exhausted, queuing requests",
        "[2024-03-15 08:00:20] api-server: ERROR - Database query timeout after 2500ms",
        "[2024-03-15 08:00:25] api-server: WARNING - Thread pool saturation due to blocking DB calls",
        "[2024-03-15 08:00:30] payment-service: ERROR - Failed to process payment: DB connection timeout",
        "[2024-03-15 08:00:35] api-server: ERROR - 35% of requests failing with 504 Gateway Timeout",
        "[2024-03-15 08:00:40] auth-service: WARNING - Intermittent auth failures, DB connection delays",
        "[2024-03-15 08:00:45] frontend: WARNING - Multiple API endpoints returning errors",
        "[2024-03-15 08:01:00] cache: INFO - Cache status normal, no issues detected",
    ]

    alerts = [
        AlertInfo(
            severity="critical",
            service="database",
            message="Connection pool exhausted: 48/50 connections in use",
            timestamp="2024-03-15 08:00:15",
        ),
        AlertInfo(
            severity="critical",
            service="api-server",
            message="Error rate at 35% - cascading from database issues",
            timestamp="2024-03-15 08:00:35",
        ),
        AlertInfo(
            severity="warning",
            service="payment-service",
            message="Payment processing failures: database connection timeout",
            timestamp="2024-03-15 08:00:30",
        ),
        AlertInfo(
            severity="warning",
            service="database",
            message="Query latency at 1200ms - exceeds threshold of 100ms",
            timestamp="2024-03-15 08:00:10",
        ),
    ]

    return services, logs, alerts


def _gen_medium_2(services: Dict[str, ServiceInfo], seed: Optional[int] = None):
    """Medium Task 2: Bad deployment to frontend causing errors + high CPU on api-server."""
    services["frontend"] = ServiceInfo(
        name="frontend",
        status=ServiceStatus.DEGRADED,
        cpu_usage=70.0,
        memory_usage=65.0,
        latency_ms=400.0,
        error_rate=55.0,
        uptime_seconds=300,  # recently deployed
        replicas=2,
    )
    services["api-server"] = ServiceInfo(
        name="api-server",
        status=ServiceStatus.DEGRADED,
        cpu_usage=75.0,
        memory_usage=60.0,
        latency_ms=600.0,
        error_rate=30.0,
        uptime_seconds=86400,
        replicas=2,
    )

    logs = [
        "[2024-03-15 16:00:00] frontend: INFO - Deployment v2.4.1 completed, 2/2 replicas updated",
        "[2024-03-15 16:00:30] frontend: ERROR - Uncaught TypeError: Cannot read property 'data' of undefined",
        "[2024-03-15 16:00:35] frontend: ERROR - 500 Internal Server Error on /dashboard",
        "[2024-03-15 16:00:40] frontend: ERROR - JavaScript bundle crash, page not rendering",
        "[2024-03-15 16:01:00] api-server: WARNING - Unusual request pattern: excessive retries from frontend",
        "[2024-03-15 16:01:05] api-server: WARNING - CPU spike due to retry storm from frontend",
        "[2024-03-15 16:01:10] api-server: ERROR - Rate limiting triggered for frontend client",
        "[2024-03-15 16:01:15] frontend: ERROR - Error rate: 55%, all errors started after v2.4.1 deploy",
        "[2024-03-15 16:01:20] database: INFO - All metrics normal, no DB-related errors",
        "[2024-03-15 16:01:25] payment-service: INFO - Operating normally",
    ]

    alerts = [
        AlertInfo(
            severity="critical",
            service="frontend",
            message="Error rate at 55% after deployment v2.4.1",
            timestamp="2024-03-15 16:01:15",
        ),
        AlertInfo(
            severity="warning",
            service="api-server",
            message="CPU at 75% due to retry storm from frontend",
            timestamp="2024-03-15 16:01:05",
        ),
        AlertInfo(
            severity="info",
            service="frontend",
            message="Recent deployment: v2.4.1 deployed 5 minutes ago",
            timestamp="2024-03-15 16:00:00",
        ),
    ]

    return services, logs, alerts


def _gen_hard_1(services: Dict[str, ServiceInfo], seed: Optional[int] = None):
    """Hard Task 1: Hidden DNS failure in service-mesh causing intermittent failures."""
    # Multiple services show issues but none are the root cause
    services["api-server"] = ServiceInfo(
        name="api-server",
        status=ServiceStatus.DEGRADED,
        cpu_usage=55.0,
        memory_usage=50.0,
        latency_ms=800.0,
        error_rate=20.0,
        uptime_seconds=172800,
        replicas=2,
    )
    services["frontend"] = ServiceInfo(
        name="frontend",
        status=ServiceStatus.DEGRADED,
        cpu_usage=40.0,
        memory_usage=45.0,
        latency_ms=600.0,
        error_rate=15.0,
        uptime_seconds=172800,
        replicas=2,
    )
    services["payment-service"] = ServiceInfo(
        name="payment-service",
        status=ServiceStatus.DEGRADED,
        cpu_usage=50.0,
        memory_usage=48.0,
        latency_ms=900.0,
        error_rate=18.0,
        uptime_seconds=172800,
        replicas=2,
    )
    services["auth-service"] = ServiceInfo(
        name="auth-service",
        status=ServiceStatus.DEGRADED,
        cpu_usage=45.0,
        memory_usage=42.0,
        latency_ms=700.0,
        error_rate=22.0,
        uptime_seconds=172800,
        replicas=2,
    )
    services["service-mesh"] = ServiceInfo(
        name="service-mesh",
        status=ServiceStatus.RUNNING,  # appears healthy!
        cpu_usage=30.0,
        memory_usage=35.0,
        latency_ms=50.0,
        error_rate=2.0,
        uptime_seconds=172800,
        replicas=2,
    )

    logs = [
        "[2024-03-15 12:00:00] api-server: ERROR - Connection timeout to payment-service (intermittent)",
        "[2024-03-15 12:00:05] payment-service: ERROR - DNS resolution failed for auth-service.internal",
        "[2024-03-15 12:00:10] frontend: ERROR - Intermittent 503 errors from api-server",
        "[2024-03-15 12:00:15] auth-service: ERROR - Unexpected connection reset from database",
        "[2024-03-15 12:00:20] api-server: WARNING - Service discovery returning stale endpoints",
        "[2024-03-15 12:00:25] database: INFO - All connections healthy, latency normal",
        "[2024-03-15 12:00:30] cache: INFO - Cache hit ratio normal at 92%",
        "[2024-03-15 12:00:35] service-mesh: INFO - Proxy status: running (but DNS cache corrupted)",
        "[2024-03-15 12:00:40] payment-service: ERROR - Retrying DNS lookup for api-server.internal",
        "[2024-03-15 12:00:45] auth-service: ERROR - TLS handshake timeout (DNS-related)",
        "[2024-03-15 12:01:00] service-mesh: WARNING - DNS TTL expired, cache entries may be stale",
        "[2024-03-15 12:01:05] api-server: ERROR - Intermittent failures across multiple services",
        "[2024-03-15 12:01:10] frontend: WARNING - User reports: pages loading slowly and sometimes failing",
        "[2024-03-15 12:01:15] service-mesh: DEBUG - Internal DNS resolver last restart: 48h ago",
    ]

    alerts = [
        AlertInfo(
            severity="warning",
            service="api-server",
            message="Intermittent connection timeouts to downstream services",
            timestamp="2024-03-15 12:00:00",
        ),
        AlertInfo(
            severity="warning",
            service="payment-service",
            message="DNS resolution failures for internal services",
            timestamp="2024-03-15 12:00:05",
        ),
        AlertInfo(
            severity="warning",
            service="auth-service",
            message="Intermittent connection resets and TLS timeouts",
            timestamp="2024-03-15 12:00:15",
        ),
        AlertInfo(
            severity="info",
            service="service-mesh",
            message="DNS cache TTL warnings - stale entries possible",
            timestamp="2024-03-15 12:01:00",
        ),
    ]

    return services, logs, alerts


# =============================================================================
# Scenario Registry
# =============================================================================

SCENARIO_GENERATORS = {
    "task_easy_1": _gen_easy_1,
    "task_easy_2": _gen_easy_2,
    "task_medium_1": _gen_medium_1,
    "task_medium_2": _gen_medium_2,
    "task_hard_1": _gen_hard_1,
}

SCENARIOS = {
    "task_easy_1": Scenario(
        task_id="task_easy_1",
        difficulty="easy",
        title="High CPU & Memory Leak",
        description="The api-server is experiencing high CPU usage and memory consumption due to a memory leak. Diagnose and fix the issue.",
        root_cause="memory_leak_api_server",
        root_cause_service="api-server",
        expected_actions=[
            {"action_type": "diagnose", "target_service": "api-server"},
            {"action_type": "restart_service", "target_service": "api-server"},
        ],
        optimal_steps=2,
    ),
    "task_easy_2": Scenario(
        task_id="task_easy_2",
        difficulty="easy",
        title="Service Crash Recovery",
        description="The payment-service has crashed and all replicas are down. Identify the failed service and restore it.",
        root_cause="crash_payment_service",
        root_cause_service="payment-service",
        expected_actions=[
            {"action_type": "restart_service", "target_service": "payment-service"},
        ],
        optimal_steps=1,
    ),
    "task_medium_1": Scenario(
        task_id="task_medium_1",
        difficulty="medium",
        title="Database Connection Exhaustion Cascade",
        description="Multiple services are showing high error rates and latency. The database connection pool is exhausted, causing cascading failures across dependent services.",
        root_cause="db_connection_exhaustion",
        root_cause_service="database",
        expected_actions=[
            {"action_type": "diagnose", "target_service": "database"},
            {"action_type": "scale_up", "target_service": "database"},
            {"action_type": "restart_service", "target_service": "api-server"},
        ],
        optimal_steps=3,
    ),
    "task_medium_2": Scenario(
        task_id="task_medium_2",
        difficulty="medium",
        title="Bad Deployment Rollback",
        description="The frontend is experiencing high error rates after a recent deployment. The api-server is also showing elevated CPU due to retry storms.",
        root_cause="bad_deployment_frontend",
        root_cause_service="frontend",
        expected_actions=[
            {"action_type": "diagnose", "target_service": "frontend"},
            {"action_type": "rollback", "target_service": "frontend"},
        ],
        optimal_steps=2,
    ),
    "task_hard_1": Scenario(
        task_id="task_hard_1",
        difficulty="hard",
        title="Hidden Service Mesh DNS Failure",
        description="Multiple services are experiencing intermittent failures with connection timeouts and DNS errors. The root cause is not immediately obvious from the metrics.",
        root_cause="dns_cache_corruption_service_mesh",
        root_cause_service="service-mesh",
        expected_actions=[
            {"action_type": "check_logs", "target_service": "service-mesh"},
            {"action_type": "diagnose", "target_service": "service-mesh"},
            {"action_type": "apply_patch", "target_service": "service-mesh"},
        ],
        optimal_steps=3,
    ),
}

TASK_IDS = list(SCENARIOS.keys())
EASY_TASKS = [t for t in TASK_IDS if SCENARIOS[t].difficulty == "easy"]
MEDIUM_TASKS = [t for t in TASK_IDS if SCENARIOS[t].difficulty == "medium"]
HARD_TASKS = [t for t in TASK_IDS if SCENARIOS[t].difficulty == "hard"]


def get_scenario(task_id: str) -> Scenario:
    """Get a scenario by its task ID."""
    if task_id not in SCENARIOS:
        raise ValueError(f"Unknown task_id: {task_id}. Available: {TASK_IDS}")
    return SCENARIOS[task_id]


def get_random_task_id(difficulty: Optional[str] = None) -> str:
    """Get a random task ID, optionally filtered by difficulty."""
    if difficulty == "easy":
        return random.choice(EASY_TASKS)
    elif difficulty == "medium":
        return random.choice(MEDIUM_TASKS)
    elif difficulty == "hard":
        return random.choice(HARD_TASKS)
    return random.choice(TASK_IDS)
