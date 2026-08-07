import sys
import os
import json
import uuid
import asyncio

# Ensure src directory is in sys.path for Vercel/serverless imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import agent components
from core.config import setup_api_key
setup_api_key()  # Load API keys from .env early

from core.utils import chat_with_agent
from agents.agent import create_protected_agent
from assignment.pipeline import build_production_plugins, build_observability

app = FastAPI(title="VinBank Security Dashboard")

# Enable CORS for localhost testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Guardrails pipeline & agent globally
plugins = build_production_plugins(max_requests=100, window_seconds=60, use_llm_judge=True)
audit, monitor = build_observability()

# Replace the pipeline plugins with our monitored ones
# This relies on the fact that build_production_plugins returns RateLimit, InputGuardrail, OutputGuardrail
# We inject our audit and monitor globally so we can track requests.
# Wait, actually, the assignment expects audit to be called manually in the pipeline logic before/after chat.
agent, runner = create_protected_agent(plugins=plugins)


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Handle incoming chat messages and pass them to the guarded agent."""
    data = await request.json()
    user_message = data.get("message", "")
    session_id = data.get("session_id")
    student_id = "demo_user"

    # Generate a unique request ID
    req_id = f"req_{uuid.uuid4().hex[:8]}"

    # Record input for auditing and metrics
    audit.record_input(user_id=student_id, text=user_message, request_id=req_id)
    monitor.total_requests += 1

    try:
        response, session = await chat_with_agent(agent, runner, user_message, session_id)
        is_rate_limited = "Rate limit exceeded" in response
        is_blocked = (
            is_rate_limited
            or "Tài khoản của bạn đã bị ghi nhận" in response
        )
    except Exception as e:
        response = f"System Error: {e}"
        is_rate_limited = False
        is_blocked = True
        session = None

    if is_blocked:
        monitor.blocked_requests += 1
    if is_rate_limited:
        monitor.rate_limit_hits += 1

    # Heuristic for which layer blocked
    blocking_layer = None
    if is_rate_limited:
        blocking_layer = "rate_limiter"
    elif is_blocked:
        blocking_layer = "guardrails"

    # Record output
    audit.record_output(
        user_id=student_id,
        text=response,
        blocked=is_blocked,
        layer=blocking_layer,
        request_id=req_id,
    )

    # Export json to file so UI can read it
    try:
        audit.export_json()
        monitor.export_json()
    except Exception:
        pass

    return {
        "response": response,
        "blocked": is_blocked,
        "session_id": session.id if session else None
    }


@app.get("/api/logs")
async def get_logs():
    """Return the current audit logs and metrics."""
    audit_file = "outputs/audit_log.json"
    metrics_file = "outputs/metrics.json"

    logs = []
    if os.path.exists(audit_file):
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            pass
    if not logs:
        # Fallback to in-memory logs if file system read failed or empty
        logs = audit.snapshot()

    metrics = {}
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except json.JSONDecodeError:
            pass
    if not metrics:
        metrics = monitor.snapshot()

    return {
        "logs": logs[-20:],  # Return only the last 20 logs for UI performance
        "metrics": metrics
    }

# Ensure the static folder path is dynamically resolved
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
