"""Check a summary.json against the schema and the source rules.

Usage: validate.py <summary.json>

Prints one error per line as `path.to.field: message` on stderr and exits 1 when anything is
wrong. The schema is `../schema/summary.schema.json`. Only a small subset of JSON Schema is
supported (see the $comment in the schema file).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "summary.schema.json"
SRC_SEPARATOR = " > "


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def type_name(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    return "number"


def _type_matches(value: object, expected: str) -> bool:
    actual = type_name(value)
    return actual == expected or (expected == "number" and actual == "integer")


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _check(value: object, schema: dict, path: str, errors: list[str]) -> None:
    label = path or "$"
    expected = schema.get("type")
    if expected and not _type_matches(value, expected):
        errors.append(f"{label}: expected {expected}, got {type_name(value)}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{label}: must be one of {', '.join(map(str, schema['enum']))}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{label}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{label}: longer than {schema['maxLength']} characters")

    elif isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{_join(path, key)}: missing required field")
        for key, child in value.items():
            if key in properties:
                _check(child, properties[key], _join(path, key), errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{_join(path, key)}: unknown field")

    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{label}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{label}: has more than {schema['maxItems']} items")
        if "items" in schema:
            for index, child in enumerate(value):
                _check(child, schema["items"], f"{path}[{index}]", errors)


def _find_src(value: object, path: str):
    """Yield (path, text) for every string stored under a key named `src`."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = _join(path, key)
            if key == "src" and isinstance(child, str):
                yield child_path, child
            else:
                yield from _find_src(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _find_src(child, f"{path}[{index}]")


def _check_sources(data: dict, errors: list[str]) -> None:
    sources = data.get("sources")
    if not isinstance(sources, list):
        return
    listed = {s["path"] for s in sources if isinstance(s, dict) and isinstance(s.get("path"), str)}
    for path, text in _find_src(data, ""):
        file_part, separator, heading = text.partition(SRC_SEPARATOR)
        if not separator or not file_part.strip() or not heading.strip():
            errors.append(f'{path}: must look like "<file> > <heading>"')
        elif file_part not in listed:
            errors.append(f'{path}: "{file_part}" is not listed in sources')


def validate(data: object, schema: dict | None = None) -> list[str]:
    """Return a list of error messages. An empty list means the data is valid."""
    errors: list[str] = []
    _check(data, schema or load_schema(), "", errors)
    if isinstance(data, dict):
        _check_sources(data, errors)
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: validate.py <summary.json>", file=sys.stderr)
        return 1
    path = Path(argv[0])
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"{argv[0]}: file not found", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"{argv[0]}: invalid JSON: {exc}", file=sys.stderr)
        return 1
    errors = validate(data)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
