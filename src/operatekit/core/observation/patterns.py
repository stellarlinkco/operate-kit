from __future__ import annotations

import fnmatch
import re

from operatekit.core.observation.observation import Observation


def match_observation(pattern: str, observation: Observation) -> bool:
    haystacks = [
        observation.text(),
        str(observation.metadata.get("url", "")),
        str(observation.metadata.get("path", "")),
        str(observation.metadata.get("name", "")),
    ]
    if pattern.startswith("contains:"):
        needle = pattern[len("contains:") :]
        return any(needle in h for h in haystacks)
    if pattern.startswith("glob:"):
        expr = pattern[len("glob:") :]
        return any(fnmatch.fnmatch(h, expr) for h in haystacks)
    if pattern.startswith("regex:"):
        expr = pattern[len("regex:") :]
        return any(re.search(expr, h) for h in haystacks)
    return any(pattern in h for h in haystacks)
