# ABOUTME: Computes the framework exemplar vectors the semantic router matches against.
# ABOUTME: Idempotent: re-runs cost nothing unless an exemplar or the model changed.

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.chat import embed  # noqa: E402
from scripts.seed import FRAMEWORKS_DIR, parse_framework  # noqa: E402

VECTORS_FILE = pathlib.Path(__file__).resolve().parent.parent / "content" / "framework_vectors.json"


def facets() -> list[tuple[str, str, str]]:
    """(framework_id, facet, text) for everything the router matches against.

    Exemplars route - they are how a person actually talks. to_find_out items are scored
    separately for offer readiness (has the person said enough yet), so they are embedded
    here too and the two uses share one source of truth.
    """
    rows: list[tuple[str, str, str]] = []
    for path in sorted(FRAMEWORKS_DIR.glob("*.md")):
        framework = parse_framework(path)
        activation = framework.get("activation") or {}
        fid = framework["id"]
        for i, text in enumerate(activation.get("exemplars") or []):
            rows.append((fid, f"exemplar:{i}", text))
        for i, text in enumerate(activation.get("to_find_out") or []):
            rows.append((fid, f"find:{i}", text))
    return rows


def content_hash(rows: list[tuple[str, str, str]]) -> str:
    """Changes when any exemplar or to_find_out item changes, so staleness is detectable."""
    joined = "\n".join(f"{fid}\t{facet}\t{text}" for fid, facet, text in sorted(rows))
    return hashlib.sha256(joined.encode()).hexdigest()


def load() -> dict | None:
    if not VECTORS_FILE.exists():
        return None
    return json.loads(VECTORS_FILE.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="exit 1 when the vectors are stale, without calling the provider",
    )
    args = parser.parse_args()

    rows = facets()
    if not rows:
        print("no exemplars found in content/frameworks/", file=sys.stderr)
        return 1
    digest = content_hash(rows)
    existing = load()
    fresh = (
        existing is not None
        and existing.get("content_sha256") == digest
        and existing.get("model") == embed.DEFAULT_MODEL
    )

    if args.check:
        print("vectors are up to date" if fresh else "vectors are STALE: run scripts/embed_frameworks.py")
        return 0 if fresh else 1

    if fresh:
        print(f"vectors are up to date ({len(rows)} facets)")
        return 0

    print(f"embedding {len(rows)} facets with {embed.DEFAULT_MODEL}...")
    vectors = embed.embedder()([text for _, _, text in rows])
    payload = {
        "model": embed.DEFAULT_MODEL,
        "dims": len(vectors[0]),
        "content_sha256": digest,
        "facets": [
            {"framework_id": fid, "facet": facet, "text": text, "vector": vector}
            for (fid, facet, text), vector in zip(rows, vectors)
        ],
    }
    VECTORS_FILE.write_text(json.dumps(payload))
    by_framework: dict[str, int] = {}
    for fid, _, _ in rows:
        by_framework[fid] = by_framework.get(fid, 0) + 1
    for fid, count in sorted(by_framework.items()):
        print(f"  {fid:<28} {count:>2} facets")
    print(f"wrote {VECTORS_FILE.name} ({len(rows)} facets, {len(vectors[0])} dims)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
