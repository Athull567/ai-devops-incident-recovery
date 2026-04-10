"""Quick API test for the running server."""
import requests
import json

BASE = "http://localhost:8000"

# Test 1: Health
r = requests.get(f"{BASE}/health")
print(f"Health: {r.status_code} -> {r.json()}")

# Test 2: Tasks
r = requests.get(f"{BASE}/tasks")
tasks = r.json()
print(f"Tasks: {len(tasks['tasks'])} tasks")
for t in tasks["tasks"]:
    print(f"  {t['task_id']}: {t['title']} ({t['difficulty']})")

# Test 3: Reset
r = requests.post(f"{BASE}/reset", json={"task_id": "task_easy_1"})
data = r.json()
print(f"Reset: {r.status_code}, done={data['done']}, reward={data['reward']}")
svc_names = list(data["observation"]["services"].keys())
print(f"  Services: {svc_names}")

# Test 4: Step - diagnose
r = requests.post(f"{BASE}/step", json={"action": {"action_type": "diagnose", "target_service": "api-server"}})
data = r.json()
print(f"Step 1 (diagnose): reward={data['reward']}, done={data['done']}")

# Test 5: Step - restart
r = requests.post(f"{BASE}/step", json={"action": {"action_type": "restart_service", "target_service": "api-server"}})
data = r.json()
print(f"Step 2 (restart): reward={data['reward']}, done={data['done']}")
if data["done"]:
    grade = data["observation"]["metadata"].get("grade", {})
    print(f"  Final score: {grade.get('total', 'N/A')}")
    print(f"  Correctness: {grade.get('correctness', 'N/A')}")
    print(f"  Efficiency: {grade.get('efficiency', 'N/A')}")
    print(f"  Diagnosis: {grade.get('diagnosis', 'N/A')}")

# Test 6: State
r = requests.get(f"{BASE}/state")
state = r.json()
print(f"State: task={state['task_id']}, steps={state['step_count']}, resolved={state['resolved']}")

# Test 7: Schema
r = requests.get(f"{BASE}/schema")
schema = r.json()
print(f"Schema: action fields={list(schema['action']['properties'].keys())}")

print("\nAll API endpoints working!")
