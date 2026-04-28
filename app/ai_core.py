"""
Core AI logic.

Reads PROVIDER env var to route between Anthropic and Ollama. Both paths
support streaming token delivery and a tool-use loop: the model calls a tool,
the registry executes it, the result feeds back in, and streaming resumes.

WebSocket message protocol sent to the frontend:
  {"type": "token",       "content": "..."}   — streaming text chunk
  {"type": "tool_call",   "tool": "...", "args": {...}}  — tool about to run
  {"type": "tool_result", "tool": "...", "result": "..."} — tool output
  {"type": "done"}                             — turn complete
  {"type": "error",       "message": "..."}   — unrecoverable failure
"""
import json

import httpx
from anthropic import AsyncAnthropic

from app.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    PROVIDER,
)
from app.memory import memory
from app.tools.registry import registry

SYSTEM_PROMPT = (
    "You are ARC (Adaptive Reasoning Core), a highly capable personal AI assistant. "
    "You are efficient, direct, and occasionally witty. "
    "You never say you cannot do something without first attempting to use an available tool. "
    "You proactively suggest using tools when appropriate. "
    "You address the user as 'Leo' unless told otherwise."
)


async def stream_chat(user_message: str, websocket) -> None:
    """
    Public entry point called by the WebSocket handler.
    Routes to the correct provider, persists the exchange to memory, then
    signals the frontend that the turn is complete.
    """
    try:
        if PROVIDER == "anthropic":
            response_text = await _stream_anthropic(user_message, websocket)
        else:
            response_text = await _stream_ollama(user_message, websocket)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        return

    # Only persist the final text (tool call intermediates are ephemeral)
    memory.add("user", user_message)
    if response_text:
        memory.add("assistant", response_text)

    await websocket.send_json({"type": "done"})


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

async def _stream_anthropic(user_message: str, websocket) -> str:
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Build message list: persistent history + current user turn
    messages = memory.get()
    messages.append({"role": "user", "content": user_message})

    full_response_text = ""

    while True:
        async with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=registry.get_anthropic_tools(),
        ) as stream:
            # Stream text tokens to the frontend as they arrive
            async for text in stream.text_stream:
                full_response_text += text
                await websocket.send_json({"type": "token", "content": text})

            final_msg = await stream.get_final_message()

        # Serialize content blocks to plain dicts for the next request
        assistant_content = [_block_to_dict(b) for b in final_msg.content]
        messages.append({"role": "assistant", "content": assistant_content})

        tool_use_blocks = [b for b in final_msg.content if b.type == "tool_use"]

        if not tool_use_blocks:
            break  # Model is done; no more tool calls

        # Execute each tool and collect results
        tool_results = []
        for block in tool_use_blocks:
            await websocket.send_json({"type": "tool_call", "tool": block.name, "args": block.input})

            result = registry.execute(block.name, block.input)

            await websocket.send_json({"type": "tool_result", "tool": block.name, "result": result})
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )

        messages.append({"role": "user", "content": tool_results})

    return full_response_text


def _block_to_dict(block) -> dict:
    """Convert an Anthropic SDK content block object to a plain dict."""
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    return block.model_dump()


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------

async def _stream_ollama(user_message: str, websocket) -> str:
    # Ollama expects system message as first item in the list
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory.get())
    messages.append({"role": "user", "content": user_message})

    full_response_text = ""

    while True:
        accumulated_text = ""
        tool_calls = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "tools": registry.get_ollama_tools(),
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = data.get("message", {})
                    content = msg.get("content", "")

                    if content:
                        accumulated_text += content
                        full_response_text += content
                        await websocket.send_json({"type": "token", "content": content})

                    # Tool calls arrive in the final chunk for Ollama
                    if msg.get("tool_calls"):
                        tool_calls = msg["tool_calls"]

        if not tool_calls:
            break

        messages.append({"role": "assistant", "content": accumulated_text, "tool_calls": tool_calls})

        for tc in tool_calls:
            func_info = tc.get("function", {})
            name = func_info.get("name", "")
            args = func_info.get("arguments", {})

            # Ollama sometimes serialises arguments as a JSON string
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            await websocket.send_json({"type": "tool_call", "tool": name, "args": args})
            result = registry.execute(name, args)
            await websocket.send_json({"type": "tool_result", "tool": name, "result": result})

            messages.append({"role": "tool", "content": result})

    return full_response_text

 