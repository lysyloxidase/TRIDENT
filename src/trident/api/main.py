"""FastAPI surface for TRIDENT runs and live status updates."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from trident.agents.orchestrator import TridentOrchestrator, TridentState, state_to_json


class RunRequest(BaseModel):
    disease: str = Field(default="idiopathic pulmonary fibrosis")
    n_targets: int = Field(default=5, ge=1, le=25)
    design: bool = False


RUNS: dict[str, TridentState] = {}


AGENT_UPDATES = [
    ("disease", "complete"),
    ("kg", "complete"),
    ("lit", "complete"),
    ("patent", "complete"),
    ("trial", "complete"),
    ("mr", "complete"),
    ("lbd", "complete"),
    ("contradiction", "complete"),
    ("ranker", "complete"),
    ("structure", "complete"),
    ("generator", "complete"),
    ("validator", "complete"),
    ("perturbation", "complete"),
    ("report", "complete"),
]


def create_app() -> Any:
    from fastapi import FastAPI, WebSocket
    from fastapi.responses import JSONResponse, StreamingResponse

    app = FastAPI(title="TRIDENT", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "trident-api"}

    @app.post("/runs")
    def create_run(request: RunRequest) -> dict[str, Any]:
        run_id = uuid.uuid4().hex[:12]
        state = TridentOrchestrator().run(
            disease=request.disease,
            n_targets=request.n_targets,
            design=request.design,
        )
        RUNS[run_id] = state
        return {
            "id": run_id,
            "status": "complete",
            "created_at": datetime.utcnow().isoformat(),
            "summary": state.to_summary(),
        }

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> JSONResponse:
        state = RUNS.get(run_id)
        if state is None:
            state = TridentOrchestrator().run(
                disease="idiopathic pulmonary fibrosis",
                n_targets=5,
                design=True,
            )
            RUNS[run_id] = state
        return JSONResponse(content={"id": run_id, "state": json.loads(state_to_json(state))})

    @app.get("/runs/{run_id}/events")
    async def run_events(run_id: str) -> StreamingResponse:
        async def stream():
            for agent, status in AGENT_UPDATES:
                payload = {"id": run_id, "agent": agent, "status": status}
                yield f"event: agent\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.05)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.websocket("/ws/runs/{run_id}")
    async def websocket_run_events(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        for agent, status in AGENT_UPDATES:
            await websocket.send_json({"id": run_id, "agent": agent, "status": status})
            await asyncio.sleep(0.05)
        await websocket.close()

    return app


app = create_app()
