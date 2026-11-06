# ABOUTME: A stand-in for OpenRouter's chat/completions that streams a valid reply for whatever schema is asked.
# ABOUTME: Thinks for the production first-token profile, then streams the text; for load tests, never a real call.
"""
Usage:
    python scripts/fake_openrouter.py [--port 8790] [--first-token-median 6] [--first-token-p90 12]

Point the backend at it with OPENROUTER_BASE_URL=http://127.0.0.1:8790/api/v1 and any OPENROUTER_API_KEY.

The profile is docs/latency-report-2026-11-05.md, section 1: the first token after p50 6 s with a tail near
12 s, then about 1.6 s of streamed text, then usage and a generation id. While it thinks it sends
OpenRouter's keepalive comment, as the real one does.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import time
import uuid
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

SAID = "That sounds like a lot to carry. What feels hardest about it right now?"


def value_for(schema: dict, root: dict, name: str = "") -> Any:
    """The plainest value that satisfies a strict JSON schema: null where null is allowed, the first of an
    enum, every property of an object, and a short sentence for text."""
    if "$ref" in schema:
        return value_for(root["$defs"][schema["$ref"].rsplit("/", 1)[-1]], root, name)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = schema[key]
            if any(o.get("type") == "null" for o in options):
                return None
            return value_for(options[0], root, name)
    kind = schema.get("type")
    if isinstance(kind, list):
        if "null" in kind:
            return None
        kind = kind[0]
    if kind == "object":
        return {key: value_for(sub, root, key) for key, sub in (schema.get("properties") or {}).items()}
    if kind == "array":
        return [value_for(schema.get("items") or {}, root, name) for _ in range(schema.get("minItems", 0))]
    if kind == "string":
        text = SAID if name in ("text", "reply") else f"fake {name or 'value'}"
        return text[: schema.get("maxLength", len(text))]
    if kind == "integer":
        return int(schema.get("minimum", 0))
    if kind == "number":
        return float(schema.get("minimum", 0))
    if kind == "boolean":
        return False
    return None


class Profile:
    def __init__(self, median: float, p90: float, ceiling: float, streaming: float) -> None:
        # Lognormal first-token wait: median `median`, 90th percentile `p90`, never past `ceiling`.
        self.mu = math.log(median)
        self.sigma = (math.log(p90) - self.mu) / 1.2816
        self.ceiling = ceiling
        self.streaming = streaming

    def first_token(self) -> float:
        return min(random.lognormvariate(self.mu, self.sigma), self.ceiling)


def app(profile: Profile) -> Starlette:
    async def completions(request: Request):
        body = await request.json()
        fmt = (body.get("response_format") or {}).get("json_schema") or {}
        schema = fmt.get("schema") or {"type": "object", "properties": {"text": {"type": "string"}}}
        content = json.dumps(value_for(schema, schema))
        generation = f"gen-fake-{uuid.uuid4().hex[:16]}"
        model = body.get("model", "openai/gpt-6-luna")

        async def stream():
            base = {"id": generation, "object": "chat.completion.chunk", "created": int(time.time()),
                    "model": model, "provider": "Fake"}
            thinking_until = time.monotonic() + profile.first_token()
            while (left := thinking_until - time.monotonic()) > 0:
                await asyncio.sleep(min(left, 2.0))
                if thinking_until - time.monotonic() > 0:
                    yield b": OPENROUTER PROCESSING\n\n"
            pieces = 16
            size = math.ceil(len(content) / pieces)
            for i in range(pieces):
                piece = content[i * size:(i + 1) * size]
                delta = {"role": "assistant", "content": piece} if i == 0 else {"content": piece}
                choice = {"index": 0, "delta": delta, "finish_reason": None}
                yield f"data: {json.dumps({**base, 'choices': [choice]})}\n\n".encode()
                await asyncio.sleep(profile.streaming / pieces)
            done = {"index": 0, "delta": {}, "finish_reason": "stop"}
            yield f"data: {json.dumps({**base, 'choices': [done]})}\n\n".encode()
            usage = {
                "prompt_tokens": 15000, "completion_tokens": 900, "total_tokens": 15900,
                "prompt_tokens_details": {"cached_tokens": 10000},
                "completion_tokens_details": {"reasoning_tokens": 600},
            }
            yield f"data: {json.dumps({**base, 'choices': [], 'usage': usage})}\n\n".encode()
            yield b"data: [DONE]\n\n"

        if not body.get("stream"):
            return JSONResponse({"error": {"message": "this fake only streams"}}, status_code=400)
        return StreamingResponse(stream(), media_type="text/event-stream")

    return Starlette(routes=[Route("/api/v1/chat/completions", completions, methods=["POST"])])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--first-token-median", type=float, default=6.0)
    parser.add_argument("--first-token-p90", type=float, default=12.0)
    parser.add_argument("--first-token-max", type=float, default=14.0)
    parser.add_argument("--stream-seconds", type=float, default=1.6)
    args = parser.parse_args()
    profile = Profile(args.first_token_median, args.first_token_p90, args.first_token_max, args.stream_seconds)
    uvicorn.run(app(profile), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
