"""天枢 HUD — 独立系统监控后端"""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from metrics import collect_metrics, metric_cards, warm_caches
from logs import collect_logs
from log_summarizer import enrich_log_row

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Tianshu HUD Monitor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    warm_caches()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/metrics")
def get_metrics():
    data = collect_metrics()
    return {"data": data, "cards": metric_cards(data), "logs": collect_logs(data, limit=45)}


@app.get("/api/logs")
def get_logs():
    data = collect_metrics()
    return {"logs": collect_logs(data, limit=50, allow_ai=True)}


@app.get("/api/stream")
async def stream():
    async def gen():
        while True:
            try:
                data = collect_metrics()
                payload = {
                    "type": "metrics",
                    "data": data,
                    "cards": metric_cards(data),
                    "logs": collect_logs(data, limit=45, allow_ai=False),
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(2)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
