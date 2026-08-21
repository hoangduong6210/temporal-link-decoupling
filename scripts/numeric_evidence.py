#!/usr/bin/env python3
"""Strict numeric-literal to checksum-owned JSON scalar verification.

The publication gate intentionally supports a small, deterministic selector
language.  It never evaluates expressions: derived values must already be
materialized in a frozen JSON artifact.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import json
from pathlib import Path
import re
from typing import Any, Mapping


NUMBER_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?:\s*(?:%|pp))?"
    r"(?![A-Za-z0-9_])"
)
LITERAL = re.compile(
    r"(?P<number>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?:\s*(?P<unit>%|pp))?"
)
SELECTOR = re.compile(
    r"\$(?:\.[A-Za-z_][A-Za-z0-9_-]*|\[(?:0|[1-9]\d*)\])+"
)
SELECTOR_STEP = re.compile(r"\.([A-Za-z_][A-Za-z0-9_-]*)|\[((?:0|[1-9]\d*))\]")
AMBIGUOUS_NUMERIC_TEXT = (
    (re.compile(r"(?<![0-9])\.[0-9]"), "leading-dot decimal"),
    (re.compile(r"[−–—]\s*[0-9]"), "Unicode minus/dash numeric sign"),
    (re.compile(r"(?<![A-Za-z0-9_])[0-9]{1,3}(?:,[0-9]{3})+(?![A-Za-z0-9_])"), "grouped numeric literal"),
)
COMPUTED_FIELDS = {
    "resolved_artifact_value",
    "transformed_artifact_value",
    "effective_quantum",
    "verified_value_mode",
}


class NumericEvidenceError(ValueError):
    """A numeric occurrence cannot be proved from its declared artifact."""


def reject_ambiguous_numeric_text(text: str, label: str) -> None:
    for pattern, description in AMBIGUOUS_NUMERIC_TEXT:
        if pattern.search(text):
            raise NumericEvidenceError(f"unsupported {description} in {label}")


def _reject_constant(value: str) -> None:
    raise NumericEvidenceError(f"non-finite JSON constant: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise NumericEvidenceError(f"duplicate JSON object key: {key}")
        output[key] = value
    return output


def load_decimal_json(path: Path) -> Any:
    if path.suffix.lower() != ".json":
        raise NumericEvidenceError("numeric evidence artifact must be a JSON file")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_int=Decimal,
            parse_float=Decimal,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidOperation) as exc:
        raise NumericEvidenceError(f"invalid numeric evidence JSON {path}: {exc}") from exc


def resolve_selector(payload: Any, selector: str) -> Decimal:
    if not isinstance(selector, str) or SELECTOR.fullmatch(selector) is None:
        raise NumericEvidenceError(f"unsupported artifact selector: {selector!r}")
    value = payload
    cursor = 1
    for match in SELECTOR_STEP.finditer(selector, cursor):
        if match.start() != cursor:
            raise NumericEvidenceError(f"non-canonical artifact selector: {selector}")
        key, index = match.groups()
        if key is not None:
            if not isinstance(value, dict) or key not in value:
                raise NumericEvidenceError(f"artifact selector key is missing: {key}")
            value = value[key]
        else:
            if not isinstance(value, list):
                raise NumericEvidenceError("artifact selector index targets a non-array")
            offset = int(index)
            if offset >= len(value):
                raise NumericEvidenceError(f"artifact selector index is out of range: {offset}")
            value = value[offset]
        cursor = match.end()
    if cursor != len(selector):
        raise NumericEvidenceError(f"non-canonical artifact selector: {selector}")
    if isinstance(value, bool) or not isinstance(value, Decimal) or not value.is_finite():
        raise NumericEvidenceError("artifact selector does not resolve to one finite numeric scalar")
    return value


def _literal_parts(literal: str) -> tuple[Decimal, str | None, str]:
    match = LITERAL.fullmatch(literal)
    if match is None:
        raise NumericEvidenceError(f"unsupported numeric literal: {literal!r}")
    number_text = match.group("number")
    try:
        value = Decimal(number_text)
    except InvalidOperation as exc:
        raise NumericEvidenceError(f"invalid numeric literal: {literal!r}") from exc
    if not value.is_finite():
        raise NumericEvidenceError(f"non-finite numeric literal: {literal!r}")
    return value, match.group("unit"), number_text


def _transform(value: Decimal, transform: str, unit: str | None) -> Decimal:
    expected = {
        None: "identity",
        "%": "fraction-to-percent",
        "pp": "fraction-to-pp",
    }[unit]
    if transform != expected:
        raise NumericEvidenceError(
            f"numeric unit requires transform={expected}, got {transform!r}"
        )
    return value if transform == "identity" else value * Decimal(100)


def verify_numeric_assertion(
    *,
    artifact: Path,
    selector: str,
    literal: str,
    assertion: Mapping[str, Any] | None,
) -> dict[str, str]:
    """Resolve and compare a paper literal, returning builder-owned audit fields."""

    selected = resolve_selector(load_decimal_json(artifact), selector)
    literal_value, unit, number_text = _literal_parts(literal)
    spec = dict(assertion or {"mode": "exact", "transform": "identity"})
    mode = spec.get("mode", "exact")
    transform = spec.get("transform", "identity")
    if set(spec) - {"mode", "transform", "decimal_places", "rounding"}:
        raise NumericEvidenceError("numeric value_assertion contains unsupported fields")
    if not isinstance(transform, str):
        raise NumericEvidenceError("numeric transform must be a string")
    transformed = _transform(selected, transform, unit)
    quantum: Decimal | None = None
    if mode == "exact":
        if "decimal_places" in spec or "rounding" in spec:
            raise NumericEvidenceError("exact numeric assertion may not declare rounding")
        compared = transformed
    elif mode == "rounded":
        places = spec.get("decimal_places")
        if isinstance(places, bool) or not isinstance(places, int) or not 0 <= places <= 15:
            raise NumericEvidenceError("rounded assertion decimal_places must be an integer in [0,15]")
        if spec.get("rounding", "half-even") != "half-even":
            raise NumericEvidenceError("only half-even publication rounding is supported")
        mantissa = re.split(r"[eE]", number_text, maxsplit=1)[0]
        literal_places = len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
        if literal_places != places:
            raise NumericEvidenceError(
                f"literal precision {literal_places} disagrees with decimal_places={places}"
            )
        exponent = int(re.split(r"[eE]", number_text, maxsplit=1)[1]) if re.search(r"[eE]", number_text) else 0
        quantum = Decimal(1).scaleb(exponent - places)
        compared = transformed.quantize(quantum, rounding=ROUND_HALF_EVEN)
    else:
        raise NumericEvidenceError(f"unsupported numeric value assertion mode: {mode!r}")
    if compared != literal_value:
        raise NumericEvidenceError(
            f"paper literal {literal!r} does not match selected artifact value {selected}"
        )
    result = {
        "resolved_artifact_value": str(selected),
        "transformed_artifact_value": str(transformed),
        "verified_value_mode": str(mode),
    }
    if quantum is not None:
        result["effective_quantum"] = str(quantum)
    return result

