# 🔧 Autonomous AI DevOps Incident Recovery Environment

> **Revolutionizing Site Reliability Engineering through Agentic AI.**
> An OpenEnv-compliant simulation platform for training and evaluating next-generation SRE Agents in high-consequence cloud environments.

[![OpenEnv Compatible](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green)](https://python.org)
[![Hugging Face Space](https://img.shields.io/badge/Deployed-Hugging%20Face-pink)](https://huggingface.co/spaces/athul890ak/devops-incident-recovery)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🚀 The Corporate Vision: Autonomous SRE
In modern enterprise environments, cloud infrastructure downtime costs an average of **$5,600 per minute**. Traditional rule-based monitoring is no longer sufficient for complex microservice architectures. 

**Our Solution** provides a high-fidelity "Wargame" environment where AI Agents can:
*   **Reduce MTTR (Mean Time to Resolution)** by diagnosing multi-service cascades in seconds.
*   **Automate Tier-1 & Tier-2 response**, freeing human engineers for high-level architecture.
*   **Benchmarking Performance**: Quantifiably measure which LLM (Llama 3, Qwen, etc.) is most reliable for production operations.

---

## 🏗️ System Architecture
The environment simulates a 7-service microservice stack with real-world complexities:
*   **Metric Drift**: Problems escalate if left unaddressed.
*   **Cascading Failures**: A database bottleneck manifests as high CPU in the API layer—testing the agent's ability to see past "Red Herrings."
*   **Realistic Observability**: Agents must parse timestamped logs, analyze telemetry, and correlate alerts—just like a human engineer.

---

## 🛠️ Technical Engineering: Overcoming Evaluation Hurdles
Building an environment for the **Meta x OpenEnv Hackathon** required solving several deep technical challenges to ensure absolute reliability during automated evaluation:

### 1. The Strict (0.01 - 0.99) Score Perimeter
The OpenEnv validator requires task scores to be strictly between 0 and 1. We implemented a **Rigid Clamping Module** in `graders.py` that mathematically ensures every sub-metric and the final total are always within the safe zone, preventing any "out of range" disqualifications.

### 2. Cumulative Reward Sum Stabilization
Standard RL validators often sum step rewards. We refactored `environment.py` into a **Sparse Terminal Reward** model:
*   **Intermediate Steps**: Yield exactly `0.0001` (to satisfy "strictly positive" requirements while remaining negligible).
*   **Terminal Step**: Yields the full, clamped grader score.
This ensures the cumulative sum perfectly reflects the intended task grade without calculation overflow.

### 3. Native Grader Parsing
To handle AST-level validator inspections, we injected a native `"score"` key into all grader return dictionaries, ensuring the platform's internal Python checks never fall back to `0.0` due to missing keys.

---

## 👁️ Observation & Action Spaces
### Observation Space
| Component | Type | Description |
|---|---|---|
| `services` | `Dict` | Real-time CPU, RAM, Latency, and Error rates. |
| `logs` | `List` | Last 20 system log lines (with diagnostic clues). |
| `alerts` | `List` | Critical/Warning alerts from the infrastructure. |

### Action Space
| Action | Purpose |
|---|---|
| `diagnose` | Formalize root cause identification (Rewarded). |
| `scale_up/down` | Resource optimization for connection exhaustion. |
| `restart_service` | Recovery from memory leaks or process crashes. |
| `rollback` | Remediation of bad deployments. |
| `apply_patch` | Fixing deep-seated config/DNS issues.|

---

## 📝 Incident Scenarios
We provide 5 diverse tasks ranging from simple to "Frontier Specialist" difficulty:
1.  **🟢 High CPU Leak**: Immediate corrective action needed for `api-server`.
2.  **🟢 Service Crash**: Restoration of `payment-service` replicas.
3.  **🟡 DB Connection Cascade**: Multi-service failure requiring horizontal scaling.
4.  **🟡 Bad Deployment**: Rolling back a buggy frontend to stabilize the API retry-storm.
5.  **🔴 Mesh DNS Corruption**: A hidden failure in the `service-mesh` proxy—testing the limit of log analysis.

---

## ⚙️ Quick Start

### 1. Local Run
```bash
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### 2. Docker Execution
```bash
docker build -t devops-env .
docker run -p 7860:7860 devops-env
```

### 3. Baseline Validation
```bash
python inference.py
```

---

## 📁 Repository Structure
*   `environment.py`: Core simulation logic.
*   `graders.py`: Robust, clamped scoring engine.
*   `inference.py`: Zero-dependency Hackathon-spec baseline.
*   `scenarios.py`: Configurable incident definitions.
*   `server/app.py`: Standardized FastAPI endpoints.

---
**Developed for the Meta x Pytorch x SST x OpenEnv Challenge.**
