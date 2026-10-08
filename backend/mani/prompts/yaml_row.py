# ABOUTME: Parses the body of a config row written in YAML into a strict pydantic model.
# ABOUTME: A refusal names the key and the rule, never the value written.

from __future__ import annotations

from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

Model = TypeVar("Model", bound=BaseModel)


def parse_yaml_row(model: type[Model], label: str, content: str) -> Model:
    """The row's content as `model`. Raises ValueError saying which keys break which rules.

    The content here may be whatever someone typed into the portal, so no text from it goes
    into the message: not the YAML parser's snippet, and not the value pydantic rejected.
    """
    try:
        body = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"{label} does not parse as YAML") from exc
    if not isinstance(body, dict):
        raise ValueError(f"{label} is not a YAML map")
    try:
        return model.model_validate(body)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors(include_input=False, include_context=False, include_url=False)
        )
        raise ValueError(f"{label} is not valid: {problems}") from None
