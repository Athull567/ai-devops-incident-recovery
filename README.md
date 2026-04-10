# 🔧 Autonomous AI DevOps Incident Recovery Environment

> An OpenEnv-compatible AI training environment that simulates real-world cloud infrastructure failures. An AI agent must analyze system metrics, logs, and alerts to diagnose root causes and take corrective actions.

[![OpenEnv Compatible](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green)](https://python.org)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 Table of Contents

- [Project Description](#-project-description)
- [Real-World Motivation](#-real-world-motivation)
- [Environment Design](#-environment-design)
- [Observation Space](#-observation-space)
- [Action Space](#-action-space)
- [Reward Design](#-reward-design)
- [Tasks (Easy → Hard)](#-tasks-easy--hard)
- [Setup Instructions](#-setup-instructions)
- [Run Instructions](#-run-instructions)
- [Baseline Results](#-baseline-results)
- [Deployment Guide](#-deployment-guide-hugging-face)

---

## 🎯 Project Description

This environment simulates a **production cloud infrastructure** with 7 interconnected services. Failures are injected — from simple service crashes to complex cascading incidents with hidden root causes. An AI agent must:

1. **Observe** system metrics (CPU, memory, latency, error rates), logs, and alerts
2. **Diagnose** the root cause by analyzing patterns across services
3. **Act** by restarting services, scaling infrastructure, rolling back deployments, or applying patches
4. **Resolve** the incident efficiently with minimal unnecessary actions

The environment follows the [OpenEnv specification](https://github.com/meta-pytorch/OpenEnv) with `step()`, `reset()`, and `state()` APIs.

---

## 🌍 Real-World Motivation

Cloud infrastructure failures cost enterprises **$300B+ annually** (Gartner, 2024). Site Reliability Engineers (SREs) spend significant time diagnosing and resolving incidents. This environment trains AI agents to:

- **Reduce Mean Time to Resolution (MTTR)** from hours to minutes
- **Identify cascading failures** that humans often misdiagnose
- **Automate routine incident response** while escalating complex issues

Real-world parallels:
| Our Simulation | Real-World Equivalent |
|---|---|
| Service crash recovery | PagerDuty auto-remediation |
| Database connection exhaustion | AWS RDS connection pool scaling |
| Bad deployment rollback | Kubernetes rollback policies |
| Service mesh DNS failure | Istio/Envoy troubleshooting |

---

## 🏗️ Environment Design

### Architecture

```
┌─────────────────────────────────────────────────┐
│              AI Agent (LLM / RL)                │
│         Observes → Diagnoses → Acts             │
└──────────┬──────────────────────┬───────────────┘
           │ POST /step           │ POST /reset
           ▼                      ▼
┌─────────────────────────────────────────────────┐
│           FastAPI Server (app.py)                │
│     /health  /reset  /step  /state  /tasks      │
└──────────┬──────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│        DevOpsEnvironment (environment.py)        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Scenarios │  │ Rewards  │  │   Graders    │  │
│  │ (5 tasks) │  │ (per-step│  │ (0.0 - 1.0)  │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
└──────────┬──────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│          Simulated Infrastructure                │
│  ┌──────────┐ ┌─────────┐ ┌───────────────┐    │
│  │api-server│→│database │ │payment-service│    │
│  └──────────┘ └─────────┘ └───────────────┘    │
│  ┌──────────┐ ┌─────────┐ ┌───────────────┐    │
│  │ frontend │ │  cache  │ │ auth-service  │    │
│  └──────────┘ └─────────┘ └───────────────┘    │
│  ┌──────────────┐                               │
│  │ service-mesh │ (routes traffic between all)   │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

### Service Dependency Graph

```
frontend → api-server → database
                      → cache
                      → auth-service → database
                                     → cache
payment-service → api-server → database
service-mesh → all services (DNS routing)
```

### Key Features

- **Cascading failures**: Fixing the root cause heals dependent services
- **Metric drift**: Unfixed issues worsen over time (creates time pressure)
- **Realistic logs**: Timestamped, varied log messages with red herrings
- **Service dependencies**: Failures propagate through the dependency graph
- **Action validation**: Prevents impossible actions (e.g., scaling a crashed service)

---

## 👁️ Observation Space

Each observation contains:

| Field | Type | Description |
|-------|------|-------------|
| `services` | `Dict[str, ServiceInfo]` | Status & metrics for all 7 services |
| `logs` | `List[str]` | Last 20 timestamped log entries |
| `alerts` | `List[AlertInfo]` | Active alerts (critical/warning/info) |
| `timestamp` | `str` | Current simulation timestamp (ISO format) |
| `done` | `bool` | Whether the episode has ended |
| `reward` | `float` | Reward from the last action |
| `metadata` | `Dict` | Task info, grade, action results |

### ServiceInfo Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `name` | `str` | — | Service identifier |
| `status` | `enum` | running/degraded/crashed/restarting | Current status |
| `cpu_usage` | `float` | 0–100% | CPU utilization |
| `memory_usage` | `float` | 0–100% | Memory utilization |
| `latency_ms` | `float` | 0+ ms | Response latency |
| `error_rate` | `float` | 0–100% | Percentage of failed requests |
| `uptime_seconds` | `int` | 0+ | Time since last restart |
| `replicas` | `int` | 0+ | Number of running instances |

---

## 🎮 Action Space

| Action | Description | When to Use |
|--------|-------------|------------|
| `diagnose` | Investigate a service for root cause | First step — confirm the problem |
| `check_logs` | Examine detailed logs for a service | Gather more diagnostic info |
| `restart_service` | Restart a service (clears state) | Memory leaks, crashes |
| `scale_up` | Add replicas to handle load | Connection exhaustion, high load |
| `scale_down` | Remove replicas | Over-provisioned resources |
| `rollback` | Revert to previous deployment version | Bad deployments |
| `apply_patch` | Apply a hotfix to a service | Configuration issues, DNS bugs |
| `no_op` | Do nothing | Not recommended (penalized) |

**Action format:**
```json
{
  "action_type": "restart_service",
  "target_service": "api-server"
}
```

---

## 💰 Reward Design

The reward system provides **partial credit throughout the episode**, not just at final success:

| Signal | Reward | Purpose |
|--------|--------|---------|
| Correct diagnosis | +0.15 | Encourage investigation first |
| Correct fix action | +0.30 | Reward proper remediation |
| Incident resolved | +0.40 | Terminal success bonus |
| Useful log check | +0.05 | Encourage using logs |
| Wrong action target | −0.10 | Penalize incorrect actions |
| Unnecessary action | −0.05 | Penalize wasted effort |
| Each step taken | −0.02 | Encourage efficiency |
| No-op (idle) | −0.03 | Penalize inaction |
| Repeated action | −0.08 | Penalize redundancy |

**Design principles:**
- ✅ Non-zero rewards at every step (not just 0/1 at end)
- ✅ Partial credit for partially correct solutions
- ✅ Time pressure via step cost + metric drift
- ✅ Diagnostic actions rewarded (not just fix actions)

---

## 📝 Tasks (Easy → Hard)

### 🟢 Easy — Task 1: High CPU & Memory Leak
- **Scenario**: `api-server` has 92% CPU, 88% memory, leaking
- **Signal**: Single service, obvious metrics
- **Solution**: Diagnose → Restart api-server
- **Optimal Steps**: 2

### 🟢 Easy — Task 2: Service Crash Recovery
- **Scenario**: `payment-service` crashed (0 replicas)
- **Signal**: Clear "FATAL" logs, service shows 100% error rate
- **Solution**: Restart payment-service
- **Optimal Steps**: 1

### 🟡 Medium — Task 3: Database Connection Cascade
- **Scenario**: Database connection pool exhausted → API timeouts → payment failures
- **Signal**: Multiple degraded services, need to find root cause
- **Solution**: Diagnose database → Scale up database → Restart api-server
- **Optimal Steps**: 3

### 🟡 Medium — Task 4: Bad Deployment Rollback
- **Scenario**: Frontend deployed buggy v2.4.1 → retry storm → api-server CPU spike
- **Signal**: Recent deployment timestamp, correlated errors
- **Solution**: Diagnose frontend → Rollback frontend
- **Optimal Steps**: 2

### 🔴 Hard — Task 5: Hidden Service Mesh DNS Failure
- **Scenario**: Corrupted DNS cache in `service-mesh` causes intermittent failures everywhere
- **Signal**: Misleading errors across all services, service-mesh appears "running"
- **Signal**: DNS-related log clues buried in noise
- **Solution**: Check logs → Diagnose service-mesh → Apply patch
- **Optimal Steps**: 3

---

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Local Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd devops-incident-recovery

# Install dependencies
pip install -r requirements.txt

# Run tests to verify everything works
python test_env.py
```

### Docker Setup

```bash
# Build the Docker image
docker build -t devops-recovery-env .

# Run the container
docker run -p 8000:8000 devops-recovery-env

# Verify it's running
curl http://localhost:8000/health
```

---

## ▶️ Run Instructions

### 1. Start the Environment Server

```bash
# Local
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Or with Docker
docker run -p 8000:8000 devops-recovery-env
```

### 2. Interact via API

```bash
# Health check
curl http://localhost:8000/health

# List tasks
curl http://localhost:8000/tasks

# Reset with a specific task
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_easy_1"}'

# Take an action
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"action_type": "diagnose", "target_service": "api-server"}}'

# Get current state
curl http://localhost:8000/state
```

### 3. Run Baseline Inference

```bash
# With LLM (set environment variables)
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-3.5-turbo"
export OPENAI_API_KEY="your-key"
python inference.py

# Without LLM (uses rule-based agent)
python inference.py
```

---

## 📊 Baseline Results

Results using the **rule-based fallback agent** (no LLM):

| Task | Difficulty | Score | Steps | Resolved |
|------|-----------|-------|-------|----------|
| task_easy_1 | 🟢 Easy | 1.00 | 2 | ✅ Yes |
| task_easy_2 | 🟢 Easy | 0.80 | 1 | ✅ Yes |
| task_medium_1 | 🟡 Medium | 1.00 | 3 | ✅ Yes |
| task_medium_2 | 🟡 Medium | 1.00 | 2 | ✅ Yes |
| task_hard_1 | 🔴 Hard | 1.00 | 3 | ✅ Yes |

**Average Score: 0.96 / 1.00**

Grader score breakdown example (task_easy_1, optimal run):
- Correctness: 0.50 / 0.50
- Efficiency: 0.30 / 0.30
- Diagnosis: 0.20 / 0.20

---

## 🚀 Deployment Guide (Hugging Face)

### Step 1: Create a Hugging Face Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Choose:
   - **Space name**: `devops-incident-recovery`
   - **SDK**: Docker
   - **Visibility**: Public
3. Add tags: `openenv`

### Step 2: Push Code

```bash
# Install git-lfs (if needed)
git lfs install

# Clone the HF Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/devops-incident-recovery
cd devops-incident-recovery

# Copy all project files
cp -r /path/to/ai_agent/* .

# Push
git add .
git commit -m "Initial OpenEnv deployment"
git push
```

### Step 3: Configure Environment Variables

In the HF Space Settings, add:
- `HF_TOKEN`: Your Hugging Face token
- `API_BASE_URL`: LLM API endpoint (e.g., `https://api.openai.com/v1`)
- `MODEL_NAME`: Model name (e.g., `gpt-3.5-turbo`)

### Step 4: Verify

```bash
# Health check (should return 200)
curl https://YOUR_USERNAME-devops-incident-recovery.hf.space/health

# Test reset
curl -X POST https://YOUR_USERNAME-devops-incident-recovery.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_easy_1"}'
```

---

## 📁 Project Structure

```
ai_agent/
├── openenv.yaml           # OpenEnv manifest
├── pyproject.toml          # Package configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container definition
├── README.md               # This file
├── inference.py            # Baseline inference script
├── test_env.py             # Test suite
├── models.py               # Action, Observation, State (Pydantic)
├── environment.py          # Core DevOpsEnvironment class
├── scenarios.py            # 5 task scenario definitions
├── graders.py              # Deterministic task graders
├── rewards.py              # Per-step reward function
└── server/
    ├── __init__.py
    └── app.py              # FastAPI HTTP server
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
