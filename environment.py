"""
Core DevOps Incident Recovery Environment.

Implements the OpenEnv Environment interface with reset(), step(), and state().
Simulates cloud infrastructure failures that an AI agent must diagnose and fix.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models import (
    ActionType,
    AlertInfo,
    DevOpsAction,
    DevOpsObservation,
    DevOpsState,
    ServiceInfo,
    ServiceStatus,
)
from scenarios import (
    ALL_SERVICES,
    SCENARIOS,
    TASK_IDS,
    get_random_task_id,
    get_scenario,
)
from rewards import calculate_step_reward
from graders import get_grader


class DevOpsEnvironment:
    """Autonomous AI DevOps Incident Recovery Environment.

    Simulates real-world cloud system failures. An AI agent must analyze
    system metrics and logs, identify root causes, and take corrective actions.

    Usage:
        env = DevOpsEnvironment()
        obs = env.reset(task_id="task_easy_1")
        obs = env.step(DevOpsAction(action_type="diagnose", target_service="api-server"))
        state = env.state
    """

    def __init__(self):
        """Initialize the environment."""
        self._state = DevOpsState(episode_id=str(uuid4()), step_count=0)
        self._services: Dict[str, ServiceInfo] = {}
        self._logs: List[str] = []
        self._alerts: List[AlertInfo] = []
        self._scenario = None
        self._sim_time = datetime(2024, 3, 15, 10, 0, 0)
        self._total_reward = 0.0
        self._done = False

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DevOpsObservation:
        """Reset the environment and start a new incident scenario.

        Args:
            seed: Optional random seed for reproducibility
            episode_id: Optional custom episode ID
            task_id: Optional task ID to load a specific scenario.
                     If None, a random task is chosen.

        Returns:
            Initial observation of the environment
        """
        if seed is not None:
            random.seed(seed)

        # Select scenario
        if task_id and task_id in SCENARIOS:
            selected_task = task_id
        elif task_id:
            raise ValueError(f"Unknown task_id: {task_id}. Available: {TASK_IDS}")
        else:
            selected_task = get_random_task_id()

        self._scenario = get_scenario(selected_task)

        # Initialize state
        self._state = DevOpsState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=selected_task,
            difficulty=self._scenario.difficulty,
            root_cause=self._scenario.root_cause,
            resolved=False,
            diagnosed=False,
            actions_taken=[],
            correct_actions_taken=0,
            wrong_actions_taken=0,
            max_steps=15,
        )

        # Generate initial infrastructure state
        initial_state = self._scenario.generate_initial_state(seed)
        self._services = initial_state["services"]
        self._logs = initial_state["logs"]
        self._alerts = initial_state["alerts"]
        self._sim_time = datetime(2024, 3, 15, 10, 0, 0)
        self._total_reward = 0.0
        self._done = False

        return self._build_observation(reward=0.0001, done=False, info={
            "message": f"Incident detected! Task: {self._scenario.title}",
            "task_id": selected_task,
            "difficulty": self._scenario.difficulty,
            "description": self._scenario.description,
            "available_actions": [a.value for a in ActionType],
            "available_services": list(self._services.keys()),
        })

    def step(
        self,
        action: DevOpsAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> DevOpsObservation:
        """Execute an action and return the resulting observation.

        Args:
            action: The DevOpsAction to execute
            timeout_s: Optional timeout (unused)

        Returns:
            Observation with updated metrics, logs, reward, and done flag
        """
        if self._done:
            return self._build_observation(
                reward=0.0, done=True,
                info={"error": "Episode already ended. Call reset() to start a new one."}
            )

        if self._scenario is None:
            return self._build_observation(
                reward=0.0, done=False,
                info={"error": "Environment not initialized. Call reset() first."}
            )

        # Increment step count
        self._state.step_count += 1

        # Advance simulation time
        self._sim_time += timedelta(seconds=30)

        # Get action details
        action_type = action.action_type.value if isinstance(action.action_type, ActionType) else action.action_type
        target_service = action.target_service

        # Build services status dict for reward calculation
        services_status = {
            name: svc.status.value if isinstance(svc.status, ServiceStatus) else svc.status
            for name, svc in self._services.items()
        }

        # Calculate reward
        reward, newly_diagnosed, newly_resolved, reward_info = calculate_step_reward(
            action_type=action_type,
            target_service=target_service,
            root_cause_service=self._scenario.root_cause_service,
            expected_actions=self._scenario.expected_actions,
            actions_taken=self._state.actions_taken,
            diagnosed=self._state.diagnosed,
            resolved=self._state.resolved,
            step_count=self._state.step_count,
            services_status=services_status,
        )

        # Update state
        action_str = f"{action_type}:{target_service or 'none'}"
        self._state.actions_taken.append(action_str)

        if newly_diagnosed:
            self._state.diagnosed = True
        if newly_resolved:
            self._state.resolved = True

        # Track correct/wrong actions
        is_expected = any(
            ea["action_type"] == action_type and ea.get("target_service") == target_service
            for ea in self._scenario.expected_actions
        )
        if is_expected:
            self._state.correct_actions_taken += 1
        elif action_type not in [ActionType.DIAGNOSE.value, ActionType.CHECK_LOGS.value, ActionType.NO_OP.value]:
            self._state.wrong_actions_taken += 1

        # Apply action effects to the simulated infrastructure
        action_result = self._apply_action_effects(action_type, target_service)

        # Add log entry for the action
        time_str = self._sim_time.strftime("%Y-%m-%d %H:%M:%S")
        self._logs.append(
            f"[{time_str}] AGENT: Executed {action_type} on {target_service or 'system'}"
        )
        if action_result.get("message"):
            self._logs.append(f"[{time_str}] SYSTEM: {action_result['message']}")

        # Apply metric drift (things get worse if not fixed)
        if not self._state.resolved:
            self._apply_metric_drift()

        # Update total reward
        self._total_reward += reward

        # Check termination conditions
        done = False
        if self._state.resolved:
            done = True
            self._logs.append(f"[{time_str}] SYSTEM: ✅ Incident resolved successfully!")
        elif self._state.step_count >= self._state.max_steps:
            done = True
            self._logs.append(f"[{time_str}] SYSTEM: ❌ Maximum steps reached. Episode ended.")

        self._done = done

        # Build info
        info = {
            "action_executed": action_str,
            "action_result": action_result,
            "reward_info": reward_info,
            "total_reward": round(self._total_reward, 4),
            "steps_remaining": self._state.max_steps - self._state.step_count,
        }

        if done:
            # Run grader
            grader = get_grader(self._state.task_id)
            grade = grader(
                actions_taken=self._state.actions_taken,
                step_count=self._state.step_count,
                resolved=self._state.resolved,
                diagnosed=self._state.diagnosed,
                correct_actions=self._state.correct_actions_taken,
                wrong_actions=self._state.wrong_actions_taken,
            )
            info["grade"] = grade
            info["final_score"] = grade["total"]
            info["score"] = grade["total"]  # Ensure standard OpenEnv score key
            
            # Emit the full bounded score as the only reward in the episode
            step_return_reward = grade["total"]
        else:
            # Emit tiny non-zero reward for intermediate steps to prevent exact 0.0 match
            step_return_reward = 0.0001

        return self._build_observation(reward=step_return_reward, done=done, info=info)

    @property
    def state(self) -> DevOpsState:
        """Get the current environment state."""
        return self._state

    def close(self):
        """Clean up resources."""
        pass

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _build_observation(self, reward: float, done: bool, info: Dict[str, Any]) -> DevOpsObservation:
        """Build an observation from current state."""
        return DevOpsObservation(
            services=dict(self._services),
            logs=list(self._logs[-20:]),  # Last 20 log entries
            alerts=list(self._alerts),
            timestamp=self._sim_time.isoformat(),
            done=done,
            reward=round(reward, 4),
            metadata=info,
        )

    def _apply_action_effects(self, action_type: str, target_service: Optional[str]) -> Dict[str, Any]:
        """Apply the effects of an action to the simulated infrastructure."""
        result = {"success": False, "message": ""}

        if action_type == ActionType.NO_OP.value:
            result["message"] = "No action taken."
            result["success"] = True
            return result

        if action_type == ActionType.CHECK_LOGS.value:
            result["success"] = True
            if target_service and target_service in self._services:
                result["message"] = f"Reviewed logs for {target_service}."
                # Add extra diagnostic logs for the target service
                time_str = self._sim_time.strftime("%Y-%m-%d %H:%M:%S")
                svc = self._services[target_service]
                self._logs.append(
                    f"[{time_str}] {target_service}: DEBUG - Status: {svc.status.value}, "
                    f"CPU: {svc.cpu_usage}%, MEM: {svc.memory_usage}%, "
                    f"LAT: {svc.latency_ms}ms, ERR: {svc.error_rate}%"
                )
            else:
                result["message"] = f"Service {target_service} not found."
                result["success"] = False
            return result

        if action_type == ActionType.DIAGNOSE.value:
            result["success"] = True
            if target_service == self._scenario.root_cause_service:
                result["message"] = (
                    f"Diagnosis confirmed: Root cause identified in {target_service}. "
                    f"Issue: {self._scenario.root_cause}"
                )
            else:
                result["message"] = (
                    f"Diagnosis of {target_service}: No root cause found here. "
                    f"This service may be affected by an upstream issue."
                )
            return result

        if not target_service or target_service not in self._services:
            result["message"] = f"Invalid target service: {target_service}"
            return result

        if action_type == ActionType.RESTART_SERVICE.value:
            svc = self._services[target_service]
            if target_service == self._scenario.root_cause_service or svc.status != ServiceStatus.RUNNING:
                # Restarting the correct or crashed service
                self._services[target_service] = ServiceInfo(
                    name=target_service,
                    status=ServiceStatus.RUNNING,
                    cpu_usage=round(random.uniform(5, 20), 1),
                    memory_usage=round(random.uniform(20, 40), 1),
                    latency_ms=round(random.uniform(10, 50), 1),
                    error_rate=round(random.uniform(0.0, 1.0), 2),
                    uptime_seconds=0,
                    replicas=svc.replicas if svc.replicas > 0 else 2,
                )
                result["success"] = True
                result["message"] = f"Service {target_service} restarted successfully. Metrics normalizing."
            else:
                result["success"] = True
                result["message"] = f"Service {target_service} restarted (was already healthy)."

        elif action_type == ActionType.SCALE_UP.value:
            svc = self._services[target_service]
            new_replicas = svc.replicas + 1
            self._services[target_service] = ServiceInfo(
                name=target_service,
                status=ServiceStatus.RUNNING if svc.status != ServiceStatus.CRASHED else ServiceStatus.CRASHED,
                cpu_usage=max(5.0, svc.cpu_usage * 0.6),
                memory_usage=max(10.0, svc.memory_usage * 0.7),
                latency_ms=max(10.0, svc.latency_ms * 0.5),
                error_rate=max(0.0, svc.error_rate * 0.4),
                uptime_seconds=svc.uptime_seconds,
                replicas=new_replicas,
            )
            result["success"] = True
            result["message"] = f"Scaled {target_service} to {new_replicas} replicas. Load distributed."

        elif action_type == ActionType.SCALE_DOWN.value:
            svc = self._services[target_service]
            new_replicas = max(1, svc.replicas - 1)
            self._services[target_service] = ServiceInfo(
                name=target_service,
                status=svc.status,
                cpu_usage=min(100, svc.cpu_usage * 1.3),
                memory_usage=min(100, svc.memory_usage * 1.2),
                latency_ms=svc.latency_ms * 1.5,
                error_rate=min(100, svc.error_rate * 1.4),
                uptime_seconds=svc.uptime_seconds,
                replicas=new_replicas,
            )
            result["success"] = True
            result["message"] = f"Scaled down {target_service} to {new_replicas} replicas."

        elif action_type == ActionType.ROLLBACK.value:
            svc = self._services[target_service]
            self._services[target_service] = ServiceInfo(
                name=target_service,
                status=ServiceStatus.RUNNING,
                cpu_usage=round(random.uniform(10, 25), 1),
                memory_usage=round(random.uniform(25, 45), 1),
                latency_ms=round(random.uniform(15, 60), 1),
                error_rate=round(random.uniform(0.0, 1.5), 2),
                uptime_seconds=0,
                replicas=svc.replicas,
            )
            result["success"] = True
            result["message"] = f"Rolled back {target_service} to previous version. Service recovering."

        elif action_type == ActionType.APPLY_PATCH.value:
            svc = self._services[target_service]
            self._services[target_service] = ServiceInfo(
                name=target_service,
                status=ServiceStatus.RUNNING,
                cpu_usage=round(random.uniform(8, 22), 1),
                memory_usage=round(random.uniform(20, 40), 1),
                latency_ms=round(random.uniform(10, 45), 1),
                error_rate=round(random.uniform(0.0, 0.5), 2),
                uptime_seconds=0,
                replicas=svc.replicas,
            )
            result["success"] = True
            result["message"] = f"Applied hotfix patch to {target_service}. Issue corrected."

        # If we fixed the root cause, also fix cascading issues
        if result["success"] and target_service == self._scenario.root_cause_service:
            self._heal_cascading_services()

        return result

    def _heal_cascading_services(self):
        """After fixing root cause, gradually heal affected services."""
        for name, svc in self._services.items():
            if name != self._scenario.root_cause_service:
                if svc.status == ServiceStatus.DEGRADED:
                    self._services[name] = ServiceInfo(
                        name=name,
                        status=ServiceStatus.RUNNING,
                        cpu_usage=max(5.0, svc.cpu_usage * 0.5),
                        memory_usage=max(10.0, svc.memory_usage * 0.6),
                        latency_ms=max(10.0, svc.latency_ms * 0.3),
                        error_rate=max(0.0, svc.error_rate * 0.2),
                        uptime_seconds=svc.uptime_seconds,
                        replicas=svc.replicas,
                    )

    def _apply_metric_drift(self):
        """Make metrics worse over time if issues aren't fixed (time pressure)."""
        for name, svc in self._services.items():
            if svc.status in [ServiceStatus.DEGRADED, ServiceStatus.CRASHED]:
                # Degraded services get slightly worse each step
                drift = random.uniform(1.01, 1.08)
                self._services[name] = ServiceInfo(
                    name=name,
                    status=svc.status,
                    cpu_usage=min(100, round(svc.cpu_usage * drift, 1)),
                    memory_usage=min(100, round(svc.memory_usage * drift, 1)),
                    latency_ms=round(svc.latency_ms * drift, 1),
                    error_rate=min(100, round(svc.error_rate * drift, 2)),
                    uptime_seconds=svc.uptime_seconds + 30,
                    replicas=svc.replicas,
                )

                # Add warning logs periodically
                if self._state.step_count % 3 == 0:
                    time_str = self._sim_time.strftime("%Y-%m-%d %H:%M:%S")
                    self._logs.append(
                        f"[{time_str}] {name}: WARNING - Metrics worsening. "
                        f"CPU: {self._services[name].cpu_usage}%, "
                        f"Errors: {self._services[name].error_rate}%"
                    )
