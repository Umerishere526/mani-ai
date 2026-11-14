# ABOUTME: Locust load test: synthetic people each start a chat with a first message and send a message every 30 to 60 seconds.
# ABOUTME: Run against a local backend pointed at scripts/fake_openrouter.py; never against a real model.
"""
Usage (from backend/, with the local Supabase, the fake and the backend running):
    python scripts/load_users.py create 100 --out "$TOKENS"
    LOAD_TOKENS="$TOKENS" locust -f scripts/locustfile.py --host http://127.0.0.1:8000 \
        --headless -u 100 -r 10 -t 10m --csv "$OUT/run100"
    python scripts/load_users.py remove

A failed request is reported as its status and error category, so the failures table reads as errors by type.
"""

from __future__ import annotations

import itertools
import json
import os
import random
import threading
import uuid

from locust import HttpUser, between, task

# The chat-tester gives up after this long, and so does a person.
CLIENT_TIMEOUT_SECONDS = 90

MESSAGES = [
    "work has been really hard lately and I can't switch off",
    "my manager keeps changing what she wants from me",
    "I snapped at my partner again last night",
    "I don't know, I just feel tired all the time",
    "it's mostly the meetings, they drain me",
    "I keep thinking I'm going to get fired",
    "yeah that's right",
    "my brother never calls unless he needs something",
]

_tokens = iter(json.loads(open(os.environ["LOAD_TOKENS"]).read()))
_taking = threading.Lock()


def _next_token() -> str:
    with _taking:
        return next(_tokens)


def _failure(response) -> str:
    try:
        category = response.json()["error"]["category"]
    except Exception:
        category = "no error body"
    return f"{response.status_code} {category}"


class Person(HttpUser):
    wait_time = between(30, 60)

    def on_start(self) -> None:
        self.client.headers["Authorization"] = f"Bearer {_next_token()}"
        self.thread_id = None
        self.lines = itertools.cycle(random.sample(MESSAGES, len(MESSAGES)))
        with self.client.post(
            "/v1/threads", json={"content": next(self.lines), "client_message_id": str(uuid.uuid4())},
            name="start", timeout=CLIENT_TIMEOUT_SECONDS, catch_response=True,
        ) as response:
            if response.status_code == 201:
                self.thread_id = response.json()["thread"]["id"]
            else:
                response.failure(_failure(response))

    @task
    def send(self) -> None:
        if self.thread_id is None:
            return
        with self.client.post(
            f"/v1/threads/{self.thread_id}/messages",
            json={"content": next(self.lines), "client_message_id": str(uuid.uuid4())},
            name="send", timeout=CLIENT_TIMEOUT_SECONDS, catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(_failure(response))
