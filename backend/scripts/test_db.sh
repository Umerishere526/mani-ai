#!/usr/bin/env bash
# ABOUTME: Runs the schema, RLS and privilege suites against Postgres.
# ABOUTME: Default is a throwaway container; --local targets the running Supabase.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER=mani-pg-test
IMAGE=postgres:17
PORT=55432
TARGET=throwaway

usage() {
  cat <<'USAGE'
usage: scripts/test_db.sh [--local]

  (no args)  Start a throwaway Postgres, apply the harness and schema, run the suites,
             tear it down. Needs Docker only.
  --local    Run the suites against the local Supabase already running
             (container supabase_db_mani). Does not reapply the schema.

  KEEP_DB=1  Leave the throwaway container running afterwards.
USAGE
}

case "${1:-}" in
  --local) TARGET=local ;;
  -h|--help) usage; exit 0 ;;
  "") ;;
  *) usage; exit 1 ;;
esac

if [ "$TARGET" = "local" ]; then
  DB_CONTAINER=supabase_db_mani
  if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    echo "$DB_CONTAINER is not running. Start it with: supabase start" >&2
    exit 1
  fi
else
  DB_CONTAINER="$CONTAINER"
  cleanup() {
    if [ "${KEEP_DB:-0}" = "1" ]; then
      echo "KEEP_DB=1, leaving $CONTAINER on port $PORT"
    else
      docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    fi
  }
  trap cleanup EXIT

  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$CONTAINER" \
    -e POSTGRES_PASSWORD=postgres -p "$PORT:5432" "$IMAGE" >/dev/null

  printf 'waiting for postgres'
  for _ in $(seq 1 120); do
    # Over TCP: the image's first start runs a temporary server on the socket only, then restarts, and a check on
    # the socket could catch that one and lose the harness to the restart.
    if docker exec "$CONTAINER" psql -U postgres -h 127.0.0.1 -c 'select 1' >/dev/null 2>&1; then
      echo " ready"
      break
    fi
    printf '.'
    sleep 0.5
  done
fi

run_sql() {
  docker exec -i "$DB_CONTAINER" psql -U postgres -v ON_ERROR_STOP=1 -q < "$1" 2>&1 \
    | sed 's/^NOTICE:  //'
}

if [ "$TARGET" = "throwaway" ]; then
  # Recreates what Supabase supplies: auth.users, auth.uid(), and the three roles.
  echo "applying test harness"
  run_sql "$HERE/supabase/test_harness.sql"
  # Every migration in order, not just the first. This named 001 alone until now, so from
  # the moment 002 landed the suites were asserting against a schema the project no longer
  # had - passing on columns and policies that production did not match. Globbing keeps a
  # new migration covered without anyone remembering to add it here.
  # A migration that moves data is tested with data: tests/sql/migrations/before_NNN.sql plants rows as the schema
  # before it held them, and after_NNN.sql asserts where the migration put them (2026-11-10: 036 passed on every
  # empty database and failed on the first one with rows to move).
  for migration in "$HERE"/supabase/migrations/*.sql; do
    number="$(basename "$migration" | cut -c1-3)"
    if [ -f "$HERE/tests/sql/migrations/before_$number.sql" ]; then
      echo "planting rows for $number"
      run_sql "$HERE/tests/sql/migrations/before_$number.sql"
    fi
    echo "applying $(basename "$migration")"
    run_sql "$migration"
    if [ -f "$HERE/tests/sql/migrations/after_$number.sql" ]; then
      run_sql "$HERE/tests/sql/migrations/after_$number.sql"
    fi
  done
fi

echo
echo "— row level security —"
run_sql "$HERE/tests/sql/test_rls.sql"

echo
echo "— privileges —"
run_sql "$HERE/tests/sql/test_grants.sql"

echo
echo "database tests passed ($TARGET)"
