"""
Typed data models for the DevOps Incident Recovery Environment.

Defines Action, Observation, and State models using Pydantic,
following the OpenEnv specification.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Action Model
# =============================================================================

class ActionType(str, Enum):
    """Available actions the agent can take."""
    DIAGNOSE = "diagnose"
    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    ROLLBACK = "rollback"
    APPLY_PATCH = "apply_patch"
    CHECK_LOGS = "check_logs"
    NO_OP = "no_op"


class DevOpsAction(BaseModel):
    """Action model for the DevOps environment.

    The agent selects an action_type and optionally targets a specific service.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    action_type: ActionType = Field(
        description="The type of action to perform"
    )
    target_service: Optional[str] = Field(
        default=None,
        description="The service to target (e.g., 'api-server', 'database')"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the action"
    )


# =============================================================================
# Observation Model
# =============================================================================

class ServiceStatus(str, Enum):
    """Status of a service."""
    RUNNING = "running"
    DEGRADED = "degraded"
    CRASHED = "crashed"
    RESTARTING = "restarting"


class ServiceInfo(BaseModel):
    """Information about a single service."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Service name")
    status: ServiceStatus = Field(description="Current status")
    cpu_usage: float = Field(description="CPU usage percentage (0-100)")
    memory_usage: float = Field(description="Memory usage percentage (0-100)")
    latency_ms: float = Field(description="Response latency in milliseconds")
    error_rate: float = Field(description="Error rate percentage (0-100)")
    uptime_seconds: int = Field(description="Seconds since last restart")
    replicas: int = Field(default=1, description="Number of running replicas")


class AlertInfo(BaseModel):
    """An active alert in the system."""
    model_config = ConfigDict(extra="forbid")

    severity: str = Field(description="Alert severity: critical, warning, info")
    service: str = Field(description="Service that triggered the alert")
    message: str = Field(description="Alert message")
    timestamp: str = Field(description="When the alert was triggered")


class DevOpsObservation(BaseModel):
    """Observation model returned by the environment.

    Contains the full state of the simulated infrastructure that
    the agent can observe.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    # Core observation fields
    services: Dict[str, ServiceInfo] = Field(
        description="Status and metrics for each service"
    )
    logs: List[str] = Field(
        default_factory=list,
        description="Recent log entries"
    )
    alerts: List[AlertInfo] = Field(
        default_factory=list,
        description="Active alerts"
    )
    timestamp: str = Field(
        description="Current simulation timestamp"
    )

    # OpenEnv required fields
    done: bool = Field(
        default=False,
        description="Whether the episode has terminated"
    )
    reward: float = Field(
        default=0.0,
        description="Reward signal from the last action"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


# =============================================================================
# State Model
# =============================================================================

class DevOpsState(BaseModel):
    """Internal state of the environment.

    Tracks episode-level information including what task is active,
    the hidden root cause, and the agent's progress.
    """
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
    )

    # OpenEnv required fields
    episode_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the current episode"
    )
    step_count: int = Field(
        default=0,
        ge=0,
        description="Number of steps taken in the current episode"
    )

    # DevOps-specific state
    task_id: str = Field(
        default="",
        description="ID of the current task"
    )
    difficulty: str = Field(
        default="easy",
        description="Difficulty level: easy, medium, hard"
    )
    root_cause: str = Field(
        default="",
        description="The hidden root cause of the incident"
    )
    resolved: bool = Field(
        default=False,
        description="Whether the incident has been resolved"
    )
    diagnosed: bool = Field(
        default=False,
        description="Whether the agent has correctly diagnosed the issue"
    )
    actions_taken: List[str] = Field(
        default_factory=list,
        description="History of actions taken by the agent"
    )
    correct_actions_taken: int = Field(
        default=0,
        description="Number of correct actions taken"
    )
    wrong_actions_taken: int = Field(
        default=0,
        description="Number of wrong actions taken"
    )
    max_steps: int = Field(
        default=15,
        description="Maximum steps before episode ends"
    )
