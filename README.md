<div align="center">

# 🔧 **AUTONOMOUS AI DEVOPS INCIDENT RECOVERY** 🔧

## *Revolutionizing Site Reliability Engineering through Agentic AI* 🚀

<br>

[![OpenEnv Compatible](https://img.shields.io/badge/OpenEnv-Compatible-2E86AB?logo=meta&logoColor=white&style=for-the-badge)](https://github.com/meta-pytorch/OpenEnv)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green?logo=python&logoColor=white&style=for-the-badge)](https://python.org)
[![Hugging Face Space](https://img.shields.io/badge/🤗_HuggingFace-Live_Space-pink?style=for-the-badge)](https://huggingface.co/spaces/athul890ak/devops-incident-recovery)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white&style=for-the-badge)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

### 🎯 *Advanced SRE Simulation for Frontier LLM Evaluation*

✨ **Train AI agents to diagnose and fix cascading microservice failures**  
🌍 *High-fidelity simulation of enterprise cloud incidents*  
⚡ *OpenEnv Phase 2 compliant with zero-risk scoring*

</div>

<br>

---

## 🚀 **Quick Navigation**

<div align="center">

| 📖 | 🏗️ | 📝 | 🔌 |
|:--:|:--:|:--:|:--:|
| [**About**](#-about-this-project) | [**Architecture**](#-system-architecture) | [**Scenarios**](#-incident-scenarios) | [**Setup**](#-quick-setup) |

</div>

---

## 📋 **About This Project**

<div align="left">

> ### 💡 **The Corporate Challenge**
> 
> In modern enterprise environments, downtime costs an average of **$5,600 per minute**. Traditional monitoring isn't enough for microservices.
>
> **Your mission?** Deploy AI Agents that can **Reduce MTTR** (Mean Time to Resolution) by diagnosing complex service cascades in seconds, freeing human engineers for higher-level architecture. 🛠️

### 🌟 Why This Matters

- 🚨 **Industrial Context**: Direct application to Site Reliability Engineering (SRE)
- 🤖 **Reasoning over Math**: Tests an LLM's ability to deduce causes from logs—not just solve graph puzzles
- 🌐 **Cascading Failures**: Realistic simulation where one service's health affects the entire stack
- 📈 **Validator Resilience**: Engineered with strict range-clamping to ensure 100% success on automated gates
- 🧠 **Observability**: Agents must parse timestamped logs and correlate alerts just like real humans

</div>

---

## ⚡ **Key Features**

<table align="center">
<tr>
<td align="center" width="33%">

### 🤖 5 Incident Levels
Easy → Medium → Hard  
Progressive difficulty

</td>
<td align="center" width="33%">

### 🧠 3-Vector Grader
Correctness, Efficiency, & Diagnosis  
Comprehensive rubrics

</td>
<td align="center" width="33%">

### 👁️ Observability
7 Unified Services  
Real-time Logs & Alerts

</td>
</tr>
<tr>
<td align="center" width="33%">

### 🔌 Full APIs
FastAPI Endpoints  
Port 7860 Compliant

</td>
<td align="center" width="33%">

### 🐳 Docker Ready
One-click deployment  
Production-grade build

</td>
<td align="center" width="33%">

### ⚖️ Clamped Scoring
Rigid (0.01 - 0.99) Perimeter  
No "out of range" errors

</td>
</tr>
</table>

---

## 🏗️ **System Architecture**

The environment simulates a 7-service microservice stack with real-world complexities:
- **Metric Drift**: Problems escalate over time if left unaddressed.
- **Cascading Failures**: A database bottleneck manifests as high CPU in the API layer—testing "Red Herring" detection.
- **Realistic Interface**: Agents interact through structured JSON actions (Restart, Scale, Patch, Rollback).

---

## 💻 **Quick Setup**

### 📦 Installation (2 Minutes)

```bash
# 1️⃣ Clone and enter
git clone <your-repo-url>
cd ai_agent

# 2️⃣ Install dependencies
pip install -r requirements.txt
```

### ▶️ Run Locally

```bash
# Start the FastAPI server (Standard Port 7860)
uvicorn server.app:app --host 0.0.0.0 --port 7860

# 📊 Run the baseline inference
python inference.py
```

### 🐳 Docker Deployment

```bash
# Build and Run
docker build -t devops-env .
docker run -p 7860:7860 devops-env
```

---

## 📝 **Incident Scenarios**

### 🟢 **EASY: Resource Leaks**
- **High CPU Leak**: Immediate corrective action needed for `api-server`.
- **Service Crash**: Restoration of `payment-service` replicas.

### 🟡 **MEDIUM: Service Cascades**
- **DB Connection Exhaustion**: Requires vertical diagnosis and horizontal scaling.
- **Bad Deployment**: Rolling back a buggy frontend before logs are flooded.

### 🔴 **HARD: Frontier Challenges**
- **Mesh DNS Corruption**: A hidden failure in the proxy layer—testing the absolute limit of log analysis.

---

## 🔌 **API Reference**

### 📡 **Standard Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Server heartbeat |
| `GET` | `/tasks` | List incident scenarios |
| `POST` | `/reset` | Start new incident episode |
| `POST` | `/step` | Execute SRE action |
| `GET` | `/state` | Full infrastructure dump |

---

## 📊 **Reward & Scoring Logic**

```
Reward = Σ (Correct_Action_Weight) 
         - (Step_Penalty) 
         - (Wrong_Action_Penalty)
```

**[STRICT COMPLIANCE]**: Our scoring engine ensures intermediate step rewards are exactly `0.0001` and final scores are clamped to `(0.01, 0.99)` to satisfy all OpenEnv validator constraints.

---

## 📁 **Project Structure**

```
📦 ai-devops-agent/
│
├── 🧠 server/                    # FastAPI Infrastructure
│   ├── app.py                    # Main API Server
│   └── ...                       
│
├── ⚙️ Core Modules
│   ├── environment.py            # Simulation Logic
│   ├── graders.py                # Clamped Scoring Engine
│   ├── scenarios.py              # Task Definitions
│   ├── models.py                 # Pydantic Schemas
│   └── rewards.py                # Reward Shaping
│
├── 📋 Configuration
│   ├── openenv.yaml              # App Config
│   ├── Dockerfile                # Container Setup
│   └── requirements.txt          # Dependencies
│
└── 📋 Validation
    ├── inference.py              # LLM Baseline Script
    ├── test_env.py               # Logic Tests
    └── test_api.py               # API Verification
```

---

<div align="center">

### 🌟 **Developed for the Meta x Pytorch x SST x OpenEnv Challenge** 🌟

**[⭐ View on GitHub](https://github.com/Athull567/ai-devops-incident-recovery)** | **[🚀 Try Live Space](https://huggingface.co/spaces/athul890ak/devops-incident-recovery)**

</div>

---

**Last Updated:** April 2026 | **Version:** 1.0.0 | **Status:** ✅ Zero-Risk Submission Ready
