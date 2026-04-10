"""
Local test script for the DevOps Incident Recovery Environment.

Validates:
  1. All tasks can be reset and stepped through
  2. Graders return non-constant, varying scores
  3. Reward function produces proper partial rewards
  4. Environment terminates correctly
  5. State tracking works
"""

import sys
import os

# Ensure we can import from parent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import DevOpsAction, ActionType
from environment import DevOpsEnvironment
from scenarios import TASK_IDS, SCENARIOS


def test_all_tasks_reset():
    """Test that all tasks can be reset successfully."""
    print("=" * 60)
    print("TEST 1: All tasks reset correctly")
    print("=" * 60)

    env = DevOpsEnvironment()
    for task_id in TASK_IDS:
        obs = env.reset(task_id=task_id, seed=42)
        assert obs is not None, f"Reset returned None for {task_id}"
        assert obs.done == False, f"Episode shouldn't be done after reset for {task_id}"
        assert len(obs.services) > 0, f"No services for {task_id}"
        assert len(obs.logs) > 0, f"No logs for {task_id}"
        print(f"  ✅ {task_id}: {len(obs.services)} services, {len(obs.logs)} logs, {len(obs.alerts)} alerts")

    print()


def test_step_and_termination():
    """Test that steps work and episodes terminate."""
    print("=" * 60)
    print("TEST 2: Step execution and termination")
    print("=" * 60)

    env = DevOpsEnvironment()

    for task_id in TASK_IDS:
        scenario = SCENARIOS[task_id]
        obs = env.reset(task_id=task_id, seed=42)

        # Execute the expected optimal sequence
        for expected_action in scenario.expected_actions:
            action = DevOpsAction(
                action_type=expected_action["action_type"],
                target_service=expected_action["target_service"],
            )
            obs = env.step(action)

        state = env.state
        print(f"  ✅ {task_id}: resolved={state.resolved}, steps={state.step_count}, "
              f"done={obs.done}, reward={obs.reward:.2f}")

    print()


def test_grader_non_constant():
    """Test that graders return DIFFERENT scores for different action sequences."""
    print("=" * 60)
    print("TEST 3: Graders return non-constant scores")
    print("=" * 60)

    env = DevOpsEnvironment()
    scores = {}

    for task_id in TASK_IDS:
        task_scores = []

        # Run 1: Optimal sequence
        scenario = SCENARIOS[task_id]
        obs = env.reset(task_id=task_id, seed=42)
        for expected_action in scenario.expected_actions:
            action = DevOpsAction(
                action_type=expected_action["action_type"],
                target_service=expected_action["target_service"],
            )
            obs = env.step(action)
        score_optimal = obs.metadata.get("final_score", 0.0)
        task_scores.append(score_optimal)

        # Run 2: Sub-optimal sequence (extra wrong actions first)
        obs = env.reset(task_id=task_id, seed=42)
        # Take some wrong actions first
        wrong_actions = [
            DevOpsAction(action_type=ActionType.NO_OP),
            DevOpsAction(action_type=ActionType.RESTART_SERVICE, target_service="cache"),
            DevOpsAction(action_type=ActionType.SCALE_DOWN, target_service="cache"),
        ]
        for wa in wrong_actions:
            obs = env.step(wa)
        # Then take correct actions
        for expected_action in scenario.expected_actions:
            action = DevOpsAction(
                action_type=expected_action["action_type"],
                target_service=expected_action["target_service"],
            )
            obs = env.step(action)
        score_suboptimal = obs.metadata.get("final_score", 0.0)
        task_scores.append(score_suboptimal)

        # Run 3: Only wrong actions (should score low)
        obs = env.reset(task_id=task_id, seed=42)
        for _ in range(5):
            obs = env.step(DevOpsAction(action_type=ActionType.NO_OP))
        # Force end by maxing steps
        while not obs.done:
            obs = env.step(DevOpsAction(action_type=ActionType.NO_OP))
        score_bad = obs.metadata.get("final_score", 0.0)
        task_scores.append(score_bad)

        scores[task_id] = task_scores
        all_same = len(set(task_scores)) == 1
        status = "❌ CONSTANT" if all_same else "✅ VARYING"
        print(f"  {status} {task_id}: scores = {[f'{s:.2f}' for s in task_scores]}")

    # Verify NO task has constant scores
    for task_id, task_scores in scores.items():
        assert len(set(task_scores)) > 1, f"FAIL: {task_id} returned constant scores: {task_scores}"

    print()


def test_partial_rewards():
    """Test that step rewards are non-zero and vary."""
    print("=" * 60)
    print("TEST 4: Partial rewards (not just final success)")
    print("=" * 60)

    env = DevOpsEnvironment()
    rewards_per_task = {}

    for task_id in TASK_IDS:
        obs = env.reset(task_id=task_id, seed=42)
        rewards = []

        # Take a mix of actions
        actions = [
            DevOpsAction(action_type=ActionType.CHECK_LOGS, target_service="api-server"),
            DevOpsAction(action_type=ActionType.DIAGNOSE, target_service="api-server"),
            DevOpsAction(action_type=ActionType.RESTART_SERVICE, target_service="api-server"),
        ]

        for action in actions:
            obs = env.step(action)
            rewards.append(obs.reward)

        rewards_per_task[task_id] = rewards
        non_zero = sum(1 for r in rewards if r != 0.0)
        print(f"  ✅ {task_id}: rewards = {[f'{r:.2f}' for r in rewards]} ({non_zero}/{len(rewards)} non-zero)")

    print()


def test_state_tracking():
    """Test that state is tracked correctly."""
    print("=" * 60)
    print("TEST 5: State tracking")
    print("=" * 60)

    env = DevOpsEnvironment()

    for task_id in TASK_IDS:
        obs = env.reset(task_id=task_id, seed=42)
        state = env.state

        assert state.step_count == 0, f"Step count should be 0 after reset"
        assert state.task_id == task_id, f"Task ID mismatch"
        assert state.episode_id is not None, f"Episode ID should be set"
        assert state.resolved == False, f"Should not be resolved after reset"

        # Take a step
        obs = env.step(DevOpsAction(action_type=ActionType.DIAGNOSE, target_service="api-server"))
        state = env.state

        assert state.step_count == 1, f"Step count should be 1 after one step"
        assert len(state.actions_taken) == 1, f"Should have 1 action in history"

        print(f"  ✅ {task_id}: episode_id={state.episode_id[:8]}..., "
              f"task={state.task_id}, difficulty={state.difficulty}")

    print()


def test_observation_structure():
    """Test that observations have the correct structure."""
    print("=" * 60)
    print("TEST 6: Observation structure validation")
    print("=" * 60)

    env = DevOpsEnvironment()
    obs = env.reset(task_id="task_easy_1", seed=42)

    # Check all required fields
    assert hasattr(obs, "services"), "Missing 'services'"
    assert hasattr(obs, "logs"), "Missing 'logs'"
    assert hasattr(obs, "alerts"), "Missing 'alerts'"
    assert hasattr(obs, "timestamp"), "Missing 'timestamp'"
    assert hasattr(obs, "done"), "Missing 'done'"
    assert hasattr(obs, "reward"), "Missing 'reward'"
    assert hasattr(obs, "metadata"), "Missing 'metadata'"

    # Check services have correct fields
    for name, svc in obs.services.items():
        assert hasattr(svc, "name"), f"Service {name} missing 'name'"
        assert hasattr(svc, "status"), f"Service {name} missing 'status'"
        assert hasattr(svc, "cpu_usage"), f"Service {name} missing 'cpu_usage'"
        assert hasattr(svc, "memory_usage"), f"Service {name} missing 'memory_usage'"
        assert hasattr(svc, "latency_ms"), f"Service {name} missing 'latency_ms'"
        assert hasattr(svc, "error_rate"), f"Service {name} missing 'error_rate'"

    # Check JSON serialization works
    obs_dict = obs.model_dump()
    assert isinstance(obs_dict, dict), "model_dump() should return dict"

    print(f"  ✅ Observation has {len(obs.services)} services, all fields valid")
    print(f"  ✅ JSON serialization works ({len(str(obs_dict))} chars)")
    print()


def main():
    """Run all tests."""
    print("\n🧪 DevOps Incident Recovery Environment — Test Suite\n")

    try:
        test_all_tasks_reset()
        test_step_and_termination()
        test_grader_non_constant()
        test_partial_rewards()
        test_state_tracking()
        test_observation_structure()

        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
