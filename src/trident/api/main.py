"""Minimal API factory placeholder for Phase 7."""


def create_app():
    try:
        from fastapi import FastAPI
    except ImportError:
        return None

    app = FastAPI(title="TRIDENT")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
