"""
Deterministic graders for the DevOps Incident Recovery Environment.

Each grader scores an agent's performance on a task from 0.0 to 1.0.
Scores are NOT constant — they vary based on the agent's exact action
sequence, timing, and diagnosis accuracy.

Scoring breakdown:
  - Correctness (0.0–0.50): Did the agent fix the root cause?
  - Efficiency  (0.0–0.30): How many steps? (fewer = better)
  - Diagnosis   (0.0–0.20): Did the agent diagnose before acting?
"""

from typing import Dict, List, Optional


def grade_task(
    task_id: str,
    actions_taken: List[str],
    step_count: int,
    resolved: bool,
    diagnosed: bool,
    correct_actions_taken: int,
    wrong_actions_taken: int,
    optimal_steps: int,
    max_steps: int,
) -> Dict[str, float]:
    """Grade an agent's performance on a task.

    Args:
        task_id: ID of the task being graded
        actions_taken: List of "action_type:target_service" strings
        step_count: Total steps taken
        resolved: Whether the incident was resolved
        diagnosed: Whether the agent diagnosed correctly
        correct_actions_taken: Number of correct actions
        wrong_actions_taken: Number of wrong actions
        optimal_steps: Optimal number of steps for this task
        max_steps: Maximum allowed steps

    Returns:
        Dict with 'total', 'correctness', 'efficiency', 'diagnosis' scores
    """
    # --- Correctness Score (0.0 – 0.50) ---
    correctness = 0.0
    if resolved:
        correctness = 0.50
    elif correct_actions_taken > 0:
        # Partial credit for correct actions even if not fully resolved
        correctness = min(0.30, correct_actions_taken * 0.15)

    # Penalize wrong actions
    if wrong_actions_taken > 0:
        penalty = min(0.15, wrong_actions_taken * 0.05)
        correctness = max(0.0, correctness - penalty)

    # --- Efficiency Score (0.0 – 0.30) ---
    efficiency = 0.0
    if resolved:
        if step_count <= optimal_steps:
            efficiency = 0.30  # Perfect efficiency
        elif step_count <= optimal_steps + 2:
            efficiency = 0.25  # Close to optimal
        elif step_count <= optimal_steps + 4:
            efficiency = 0.15  # Acceptable
        elif step_count <= max_steps // 2:
            efficiency = 0.10  # Below average
        else:
            efficiency = 0.05  # Inefficient but got there
    elif correct_actions_taken > 0:
        # Some credit if partially correct
        efficiency = 0.05

    # --- Diagnosis Score (0.0 – 0.20) ---
    diagnosis_score = 0.0
    if diagnosed:
        diagnosis_score = 0.15
        # Bonus if diagnosed early (first 3 steps)
        diagnose_actions = [a for a in actions_taken if a.startswith("diagnose:")]
        check_log_actions = [a for a in actions_taken if a.startswith("check_logs:")]
        if diagnose_actions or check_log_actions:
            # Find earliest diagnostic step
            earliest_diag = len(actions_taken)
            for i, a in enumerate(actions_taken):
                if a.startswith("diagnose:") or a.startswith("check_logs:"):
                    earliest_diag = i
                    break
            if earliest_diag <= 1:
                diagnosis_score = 0.20  # Diagnosed very early
            elif earliest_diag <= 3:
                diagnosis_score = 0.17  # Diagnosed early enough
    elif any(a.startswith("check_logs:") for a in actions_taken):
        # Partial credit for at least checking logs
        diagnosis_score = 0.05

    total = round(correctness + efficiency + diagnosis_score, 4)
    total = min(0.99, max(0.01, total))

    return {
        "total": total,
        "correctness": min(0.99, max(0.01, round(correctness, 4))),
        "efficiency": min(0.99, max(0.01, round(efficiency, 4))),
        "diagnosis": min(0.99, max(0.01, round(diagnosis_score, 4))),
        "task_id": task_id,
        "steps_taken": step_count,
        "optimal_steps": optimal_steps,
        "resolved": resolved,
        "diagnosed": diagnosed,
    }


def grade_easy_1(actions_taken, step_count, resolved, diagnosed,
                  correct_actions, wrong_actions) -> Dict[str, float]:
    """Grade Easy Task 1: High CPU / Memory Leak on api-server."""
    return grade_task(
        task_id="task_easy_1",
        actions_taken=actions_taken,
        step_count=step_count,
        resolved=resolved,
        diagnosed=diagnosed,
        correct_actions_taken=correct_actions,
        wrong_actions_taken=wrong_actions,
        optimal_steps=2,
        max_steps=15,
    )


def grade_easy_2(actions_taken, step_count, resolved, diagnosed,
                  correct_actions, wrong_actions) -> Dict[str, float]:
    """Grade Easy Task 2: Payment Service Crash."""
    return grade_task(
        task_id="task_easy_2",
        actions_taken=actions_taken,
        step_count=step_count,
        resolved=resolved,
        diagnosed=diagnosed,
        correct_actions_taken=correct_actions,
        wrong_actions_taken=wrong_actions,
        optimal_steps=1,
        max_steps=15,
    )


def grade_medium_1(actions_taken, step_count, resolved, diagnosed,
                    correct_actions, wrong_actions) -> Dict[str, float]:
    """Grade Medium Task 1: Database Connection Exhaustion."""
    return grade_task(
        task_id="task_medium_1",
        actions_taken=actions_taken,
        step_count=step_count,
        resolved=resolved,
        diagnosed=diagnosed,
        correct_actions_taken=correct_actions,
        wrong_actions_taken=wrong_actions,
        optimal_steps=3,
        max_steps=15,
    )


def grade_medium_2(actions_taken, step_count, resolved, diagnosed,
                    correct_actions, wrong_actions) -> Dict[str, float]:
    """Grade Medium Task 2: Bad Deployment Rollback."""
    return grade_task(
        task_id="task_medium_2",
        actions_taken=actions_taken,
        step_count=step_count,
        resolved=resolved,
        diagnosed=diagnosed,
        correct_actions_taken=correct_actions,
        wrong_actions_taken=wrong_actions,
        optimal_steps=2,
        max_steps=15,
    )


def grade_hard_1(actions_taken, step_count, resolved, diagnosed,
                  correct_actions, wrong_actions) -> Dict[str, float]:
    """Grade Hard Task 1: Hidden Service Mesh DNS Failure."""
    return grade_task(
        task_id="task_hard_1",
        actions_taken=actions_taken,
        step_count=step_count,
        resolved=resolved,
        diagnosed=diagnosed,
        correct_actions_taken=correct_actions,
        wrong_actions_taken=wrong_actions,
        optimal_steps=3,
        max_steps=15,
    )


# Registry mapping task IDs to grader functions
GRADERS = {
    "task_easy_1": grade_easy_1,
    "task_easy_2": grade_easy_2,
    "task_medium_1": grade_medium_1,
    "task_medium_2": grade_medium_2,
    "task_hard_1": grade_hard_1,
}


def get_grader(task_id: str):
    """Get the grader function for a task ID."""
    if task_id not in GRADERS:
        raise ValueError(f"No grader for task: {task_id}")
    return GRADERS[task_id]
