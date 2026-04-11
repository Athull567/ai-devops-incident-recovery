"""
FastAPI application for the DevOps Incident Recovery Environment.

Exposes the environment over HTTP REST endpoints compatible with
the OpenEnv specification. Endpoints:

  GET  /health  → Health check (returns 200)
  GET  /        → Environment info page
  POST /reset   → Reset environment, returns initial observation
  POST /step    → Execute action, returns observation
  GET  /state   → Get current environment state
  GET  /schema  → Get action/observation/state JSON schemas
  GET  /tasks   → List available tasks
"""

import sys
import os
import json
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import DevOpsAction, DevOpsObservation, DevOpsState, ActionType
from environment import DevOpsEnvironment
from scenarios import SCENARIOS, TASK_IDS


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="DevOps Incident Recovery Environment",
    description="An OpenEnv-compatible environment that simulates real-world cloud infrastructure failures for AI agent training.",
    version="1.0.0",
)

# Global environment instance (one per server for simplicity)
env = DevOpsEnvironment()


# =============================================================================
# Request/Response Models
# =============================================================================

class ResetRequest(BaseModel):
    seed: Optional[int] = None
    episode_id: Optional[str] = None
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    action: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str = "healthy"


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint. Returns 200 when server is running."""
    return HealthResponse(status="healthy")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with environment info."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DevOps Incident Recovery Environment</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 50px auto;
                   background: #0d1117; color: #c9d1d9; padding: 20px; }
            h1 { color: #58a6ff; }
            h2 { color: #79c0ff; }
            .badge { display: inline-block; padding: 4px 12px; border-radius: 12px;
                     font-size: 12px; margin: 2px; }
            .easy { background: #238636; color: white; }
            .medium { background: #d29922; color: black; }
            .hard { background: #da3633; color: white; }
            code { background: #161b22; padding: 2px 6px; border-radius: 4px; color: #79c0ff; }
            a { color: #58a6ff; }
            .endpoint { background: #161b22; padding: 10px; margin: 5px 0; border-radius: 6px;
                        border-left: 3px solid #58a6ff; }
        </style>
    </head>
    <body>
        <h1>🔧 DevOps Incident Recovery Environment</h1>
        <p>An OpenEnv-compatible AI training environment simulating real-world cloud infrastructure failures.</p>

        <h2>📡 API Endpoints</h2>
        <div class="endpoint"><code>GET /health</code> — Health check</div>
        <div class="endpoint"><code>POST /reset</code> — Reset environment (body: {"task_id": "..."})</div>
        <div class="endpoint"><code>POST /step</code> — Execute action (body: {"action": {"action_type": "...", "target_service": "..."}})</div>
        <div class="endpoint"><code>GET /state</code> — Get current state</div>
        <div class="endpoint"><code>GET /schema</code> — Get JSON schemas</div>
        <div class="endpoint"><code>GET /tasks</code> — List available tasks</div>

        <h2>🎯 Available Tasks</h2>
        <p><span class="badge easy">EASY</span> Task 1: High CPU & Memory Leak</p>
        <p><span class="badge easy">EASY</span> Task 2: Service Crash Recovery</p>
        <p><span class="badge medium">MEDIUM</span> Task 3: Database Connection Cascade</p>
        <p><span class="badge medium">MEDIUM</span> Task 4: Bad Deployment Rollback</p>
        <p><span class="badge hard">HARD</span> Task 5: Hidden Service Mesh DNS Failure</p>

        <h2>🤖 Actions</h2>
        <p>diagnose, restart_service, scale_up, scale_down, rollback, apply_patch, check_logs, no_op</p>

        <p><a href="/docs">📖 Interactive API Docs (Swagger UI)</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/reset")
async def reset_env(request: ResetRequest = None):
    """Reset the environment and start a new incident scenario."""
    if request is None:
        request = ResetRequest()

    try:
        obs = env.reset(
            seed=request.seed,
            episode_id=request.episode_id,
            task_id=request.task_id,
        )
        obs_dict = obs.model_dump()
        return {
            "observation": {
                "services": {k: v.model_dump() if hasattr(v, 'model_dump') else v for k, v in obs_dict.get("services", {}).items()},
                "logs": obs_dict.get("logs", []),
                "alerts": [a.model_dump() if hasattr(a, 'model_dump') else a for a in obs_dict.get("alerts", [])],
                "timestamp": obs_dict.get("timestamp", ""),
                "metadata": obs_dict.get("metadata", {}),
            },
            "reward": obs_dict.get("reward", 0.0001),
            "done": obs_dict.get("done", False),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@app.post("/step")
async def step_env(request: StepRequest):
    """Execute an action in the environment."""
    try:
        action_data = request.action
        action = DevOpsAction(
            action_type=action_data.get("action_type", "no_op"),
            target_service=action_data.get("target_service"),
            metadata=action_data.get("metadata", {}),
        )
        obs = env.step(action)
        obs_dict = obs.model_dump()
        return {
            "observation": {
                "services": {k: v.model_dump() if hasattr(v, 'model_dump') else v for k, v in obs_dict.get("services", {}).items()},
                "logs": obs_dict.get("logs", []),
                "alerts": [a.model_dump() if hasattr(a, 'model_dump') else a for a in obs_dict.get("alerts", [])],
                "timestamp": obs_dict.get("timestamp", ""),
                "metadata": obs_dict.get("metadata", {}),
            },
            "reward": obs_dict.get("reward", 0.0001),
            "done": obs_dict.get("done", False),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Step failed: {str(e)}")


@app.get("/state")
async def get_state():
    """Get the current environment state."""
    return env.state.model_dump()


@app.get("/schema")
async def get_schema():
    """Get JSON schemas for action, observation, and state models."""
    return {
        "action": DevOpsAction.model_json_schema(),
        "observation": DevOpsObservation.model_json_schema(),
        "state": DevOpsState.model_json_schema(),
    }


@app.get("/tasks")
async def get_tasks():
    """List all available tasks with descriptions."""
    tasks = []
    for task_id, scenario in SCENARIOS.items():
        tasks.append({
            "task_id": task_id,
            "title": scenario.title,
            "difficulty": scenario.difficulty,
            "description": scenario.description,
            "optimal_steps": scenario.optimal_steps,
        })
    return {"tasks": tasks, "total": len(tasks)}

def main():
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
