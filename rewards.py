"""
Reward function for the DevOps Incident Recovery Environment.

Provides per-step rewards based on action correctness, efficiency,
and diagnosis quality. Rewards are NOT just final-success — they
give partial credit throughout the episode.
"""

from typing import Dict, List, Optional
from models import ActionType


# =============================================================================
# Reward Constants
# =============================================================================

REWARD_CORRECT_DIAGNOSIS = 0.15       # Agent correctly diagnosed the root cause
REWARD_CORRECT_FIX = 0.30            # Agent took the correct fix action
REWARD_RESOLUTION_BONUS = 0.40       # Terminal bonus when incident is fully resolved
REWARD_CHECK_LOGS_USEFUL = 0.05      # Checked logs on a relevant service
REWARD_CHECK_LOGS_IRRELEVANT = -0.02 # Checked logs on an irrelevant service

PENALTY_WRONG_ACTION = -0.10         # Wrong action (restart healthy service, etc.)
PENALTY_UNNECESSARY = -0.05          # Action on a healthy service
PENALTY_STEP_COST = -0.02           # Small penalty per step (encourages efficiency)
PENALTY_NO_OP = -0.03              # Doing nothing when action is needed
PENALTY_REPEATED_ACTION = -0.08    # Repeating the same action


def calculate_step_reward(
    action_type: str,
    target_service: Optional[str],
    root_cause_service: str,
    expected_actions: List[Dict[str, str]],
    actions_taken: List[str],
    diagnosed: bool,
    resolved: bool,
    step_count: int,
    services_status: Dict[str, str],
) -> tuple:
    """Calculate the reward for a single step.

    Args:
        action_type: The action type taken by the agent
        target_service: The service targeted by the action
        root_cause_service: The actual root cause service
        expected_actions: List of expected {action_type, target_service} dicts
        actions_taken: History of actions already taken (as "action:target" strings)
        diagnosed: Whether the agent has already diagnosed correctly
        resolved: Whether the incident is now resolved
        step_count: Current step number
        services_status: Dict of service_name -> status string

    Returns:
        Tuple of (reward: float, newly_diagnosed: bool, newly_resolved: bool, info: dict)
    """
    reward = 0.0
    info = {"reward_breakdown": {}}
    newly_diagnosed = False
    newly_resolved = False

    # Step cost (always applied)
    reward += PENALTY_STEP_COST
    info["reward_breakdown"]["step_cost"] = PENALTY_STEP_COST

    # Build action string for history checking
    action_str = f"{action_type}:{target_service or 'none'}"

    # Check for repeated action
    if action_str in actions_taken:
        reward += PENALTY_REPEATED_ACTION
        info["reward_breakdown"]["repeated_action"] = PENALTY_REPEATED_ACTION
        return reward, newly_diagnosed, newly_resolved, info

    # Handle NO_OP
    if action_type == ActionType.NO_OP.value or action_type == ActionType.NO_OP:
        reward += PENALTY_NO_OP
        info["reward_breakdown"]["no_op"] = PENALTY_NO_OP
        return reward, newly_diagnosed, newly_resolved, info

    # Check if target service exists
    if target_service and target_service not in services_status:
        reward += PENALTY_WRONG_ACTION
        info["reward_breakdown"]["invalid_target"] = PENALTY_WRONG_ACTION
        return reward, newly_diagnosed, newly_resolved, info

    # --- Diagnose Action ---
    if action_type == ActionType.DIAGNOSE.value or action_type == ActionType.DIAGNOSE:
        if target_service == root_cause_service:
            reward += REWARD_CORRECT_DIAGNOSIS
            info["reward_breakdown"]["correct_diagnosis"] = REWARD_CORRECT_DIAGNOSIS
            newly_diagnosed = True
        else:
            # Diagnosing wrong service — small penalty
            reward += -0.03
            info["reward_breakdown"]["wrong_diagnosis_target"] = -0.03
        return reward, newly_diagnosed, newly_resolved, info

    # --- Check Logs Action ---
    if action_type == ActionType.CHECK_LOGS.value or action_type == ActionType.CHECK_LOGS:
        if target_service == root_cause_service:
            reward += REWARD_CHECK_LOGS_USEFUL
            info["reward_breakdown"]["useful_log_check"] = REWARD_CHECK_LOGS_USEFUL
        else:
            reward += REWARD_CHECK_LOGS_IRRELEVANT
            info["reward_breakdown"]["irrelevant_log_check"] = REWARD_CHECK_LOGS_IRRELEVANT
        return reward, newly_diagnosed, newly_resolved, info

    # --- Fix Actions (restart, scale_up, scale_down, rollback, apply_patch) ---
    is_fix_action = action_type in [
        ActionType.RESTART_SERVICE.value, ActionType.SCALE_UP.value,
        ActionType.SCALE_DOWN.value, ActionType.ROLLBACK.value,
        ActionType.APPLY_PATCH.value,
        ActionType.RESTART_SERVICE, ActionType.SCALE_UP,
        ActionType.SCALE_DOWN, ActionType.ROLLBACK,
        ActionType.APPLY_PATCH,
    ]

    if is_fix_action:
        # Check if this action matches any expected action
        action_type_str = action_type if isinstance(action_type, str) else action_type.value
        is_expected = any(
            ea["action_type"] == action_type_str and ea["target_service"] == target_service
            for ea in expected_actions
        )

        if is_expected:
            reward += REWARD_CORRECT_FIX
            info["reward_breakdown"]["correct_fix"] = REWARD_CORRECT_FIX

            # Check if all expected actions have now been taken
            all_expected_taken = True
            updated_actions = actions_taken + [action_str]
            for ea in expected_actions:
                ea_str = f"{ea['action_type']}:{ea['target_service']}"
                if ea_str not in updated_actions:
                    # Also check diagnose actions since they're optional for some tasks
                    if ea["action_type"] != "diagnose":
                        all_expected_taken = False
                        break

            if all_expected_taken:
                reward += REWARD_RESOLUTION_BONUS
                info["reward_breakdown"]["resolution_bonus"] = REWARD_RESOLUTION_BONUS
                newly_resolved = True
        else:
            # Check if the target service is actually unhealthy
            target_status = services_status.get(target_service, "running")
            if target_status in ["running"] and target_service != root_cause_service:
                reward += PENALTY_UNNECESSARY
                info["reward_breakdown"]["unnecessary_action"] = PENALTY_UNNECESSARY
            else:
                # Action on a degraded/crashed service that isn't root cause
                # Might help partially but isn't the correct fix
                reward += -0.03
                info["reward_breakdown"]["partially_useful"] = -0.03

    return reward, newly_diagnosed, newly_resolved, info
