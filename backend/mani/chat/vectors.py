# ABOUTME: Loads the framework exemplar vectors once per process and fails loud when stale.
# ABOUTME: Routing on vectors that no longer match the framework files is worse than not routing.

from __future__ import annotations

import json
import logging
import pathlib
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

VECTORS_FILE = pathlib.Path(__file__).resolve().parents[2] / "content" / "framework_vectors.json"


@dataclass(frozen=True)
class Facet:
    """One thing a person might say that points at a framework, as a vector."""

    framework_id: str
    facet: str
    text: str
    vector: tuple[float, ...]

    @property
    def kind(self) -> str:
        """`exemplar` (how a person talks, what routes) or `find` (what the framework still
        needs to know, what decides readiness)."""
        return self.facet.split(":", 1)[0]


@dataclass(frozen=True)
class FacetIndex:
    model: str
    dims: int
    content_sha256: str
    facets: tuple[Facet, ...]

    def of_kind(self, kind: str) -> tuple[Facet, ...]:
        return tuple(f for f in self.facets if f.kind == kind)

    def for_framework(self, framework_id: str, kind: str | None = None) -> tuple[Facet, ...]:
        return tuple(
            f for f in self.facets
            if f.framework_id == framework_id and (kind is None or f.kind == kind)
        )

    @property
    def framework_ids(self) -> tuple[str, ...]:
        seen: list[str] = []
        for f in self.facets:
            if f.framework_id not in seen:
                seen.append(f.framework_id)
        return tuple(seen)


@lru_cache(maxsize=1)
def load(path: pathlib.Path | None = None) -> FacetIndex | None:
    """The shipped vectors, or None when the file is missing.

    None is a working state: the orchestrator falls back to the phrase router. A *corrupt*
    file is not, and raises.
    """
    file = path or VECTORS_FILE
    if not file.exists():
        logger.warning("no framework vectors at %s; semantic routing is unavailable", file)
        return None
    payload = json.loads(file.read_text())
    facets = tuple(
        Facet(
            framework_id=row["framework_id"],
            facet=row["facet"],
            text=row["text"],
            vector=tuple(row["vector"]),
        )
        for row in payload["facets"]
    )
    if not facets:
        raise ValueError(f"{file} has no facets")
    return FacetIndex(
        model=payload["model"],
        dims=payload["dims"],
        content_sha256=payload["content_sha256"],
        facets=facets,
    )


def is_stale(index: FacetIndex, expected_sha256: str) -> bool:
    """Whether the framework files have changed since the vectors were computed."""
    return index.content_sha256 != expected_sha256
