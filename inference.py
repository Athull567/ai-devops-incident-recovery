"""
Baseline Inference Script for the DevOps Incident Recovery Environment.

Uses an OpenAI-compatible LLM to interact with the environment.
Reads configuration from environment variables:
  - API_BASE_URL: Base URL for the OpenAI-compatible API
  - MODEL_NAME: Model to use for inference
  - HF_TOKEN: Hugging Face token for authentication

Output format (STRICT):
  [START] task=... env=... model=...
  [STEP] step=... action=... reward=... done=... error=...
  [END] success=... steps=... rewards=...
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Any, Optional

# Try to import openai, but allow running without it for testing
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    OpenAI = None  # type: ignore
    HAS_OPENAI = False
    print("WARNING: openai package not installed. Install with: pip install openai", file=sys.stderr)


# =============================================================================
# Configuration
# =============================================================================

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional - if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

ENV_NAME = "devops_incident_recovery"
MAX_STEPS = 15


# =============================================================================
# Environment Client (HTTP)
# =============================================================================

class EnvClient:
    """Simple HTTP client for the DevOps environment (zero dependencies)."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def health(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/health")
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception:
            return False

    def reset(self, task_id: str, seed: Optional[int] = None) -> dict:
        payload = {"task_id": task_id}
        if seed is not None:
            payload["seed"] = seed
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f"{self.base_url}/reset", data=data, 
                                     headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")

    def step(self, action_type: str, target_service: Optional[str] = None) -> dict:
        payload = {
            "action": {
                "action_type": action_type,
                "target_service": target_service,
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(f"{self.base_url}/step", data=data, 
                                     headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")

    def get_tasks(self) -> list:
        req = urllib.request.Request(f"{self.base_url}/tasks")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                tasks_data = json.loads(response.read().decode('utf-8'))
                return tasks_data.get("tasks", [])
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")


# =============================================================================
# LLM Agent
# =============================================================================

SYSTEM_PROMPT = """You are an expert DevOps Site Reliability Engineer (SRE) AI agent.
You are investigating a cloud infrastructure incident. You must analyze the system metrics,
logs, and alerts to identify the root cause and take corrective actions.

Available actions:
- diagnose: Investigate a specific service to identify root cause
- restart_service: Restart a service to clear its state
- scale_up: Add more replicas to handle load
- scale_down: Remove replicas
- rollback: Roll back a service to its previous version
- apply_patch: Apply a hotfix patch to a service
- check_logs: Examine detailed logs for a service
- no_op: Do nothing (not recommended)

You must respond with EXACTLY one JSON object like:
{"action_type": "<action>", "target_service": "<service_name>"}

Strategy:
1. First, analyze the metrics and alerts to identify which service is problematic
2. Use diagnose or check_logs to confirm the root cause
3. Apply the appropriate fix action
4. Be efficient — minimize unnecessary actions

Think step by step, but only output the JSON action."""


def format_observation_for_llm(obs_data: dict, step_num: int) -> str:
    """Format the observation data into a readable prompt for the LLM."""
    obs = obs_data.get("observation", obs_data)

    prompt_parts = [f"=== Step {step_num} - Current System State ===\n"]

    # Services
    services = obs.get("services", {})
    prompt_parts.append("SERVICES:")
    for name, svc in services.items():
        if isinstance(svc, dict):
            status = svc.get("status", "unknown")
            cpu = svc.get("cpu_usage", 0)
            mem = svc.get("memory_usage", 0)
            lat = svc.get("latency_ms", 0)
            err = svc.get("error_rate", 0)
            reps = svc.get("replicas", 0)
            prompt_parts.append(
                f"  {name}: status={status}, CPU={cpu}%, MEM={mem}%, "
                f"latency={lat}ms, errors={err}%, replicas={reps}"
            )

    # Alerts
    alerts = obs.get("alerts", [])
    if alerts:
        prompt_parts.append("\nALERTS:")
        for alert in alerts:
            if isinstance(alert, dict):
                prompt_parts.append(
                    f"  [{alert.get('severity', 'info').upper()}] {alert.get('service', '?')}: "
                    f"{alert.get('message', '')}"
                )

    # Recent logs
    logs = obs.get("logs", [])
    if logs:
        prompt_parts.append(f"\nRECENT LOGS (last {min(10, len(logs))}):")
        for log in logs[-10:]:
            prompt_parts.append(f"  {log}")

    # Metadata
    metadata = obs.get("metadata", {})
    if "description" in metadata:
        prompt_parts.insert(1, f"\nINCIDENT: {metadata['description']}\n")
    if "steps_remaining" in metadata:
        prompt_parts.append(f"\nSteps remaining: {metadata['steps_remaining']}")

    return "\n".join(prompt_parts)


def get_llm_action(client: Any, observation_text: str) -> dict:
    """Call the LLM to decide on an action."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": observation_text},
            ],
            temperature=0.1,
            max_tokens=200,
        )

        content = response.choices[0].message.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Find JSON object in content
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)

        return {"action_type": "no_op", "target_service": None}

    except Exception as e:
        print(f"  LLM error: {e}", file=sys.stderr)
        return {"action_type": "no_op", "target_service": None}


# =============================================================================
# Fallback Rule-Based Agent (when no LLM available)
# =============================================================================

def get_rule_based_action(obs_data: dict, step_num: int, actions_taken: list) -> dict:
    """Smarter rule-based agent that analyzes alerts and logs for clues."""
    obs = obs_data.get("observation", obs_data)
    services = obs.get("services", {})
    alerts = obs.get("alerts", [])
    logs = obs.get("logs", [])
    log_text = " ".join(logs).lower()
    alert_text = " ".join(
        a.get("message", "") for a in alerts if isinstance(a, dict)
    ).lower()

    # --- Heuristic 1: Detect DNS / service-mesh issue ---
    dns_clues = ["dns resolution", "dns cache", "dns ttl", "stale endpoint", "service discovery"]
    if any(clue in log_text or clue in alert_text for clue in dns_clues):
        mesh_key = "check_logs:service-mesh"
        diag_key = "diagnose:service-mesh"
        patch_key = "apply_patch:service-mesh"
        if mesh_key not in actions_taken:
            return {"action_type": "check_logs", "target_service": "service-mesh"}
        if diag_key not in actions_taken:
            return {"action_type": "diagnose", "target_service": "service-mesh"}
        if patch_key not in actions_taken:
            return {"action_type": "apply_patch", "target_service": "service-mesh"}

    # --- Heuristic 2: Detect connection pool / database root cause ---
    db_clues = ["connection pool", "pool exhausted", "pool nearing", "db connection"]
    if any(clue in log_text or clue in alert_text for clue in db_clues):
        diag_key = "diagnose:database"
        scale_key = "scale_up:database"
        if diag_key not in actions_taken:
            return {"action_type": "diagnose", "target_service": "database"}
        if scale_key not in actions_taken:
            return {"action_type": "scale_up", "target_service": "database"}
        # After fixing DB, restart dependent services
        restart_api = "restart_service:api-server"
        if restart_api not in actions_taken:
            return {"action_type": "restart_service", "target_service": "api-server"}

    # --- Heuristic 3: Detect bad deployment ---
    deploy_clues = ["deployment", "deployed", "after v", "deploy"]
    if any(clue in log_text or clue in alert_text for clue in deploy_clues):
        # Find recently deployed service (low uptime)
        for name, svc in services.items():
            if isinstance(svc, dict):
                uptime = svc.get("uptime_seconds", 99999)
                err = svc.get("error_rate", 0)
                if uptime < 600 and err > 20:
                    diag_key = f"diagnose:{name}"
                    roll_key = f"rollback:{name}"
                    if diag_key not in actions_taken:
                        return {"action_type": "diagnose", "target_service": name}
                    if roll_key not in actions_taken:
                        return {"action_type": "rollback", "target_service": name}

    # --- Default: score-based approach for remaining cases ---
    worst_service = None
    worst_score = 0

    for name, svc in services.items():
        if isinstance(svc, dict):
            score = 0
            status = svc.get("status", "running")
            if status == "crashed":
                score += 100
            elif status == "degraded":
                score += 50
            score += svc.get("cpu_usage", 0) * 0.3
            score += svc.get("error_rate", 0) * 0.5
            score += min(100, svc.get("latency_ms", 0) / 10) * 0.2
            if score > worst_score:
                worst_score = score
                worst_service = name

    if not worst_service:
        return {"action_type": "no_op", "target_service": None}

    svc = services.get(worst_service, {})
    status = svc.get("status", "running") if isinstance(svc, dict) else "running"

    # Diagnose first
    diag_key = f"diagnose:{worst_service}"
    if diag_key not in actions_taken and step_num <= 2:
        return {"action_type": "diagnose", "target_service": worst_service}

    # Crashed → restart
    restart_key = f"restart_service:{worst_service}"
    if status == "crashed" and restart_key not in actions_taken:
        return {"action_type": "restart_service", "target_service": worst_service}

    # Recently deployed → rollback
    uptime = svc.get("uptime_seconds", 99999) if isinstance(svc, dict) else 99999
    rollback_key = f"rollback:{worst_service}"
    if uptime < 600 and rollback_key not in actions_taken:
        return {"action_type": "rollback", "target_service": worst_service}

    # High CPU → restart
    cpu = svc.get("cpu_usage", 0) if isinstance(svc, dict) else 0
    if cpu > 70 and restart_key not in actions_taken:
        return {"action_type": "restart_service", "target_service": worst_service}

    # High latency → scale up
    scale_key = f"scale_up:{worst_service}"
    latency = svc.get("latency_ms", 0) if isinstance(svc, dict) else 0
    if latency > 500 and scale_key not in actions_taken:
        return {"action_type": "scale_up", "target_service": worst_service}

    # Check logs
    logs_key = f"check_logs:{worst_service}"
    if logs_key not in actions_taken:
        return {"action_type": "check_logs", "target_service": worst_service}

    # Apply patch
    patch_key = f"apply_patch:{worst_service}"
    if patch_key not in actions_taken:
        return {"action_type": "apply_patch", "target_service": worst_service}

    # Restart
    if restart_key not in actions_taken:
        return {"action_type": "restart_service", "target_service": worst_service}

    return {"action_type": "no_op", "target_service": None}


# =============================================================================
# Main Inference Loop
# =============================================================================

def run_inference():
    """Run inference over all tasks."""
    env_client = EnvClient(ENV_BASE_URL)

    # Check health
    if not env_client.health():
        print(f"ERROR: Environment at {ENV_BASE_URL} is not healthy!", file=sys.stderr)
        sys.exit(1)

    # Initialize LLM client if available
    llm_client = None
    use_llm = HAS_OPENAI and API_BASE_URL and MODEL_NAME

    if use_llm:
        try:
            llm_client = OpenAI(
                base_url=API_BASE_URL,
                api_key=HF_TOKEN or "dummy",
            )
            print(f"Using LLM: {MODEL_NAME} at {API_BASE_URL}", file=sys.stderr)
        except Exception as e:
            print(f"LLM init failed: {e}. Using rule-based agent.", file=sys.stderr)
            use_llm = False

    if not use_llm:
        print("Using rule-based fallback agent.", file=sys.stderr)

    # Get available tasks
    try:
        tasks = env_client.get_tasks()
    except Exception:
        tasks = [{"task_id": tid} for tid in [
            "task_easy_1", "task_easy_2", "task_medium_1", "task_medium_2", "task_hard_1"
        ]]

    model_name = MODEL_NAME if use_llm else "rule_based_agent"

    # Run each task
    for task_info in tasks:
        task_id = task_info["task_id"]
        actions_taken = []

        # Print START line
        print(f"[START] task={task_id} env={ENV_NAME} model={model_name}")

        try:
            # Reset environment
            obs_data = env_client.reset(task_id=task_id, seed=42)
            total_reward = 0.0
            done = False
            step_num = 0
            error_str = "none"

            while not done and step_num < MAX_STEPS:
                step_num += 1

                # Decide action
                if use_llm and llm_client:
                    obs_text = format_observation_for_llm(obs_data, step_num)
                    action = get_llm_action(llm_client, obs_text)
                else:
                    action = get_rule_based_action(obs_data, step_num, actions_taken)

                action_type = action.get("action_type", "no_op")
                target = action.get("target_service", "none")
                action_str = f"{action_type}:{target}"
                actions_taken.append(action_str)

                # Execute step
                try:
                    obs_data = env_client.step(action_type, target if target != "none" else None)
                    reward = obs_data.get("reward", 0.0)
                    done = obs_data.get("done", False)
                    total_reward += reward
                    error_str = "none"
                except Exception as e:
                    reward = 0.0
                    error_str = str(e).replace("\n", " ")[:100]

                # Print STEP line
                done_str = "true" if done else "false"
                print(f"[STEP] step={step_num} action={action_str} reward={reward:.2f} done={done_str} error={error_str}")

            # Print END line
            success = obs_data.get("observation", {}).get("metadata", {}).get("grade", {}).get("resolved", False) if done else False
            success_str = "true" if success else "false"
            print(f"[END] success={success_str} steps={step_num} rewards={total_reward:.2f}")

        except Exception as e:
            # Always print END line even on error
            print(f"[STEP] step=0 action=error:none reward=0.00 done=true error={str(e)[:100]}")
            print(f"[END] success=false steps=0 rewards=0.00")

    print("\n--- Inference complete ---", file=sys.stderr)


if __name__ == "__main__":
    run_inference()
