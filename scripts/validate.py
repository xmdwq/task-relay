#!/usr/bin/env python3
"""Validate the task-relay skill using only the Python standard library."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote


REQUIRED_STATE_KEYS = {
    "schema_version",
    "task_id",
    "goal",
    "acceptance_criteria",
    "constraints",
    "decisions",
    "completed",
    "unverified",
    "remaining",
    "blockers",
    "artifacts",
    "authorization_notes",
    "next_action",
    "updated_at",
}

ARRAY_KEYS = {
    "acceptance_criteria",
    "constraints",
    "decisions",
    "completed",
    "unverified",
    "remaining",
    "blockers",
    "artifacts",
    "authorization_notes",
}

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---", re.DOTALL)
JSON_FENCE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
SECRET_VALUE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key|password)"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"
)


def load_json(path: Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
    return None


def validate_state(data: Any, label: str, errors: list[str]) -> None:
    if not isinstance(data, dict):
        errors.append(f"{label}: state must be a JSON object")
        return

    missing = sorted(REQUIRED_STATE_KEYS - data.keys())
    if missing:
        errors.append(f"{label}: missing required keys: {', '.join(missing)}")

    if data.get("schema_version") != "1.0":
        errors.append(f"{label}: schema_version must be '1.0'")

    for key in sorted(ARRAY_KEYS):
        if key in data and not isinstance(data[key], list):
            errors.append(f"{label}: {key} must be an array")

    next_action = data.get("next_action")
    if next_action is not None:
        if not isinstance(next_action, dict):
            errors.append(f"{label}: next_action must be null or an object")
        else:
            needed = {"action", "complete_when", "prerequisites"}
            absent = sorted(needed - next_action.keys())
            if absent:
                errors.append(
                    f"{label}: next_action is missing: {', '.join(absent)}"
                )
            if "prerequisites" in next_action and not isinstance(
                next_action["prerequisites"], list
            ):
                errors.append(f"{label}: next_action.prerequisites must be an array")


def validate_skill_frontmatter(root: Path, errors: list[str]) -> None:
    skill = root / "SKILL.md"
    if not skill.exists():
        errors.append("SKILL.md is missing")
        return

    text = skill.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        errors.append("SKILL.md has invalid YAML frontmatter boundaries")
        return

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip():
            values[key.strip()] = value.strip()

    if values.get("name") != "task-relay":
        errors.append("SKILL.md frontmatter name must be task-relay")
    if not values.get("description"):
        errors.append("SKILL.md frontmatter description is missing")
    if re.search(r"(?m)^ {0,3}\[TODO:[^\n]*\]\s*$", text[match.end() :]):
        errors.append("SKILL.md contains an unfinished TODO placeholder")


def validate_links(root: Path, errors: list[str]) -> None:
    for markdown in sorted(root.rglob("*.md")):
        text = markdown.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            resolved = (markdown.parent / target).resolve()
            if not resolved.exists():
                errors.append(
                    f"broken relative link in {markdown.relative_to(root)}: {raw_target}"
                )


def validate_examples(root: Path, errors: list[str]) -> None:
    example = root / "examples" / "writing-handoff.md"
    if not example.exists():
        errors.append("examples/writing-handoff.md is missing")
        return

    text = example.read_text(encoding="utf-8")
    blocks = JSON_FENCE.findall(text)
    if not blocks:
        errors.append("writing example has no fenced JSON state")
        return

    for index, block in enumerate(blocks, start=1):
        try:
            data = json.loads(block)
        except json.JSONDecodeError as exc:
            errors.append(f"writing example JSON block {index} is invalid: {exc}")
            continue
        if isinstance(data, dict) and "schema_version" in data:
            validate_state(data, f"writing example JSON block {index}", errors)

    required_phrases = (
        "动作 A：生成交接",
        "新智能体读取并恢复",
        "继续完成",
        "更新后的接力点",
        "本地模拟",
        "不是跨智能体集成测试",
    )
    for phrase in required_phrases:
        if phrase not in text:
            errors.append(f"writing example is missing phase label: {phrase}")

    development = root / "examples" / "development-handoff.md"
    if not development.exists():
        errors.append("examples/development-handoff.md is missing")
        return

    development_text = development.read_text(encoding="utf-8")
    development_blocks = JSON_FENCE.findall(development_text)
    if not development_blocks:
        errors.append("development example has no fenced JSON state")
    for index, block in enumerate(development_blocks, start=1):
        try:
            data = json.loads(block)
        except json.JSONDecodeError as exc:
            errors.append(f"development example JSON block {index} is invalid: {exc}")
            continue
        if isinstance(data, dict) and "schema_version" in data:
            validate_state(data, f"development example JSON block {index}", errors)

    development_phrases = (
        "动作 A：生成交接",
        "新智能体读取并恢复",
        "继续完成安全范围内的工作",
        "更新接力点",
        "本地模拟",
        "无法确认时不重复部署",
    )
    for phrase in development_phrases:
        if phrase not in development_text:
            errors.append(f"development example is missing phase label: {phrase}")


def scan_secret_values(root: Path, errors: list[str]) -> None:
    text_suffixes = {".md", ".json", ".py", ".yml", ".yaml", ".txt"}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        if SECRET_VALUE.search(text):
            errors.append(f"possible embedded secret value in {path.relative_to(root)}")


def validate_license(root: Path, errors: list[str]) -> None:
    license_path = root / "LICENSE"
    if not license_path.exists():
        errors.append("LICENSE is missing")
        return

    text = license_path.read_text(encoding="utf-8")
    required_phrases = (
        "MIT License",
        "Copyright (c) 2026 task-relay contributors",
        "Permission is hereby granted, free of charge",
        'THE SOFTWARE IS PROVIDED "AS IS"',
    )
    for phrase in required_phrases:
        if phrase not in text:
            errors.append(f"LICENSE is missing expected MIT text: {phrase}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        action="append",
        default=[],
        type=Path,
        help="additional task-state.json file to validate; may be repeated",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    validate_skill_frontmatter(root, errors)

    schema = load_json(root / "schemas" / "task-state.schema.json", errors)
    if isinstance(schema, dict):
        schema_required = set(schema.get("required", []))
        if schema_required != REQUIRED_STATE_KEYS:
            errors.append("JSON Schema required keys do not match the Skill contract")

    template_path = root / "templates" / "task-state.json"
    template = load_json(template_path, errors)
    if template is not None:
        validate_state(template, str(template_path.relative_to(root)), errors)

    for state_path in args.state:
        data = load_json(state_path, errors)
        if data is not None:
            validate_state(data, str(state_path), errors)

    validate_links(root, errors)
    validate_examples(root, errors)
    validate_license(root, errors)
    scan_secret_values(root, errors)

    if errors:
        print("task-relay validation: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("task-relay validation: PASS")
    print(f"- required state keys: {len(REQUIRED_STATE_KEYS)}")
    print("- template JSON: valid")
    print("- JSON Schema: parsed and aligned")
    print("- Markdown links: valid")
    print("- writing and development relay simulations: complete")
    print("- MIT License: present")
    print("- likely embedded secret values: none found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
