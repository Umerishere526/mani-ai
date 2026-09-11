#!/usr/bin/env bash
# ABOUTME: PostToolUse hook that lints and typechecks the app a just-edited file belongs to.
# ABOUTME: Routes web/ to eslint+tsc, mobile/ to expo lint+tsc, backend/ to a py_compile check.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Claude Code passes the tool payload as JSON on stdin.
payload="$(cat)"
file="$(printf '%s' "$payload" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

[ -z "$file" ] && exit 0
case "$file" in
  "$ROOT"/*) rel="${file#"$ROOT"/}" ;;
  *) exit 0 ;;
esac

app="${rel%%/*}"
status=0

report() {
  # Exit code 2 sends stderr back to Claude as actionable feedback.
  printf '%s\n' "$1" >&2
  status=2
}

case "$app" in
  web)
    case "$file" in
      *.ts|*.tsx|*.js|*.jsx|*.mjs) ;;
      *) exit 0 ;;
    esac
    cd "$ROOT/web" || exit 0
    [ -d node_modules ] || exit 0
    if ls eslint.config.* .eslintrc* >/dev/null 2>&1; then
      if ! out="$(npx --no-install eslint "$file" 2>&1)"; then
        report "eslint (web) failed:
$out"
      fi
    fi
    if ! out="$(npx --no-install tsc --noEmit 2>&1)"; then
      report "tsc (web) failed:
$out"
    fi
    ;;

  mobile)
    case "$file" in
      *.ts|*.tsx|*.js|*.jsx) ;;
      *) exit 0 ;;
    esac
    cd "$ROOT/mobile" || exit 0
    [ -d node_modules ] || exit 0
    # Only lint if a config already exists: `expo lint` otherwise tries to
    # install eslint on the fly, which mutates package.json mid-edit.
    if ls eslint.config.* .eslintrc* >/dev/null 2>&1; then
      if ! out="$(npx --no-install expo lint 2>&1)"; then
        report "expo lint (mobile) failed:
$out"
      fi
    fi
    if ! out="$(npx --no-install tsc --noEmit 2>&1)"; then
      report "tsc (mobile) failed:
$out"
    fi
    ;;

  backend)
    case "$file" in
      *.py) ;;
      *) exit 0 ;;
    esac
    cd "$ROOT/backend" || exit 0
    py="./.venv/bin/python"
    [ -x "$py" ] || exit 0
    if ! out="$("$py" -m py_compile "$file" 2>&1)"; then
      report "python syntax check failed:
$out"
    fi
    if [ -x ./.venv/bin/ruff ]; then
      if ! out="$(./.venv/bin/ruff check "$file" 2>&1)"; then
        report "ruff failed:
$out"
      fi
    fi
    ;;
esac

exit $status
