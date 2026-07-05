"""Load Stephen CLI agent profiles (YAML) and suggest routing."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

DEFAULT_PROFILES_DIR = Path.home() / "projects" / "ai-agent-teamwork-prompt" / "profiles"


def profiles_dir() -> Path:
    return Path(os.getenv("AGENT_CLI_PROFILES_DIR", DEFAULT_PROFILES_DIR))


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML required: pip install pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid profile: {path}")
    return data


def list_profile_ids() -> list[str]:
    root = profiles_dir()
    if not root.is_dir():
        return []
    return sorted(p.stem for p in root.glob("*.yaml") if p.stem != "agent-cli-profile")


def load_profile(profile_id: str) -> dict[str, Any]:
    path = profiles_dir() / f"{profile_id}.yaml"
    if not path.is_file():
        raise KeyError(f"unknown cli profile: {profile_id}")
    profile = _load_yaml(path)
    profile.setdefault("id", profile_id)
    return profile


def load_all_profiles() -> list[dict[str, Any]]:
    return [load_profile(pid) for pid in list_profile_ids()]


def _score_profile(profile: dict[str, Any], description: str) -> tuple[int, list[str]]:
    text = description.lower()
    score = 0
    reasons: list[str] = []

    for phrase in profile.get("good_for", []):
        tokens = [t for t in re.split(r"[^a-z0-9]+", phrase.lower()) if len(t) > 3]
        hits = sum(1 for t in tokens if t in text)
        if hits:
            score += hits * 2
            reasons.append(f"good_for:{phrase}")

    for phrase in profile.get("avoid_for", []):
        tokens = [t for t in re.split(r"[^a-z0-9]+", phrase.lower()) if len(t) > 3]
        hits = sum(1 for t in tokens if t in text)
        if hits:
            score -= hits * 3
            reasons.append(f"avoid_for:{phrase}")

    for tag in profile.get("tags", []):
        if tag.lower() in text:
            score += 1
            reasons.append(f"tag:{tag}")

    # Light priors for common verbs
    if "plan" in text or "implement" in text:
        if profile.get("id") in {"codex", "agy"}:
            score += 2
            reasons.append("prior:plan-implementation")
    if "mcp" in text or "orchestrat" in text:
        if profile.get("id") in {"hermes", "grok"}:
            score += 2
            reasons.append("prior:orchestration")
    if "opencode" in text or "subagent" in text:
        if profile.get("id") == "opencode":
            score += 3
            reasons.append("prior:opencode-mention")

    return score, reasons


def suggest_cli_for_task(
    description: str,
    *,
    exclude_kinds: list[str] | None = None,
    top_n: int = 3,
) -> dict[str, Any]:
    """Rank CLI profiles for a natural-language task description."""
    exclude = set(exclude_kinds or [])
    ranked: list[tuple[int, dict[str, Any], list[str]]] = []
    for profile in load_all_profiles():
        if profile.get("kind") in exclude:
            continue
        score, reasons = _score_profile(profile, description)
        ranked.append((score, profile, reasons))

    ranked.sort(key=lambda x: x[0], reverse=True)
    suggestions = []
    for score, profile, reasons in ranked[:top_n]:
        suggestions.append(
            {
                "profile_id": profile.get("id"),
                "display_name": profile.get("display_name"),
                "kind": profile.get("kind"),
                "score": score,
                "reasons": reasons[:6],
                "parallel_lane_id": profile.get("parallel_lane_id"),
                "invoke_one_shot": (profile.get("invoke") or {}).get("one_shot"),
            }
        )

    best = suggestions[0] if suggestions and suggestions[0]["score"] > 0 else None
    return {
        "profiles_dir": str(profiles_dir()),
        "description": description,
        "suggested": best,
        "alternatives": suggestions[1:] if best else suggestions,
        "all_ranked": suggestions,
    }