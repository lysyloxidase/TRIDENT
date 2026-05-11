"""Celery worker entry point for long-running TRIDENT agent tasks."""

from __future__ import annotations

import os
from typing import Any

from trident.agents.orchestrator import TridentOrchestrator

try:
    from celery import Celery
except ImportError:  # pragma: no cover
    Celery = None  # type: ignore[assignment]


def build_celery_app() -> Any:
    broker = os.getenv("TRIDENT_REDIS_URL", "redis://redis:6379/0")
    backend = os.getenv("TRIDENT_RESULT_BACKEND", broker)
    if Celery is None:
        return None
    app = Celery("trident", broker=broker, backend=backend)

    @app.task(name="trident.run_pipeline")
    def run_pipeline(disease: str, n_targets: int = 5, design: bool = False) -> dict[str, Any]:
        state = TridentOrchestrator().run(disease=disease, n_targets=n_targets, design=design)
        return state.to_summary()

    return app


celery_app = build_celery_app()


def main() -> int:
    if celery_app is None:
        print("Celery is not installed; install trident-discovery with production dependencies.")
        return 1
    print("Start with: celery -A trident.worker.celery_app worker --loglevel=info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
