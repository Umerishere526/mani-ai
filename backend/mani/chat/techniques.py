# ABOUTME: The registry of active frameworks, keyed by id, and where each one's phases end.
# ABOUTME: Membership here is the closed set a model supplied technique id is checked against.

from __future__ import annotations

from mani.models.rows import Framework

# Every framework opens by offering itself. The schema enforces it; the machine relies
# on it to tell "nothing started" apart from "started at the beginning".
OFFERING = "offering"


class Registry:
    """The active frameworks, keyed by id.

    Loaded from admin.frameworks rather than hardcoded, so adding a framework is a
    content change. Membership of this registry is the closed set that model-supplied
    technique ids are checked against.
    """

    def __init__(self, frameworks: list[Framework]) -> None:
        self._by_id = {f.id: f for f in frameworks}

    def __contains__(self, framework_id: object) -> bool:
        return framework_id in self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    @property
    def ids(self) -> list[str]:
        return list(self._by_id)

    def get(self, framework_id: str | None) -> Framework | None:
        return self._by_id.get(framework_id) if framework_id else None

    def is_final(self, framework_id: str | None, phase: str | None) -> bool:
        """Whether this phase is the last one in the framework's sequence.

        Completion is a position, not a name. Comparing against a literal phase id can
        only ever recognise the frameworks that happen to end on it, and makes any phase
        appended after it unreachable.
        """
        framework = self.get(framework_id)
        if framework is None or phase is None:
            return False
        return bool(framework.phases) and framework.phases[-1] == phase
