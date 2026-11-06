# ABOUTME: Creates and removes the synthetic users a local load test signs in as, with tokens local GoTrue would issue.
# ABOUTME: Local only: it reads the signing key from the local auth container and refuses any other database.
"""
Usage:
    python scripts/load_users.py create 500 --out /path/tokens.json
    python scripts/load_users.py remove

Local GoTrue allows 30 password sign-ins per 5 minutes per address (supabase/config.toml, [auth.rate_limit]),
so 500 people cannot sign in through it in a test's time. Their tokens are signed instead with the key local
GoTrue signs with (GOTRUE_JWT_KEYS in the supabase_auth_mani container), carrying the claims it issues, and
the backend verifies them through the same published key set as any other token.

The users are inserted into auth.users as the scenario check does, which runs the signup trigger. `remove`
deletes every one of them and the cost rows their calls left, as tests/integration/cleanup.py does.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import subprocess
import sys
import time
import uuid

import asyncpg
import jwt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.config import get_settings  # noqa: E402
from tests.integration.cleanup import remove_test_users  # noqa: E402

DOMAIN = "load.test"
AUTH_CONTAINER = "supabase_auth_mani"
TOKEN_HOURS = 3


def _local_url() -> str:
    url = get_settings().database_url
    if "127.0.0.1" not in url and "localhost" not in url:
        raise SystemExit("DATABASE_URL is not local; this script only runs against the local Supabase")
    return url


def _signing_key() -> tuple[str, jwt.PyJWK]:
    env = subprocess.run(
        ["docker", "exec", AUTH_CONTAINER, "printenv", "GOTRUE_JWT_KEYS"],
        check=True, capture_output=True, text=True,
    ).stdout
    key = next(k for k in json.loads(env) if "sign" in k.get("key_ops", []))
    return key["kid"], jwt.PyJWK(key)


async def create(count: int, out: pathlib.Path) -> None:
    kid, key = _signing_key()
    issuer = f"{get_settings().supabase_url}/auth/v1"
    now = int(time.time())
    users = [(uuid.uuid4(), f"load-{i}-{uuid.uuid4().hex[:8]}@{DOMAIN}") for i in range(count)]
    conn = await asyncpg.connect(_local_url())
    try:
        await conn.executemany("insert into auth.users (id, email) values ($1, $2)", users)
    finally:
        await conn.close()
    tokens = [
        jwt.encode(
            {
                "sub": str(user), "aud": "authenticated", "role": "authenticated", "email": email,
                "iss": issuer, "iat": now, "exp": now + TOKEN_HOURS * 3600,
                "app_metadata": {"provider": "email"}, "user_metadata": {}, "aal": "aal1",
                "session_id": str(uuid.uuid4()), "is_anonymous": False,
            },
            key.key, algorithm="ES256", headers={"kid": kid},
        )
        for user, email in users
    ]
    out.write_text(json.dumps(tokens))
    print(f"created {count} users; tokens in {out}")


async def remove() -> None:
    conn = await asyncpg.connect(_local_url())
    try:
        ids = [r["id"] for r in await conn.fetch("select id from auth.users where email like $1", f"%@{DOMAIN}")]
        await remove_test_users(conn, *ids)
    finally:
        await conn.close()
    print(f"removed {len(ids)} users")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    making = commands.add_parser("create")
    making.add_argument("count", type=int)
    making.add_argument("--out", type=pathlib.Path, required=True)
    commands.add_parser("remove")
    args = parser.parse_args()
    asyncio.run(create(args.count, args.out) if args.command == "create" else remove())


if __name__ == "__main__":
    main()
