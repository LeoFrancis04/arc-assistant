"""
FastAPI application entry point.

Serves the static single-page frontend and exposes:
  WS  /ws/chat        — streaming chat (main interface)
  GET /api/history    — read conversation memory
  POST /api/clear     — wipe conversation memory
  GET /api/health     — provider + status check
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.ai_core import stream_chat
from app.config import PROVIDER
from app.memory import memory

app = FastAPI(title="ARC — Adaptive Reasoning Core", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("app/static/index.html") as f:
        return f.read()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Accepts a WebSocket connection and handles the streaming chat loop.

    Expects: {"message": "<user text>"}
    Sends:   see ai_core.py protocol header
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "").strip()
            if not user_message:
                continue
            await stream_chat(user_message, websocket)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.get("/api/history")
async def get_history():
    return JSONResponse({"messages": memory.get()})


@app.post("/api/clear")
async def clear_history():
    memory.clear()
    return JSONResponse({"status": "cleared"})


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "provider": PROVIDER})
 