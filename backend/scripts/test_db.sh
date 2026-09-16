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
    if docker exec "$CONTAINER" psql -U postgres -c 'select 1' >/dev/null 2>&1; then
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
  echo "applying schema"
  run_sql "$HERE/supabase/migrations/001_initial_schema.sql"
fi

echo
echo "— row level security —"
run_sql "$HERE/tests/sql/test_rls.sql"

echo
echo "— privileges —"
run_sql "$HERE/tests/sql/test_grants.sql"

echo
echo "database tests passed ($TARGET)"
