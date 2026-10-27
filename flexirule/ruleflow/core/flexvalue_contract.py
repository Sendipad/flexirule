# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Strict FlexValue validation and safe resolution for canonical conditions.

This module intentionally does not tighten the legacy ValueResolver API. Canonical
conditions enter through these explicit functions and use only declared capabilities.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from flexirule.ruleflow.core.condition_errors import ConditionEvaluationError, ConditionValidationError

BASE_SCOPES = frozenset({
	"doc", "old_doc", "vars", "item", "loop", "row", "caller", "rule", "doctype"
})

MAX_CONDITION_DEPTH = 32
MAX_CONDITION_NODES = 1000
MAX_RESOLVER_DEPTH = 16
MAX_FLEXVALUE_DEPTH = 32
MAX_PATH_SEGMENTS = 32
MAX_TEMPLATE_SEGMENTS = 1000
MAX_TEMPLATE_OUTPUT_CHARS = 1_000_000
MAX_CONDITION_PAYLOAD_BYTES = 1_000_000
MAX_COLLECTION_ROWS = 10000
MAX_STATIC_ITEMS = 10000

CONDITION_LIMITS = {
	"condition_depth": MAX_CONDITION_DEPTH,
	"condition_nodes": MAX_CONDITION_NODES,
	"resolver_depth": MAX_RESOLVER_DEPTH,
	"flexvalue_depth": MAX_FLEXVALUE_DEPTH,
	"path_segments": MAX_PATH_SEGMENTS,
	"template_segments": MAX_TEMPLATE_SEGMENTS,
	"template_output_chars": MAX_TEMPLATE_OUTPUT_CHARS,
	"payload_bytes": MAX_CONDITION_PAYLOAD_BYTES,
	"collection_rows": MAX_COLLECTION_ROWS,
	"static_items": MAX_STATIC_ITEMS,
}

VALUE_TYPES = frozenset({
	"string", "integer", "decimal", "boolean", "null",
	"date", "datetime", "time", "list", "object",
})

# Resolver operations are deny-by-default. Adding an entry requires a reviewed,
# deterministic, read-only implementation and explicit config/output validation.
CONDITION_RESOLVER_REGISTRY: dict[tuple[str, str], dict[str, Any]] = {}


def register_condition_resolver(
	family: str,
	operation: str,
	*,
	label: str,
	output_type: str,
	config_schema: dict[str, Any],
	permission_policy: str,
	validate_config: Callable[[dict, str, set[str], int, int], None],
	resolve: Callable[[dict, dict], Any],
	condition_operand_allowed: bool = False,
	required_capability: str = "condition_operand",
):
	"""Register a reviewed resolver operation for canonical conditions.

	validate_config must validate exact keys and nested FlexValues, carrying both the
	current resolver depth and FlexValue depth into validate_flex_value(). resolve must
	be read-only, bounded, deterministic for a given context, and must not cache context
	or resolved values. An operation may only be enabled when its permission policy is
	"no_data_access"; database-backed resolvers require a separately reviewed adapter.
	"""
	if (
		not isinstance(family, str)
		or not family
		or not isinstance(operation, str)
		or not operation
		or not isinstance(label, str)
		or not label
		or not isinstance(output_type, str)
		or output_type not in VALUE_TYPES
		or not isinstance(config_schema, dict)
		or not isinstance(permission_policy, str)
		or not permission_policy
		or not isinstance(required_capability, str)
		or not required_capability
	):
		raise ValueError("Invalid canonical condition resolver registration")
	try:
		json.dumps(config_schema, sort_keys=True, allow_nan=False)
	except (TypeError, ValueError) as exc:
		raise ValueError("Resolver config_schema must be JSON-serializable") from exc
	if not callable(validate_config) or not callable(resolve):
		raise ValueError("Resolver validators and resolvers must be callable")
	if condition_operand_allowed and permission_policy != "no_data_access":
		raise ValueError(
			"Condition operands may only enable resolvers with permission_policy='no_data_access'"
		)
	key = (family, operation)
	if key in CONDITION_RESOLVER_REGISTRY:
		raise ValueError(f"Canonical condition resolver already registered: {family}.{operation}")
	CONDITION_RESOLVER_REGISTRY[key] = {
		"family": family,
		"operation": operation,
		"label": label,
		"output_type": output_type,
		"config_schema": config_schema,
		"permission_policy": permission_policy,
		"required_capability": required_capability,
		"condition_operand_allowed": bool(condition_operand_allowed),
		"validate_config": validate_config,
		"resolve": resolve,
	}


def resolver_registry_fingerprint() -> str:
	"""Stable cache key material; implementation callables stay private."""
	payload = json.dumps(
		resolver_contract_dto(),
		sort_keys=True,
		ensure_ascii=False,
		separators=(",", ":"),
		allow_nan=False,
	)
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolver_contract_dto() -> list[dict[str, Any]]:
	"""Return public metadata only; internal functions are never exposed."""
	return [
		{
			"family": item["family"],
			"operation": item["operation"],
			"label": item["label"],
			"output_type": item["output_type"],
			"config_schema": item["config_schema"],
			"permission_policy": item["permission_policy"],
			"required_capability": item["required_capability"],
			"condition_operand_allowed": bool(item["condition_operand_allowed"]),
		}
		for _, item in sorted(CONDITION_RESOLVER_REGISTRY.items())
	]


def _fail(code: str, path: str, message: str) -> None:
	raise ConditionValidationError(code, path, message)


def _exact_keys(value: Mapping, required: set[str], optional: set[str], path: str) -> None:
	if any(not isinstance(key, str) for key in value):
		_fail("invalid_key_type", path, "FlexValue object keys must be strings")
	missing = required - set(value)
	unknown = set(value) - required - optional
	if missing:
		_fail("missing_key", path, f"Missing required key(s): {', '.join(sorted(missing))}")
	if unknown:
		_fail("unknown_key", path, f"Unknown key(s): {', '.join(sorted(unknown))}")


def _validate_json_value(value: Any, path: str, depth: int = 0) -> None:
	if depth > MAX_RESOLVER_DEPTH:
		_fail("static_value_too_deep", path, "Nested static value exceeds the configured depth limit")
	if value is None or type(value) in (str, bool, int):
		return
	if isinstance(value, float):
		if not math.isfinite(value):
			_fail("non_finite_number", path, "Static numbers must be finite")
		return
	if isinstance(value, list):
		if len(value) > MAX_STATIC_ITEMS:
			_fail("static_value_too_large", path, "Static list exceeds the configured item limit")
		for index, child in enumerate(value):
			_validate_json_value(child, f"{path}[{index}]", depth + 1)
		return
	if isinstance(value, dict):
		if len(value) > MAX_STATIC_ITEMS:
			_fail("static_value_too_large", path, "Static object exceeds the configured item limit")
		for key, child in value.items():
			if not isinstance(key, str):
				_fail("invalid_object_key", path, "Static object keys must be strings")
			_validate_json_value(child, f"{path}.{key}", depth + 1)
		return
	_fail("invalid_static_value", path, "Static object contains a non-JSON value")


def _validate_path(path_value: Any, path: str, allowed_scopes: set[str]) -> tuple[str, tuple[str, ...]]:
	if not isinstance(path_value, Mapping):
		_fail("invalid_path", path, "Path must be an object")
	_exact_keys(path_value, {"scope", "segments"}, set(), path)
	scope = path_value.get("scope")
	segments = path_value.get("segments")
	if not isinstance(scope, str) or scope not in allowed_scopes:
		_fail("unknown_scope", f"{path}.scope", "Path scope is not available in this context")
	if not isinstance(segments, list) or len(segments) > MAX_PATH_SEGMENTS:
		_fail("invalid_path_segments", f"{path}.segments", "Path segments must be a bounded list")
	if scope != "doctype" and not segments:
		_fail("invalid_path_segments", f"{path}.segments", "A variable path must name at least one segment")
	if scope == "doctype" and segments:
		_fail("invalid_path_segments", f"{path}.segments", "The doctype scope does not accept path segments")
	for index, segment in enumerate(segments):
		if (
			not isinstance(segment, str)
			or not segment
			or not re.fullmatch(r"[A-Za-z0-9_]+", segment)
			or "__" in segment
		):
			_fail("invalid_path_segment", f"{path}.segments[{index}]", "Unsafe or empty path segment")
	return scope, tuple(segments)


def infer_flex_value_type(value: Any, *, resolver_depth: int = 0) -> str | None:
	"""Return the statically known output type, or None for a variable."""
	if not isinstance(value, Mapping):
		return None
	mode = value.get("mode")
	if mode == "static":
		return value.get("value_type")
	if mode == "variable":
		return None
	if mode == "template":
		return "string"
	if mode == "resolver":
		if resolver_depth > MAX_RESOLVER_DEPTH:
			return None
		entry = CONDITION_RESOLVER_REGISTRY.get((value.get("family"), value.get("operation")))
		return entry.get("output_type") if entry else None
	return None


def validate_flex_value(
	value: Any,
	*,
	path: str = "$",
	allowed_scopes: set[str] | None = None,
	resolver_depth: int = 0,
	flexvalue_depth: int = 0,
) -> str | None:
	"""Validate one canonical FlexValue without mutating it; return known output type."""
	if flexvalue_depth > MAX_FLEXVALUE_DEPTH:
		_fail("flexvalue_depth_exceeded", path, "Nested FlexValue exceeds the configured depth limit")
	if not isinstance(value, Mapping):
		_fail("invalid_flex_value", path, "FlexValue must be an object")
	allowed = set(allowed_scopes or BASE_SCOPES)
	mode = value.get("mode")

	if mode == "static":
		_exact_keys(value, {"mode", "value_type", "value"}, set(), path)
		value_type = value.get("value_type")
		val = value.get("value")
		if not isinstance(value_type, str) or value_type not in VALUE_TYPES:
			_fail("unknown_value_type", f"{path}.value_type", "Unsupported static value type")
		if value_type == "string" and not isinstance(val, str):
			_fail("invalid_static_type", f"{path}.value", "Expected a string")
		elif value_type == "integer" and type(val) is not int:
			_fail("invalid_static_type", f"{path}.value", "Expected an integer (not a boolean)")
		elif value_type == "decimal":
			if not isinstance(val, str):
				_fail("invalid_static_type", f"{path}.value", "Decimal values must be serialized as strings")
			try:
				number = Decimal(val)
			except (InvalidOperation, ValueError):
				_fail("invalid_decimal", f"{path}.value", "Decimal value is not valid")
			if not number.is_finite():
				_fail("invalid_decimal", f"{path}.value", "Decimal value must be finite")
		elif value_type == "boolean" and type(val) is not bool:
			_fail("invalid_static_type", f"{path}.value", "Expected a boolean")
		elif value_type == "null" and val is not None:
			_fail("invalid_static_type", f"{path}.value", "Null values must be JSON null")
		elif value_type == "date":
			if not isinstance(val, str):
				_fail("invalid_static_type", f"{path}.value", "Dates must be ISO strings")
			try:
				if date.fromisoformat(val).isoformat() != val:
					raise ValueError
			except ValueError:
				_fail("invalid_date", f"{path}.value", "Expected an ISO date in YYYY-MM-DD format")
		elif value_type == "datetime":
			if not isinstance(val, str):
				_fail("invalid_static_type", f"{path}.value", "Datetimes must be ISO strings")
			try:
				datetime.fromisoformat(val[:-1] + "+00:00" if val.endswith("Z") else val)
			except ValueError:
				_fail("invalid_datetime", f"{path}.value", "Expected a valid ISO datetime")
		elif value_type == "time":
			if not isinstance(val, str):
				_fail("invalid_static_type", f"{path}.value", "Times must be ISO strings")
			try:
				time.fromisoformat(val)
			except ValueError:
				_fail("invalid_time", f"{path}.value", "Expected a valid ISO time")
		elif value_type in {"list", "object"}:
			if value_type == "list" and not isinstance(val, list):
				_fail("invalid_static_type", f"{path}.value", "Expected a list")
			if value_type == "object" and not isinstance(val, dict):
				_fail("invalid_static_type", f"{path}.value", "Expected an object")
			_validate_json_value(val, f"{path}.value")
		return str(value_type)

	if mode == "variable":
		_exact_keys(value, {"mode", "path"}, set(), path)
		_validate_path(value.get("path"), f"{path}.path", allowed)
		return None

	if mode == "resolver":
		_exact_keys(value, {"mode", "family", "operation", "config"}, set(), path)
		if not isinstance(value.get("family"), str) or not value.get("family"):
			_fail("invalid_resolver_family", f"{path}.family", "Resolver family is required")
		if not isinstance(value.get("operation"), str) or not value.get("operation"):
			_fail("invalid_resolver_operation", f"{path}.operation", "Resolver operation is required")
		if resolver_depth >= MAX_RESOLVER_DEPTH:
			_fail("resolver_depth_exceeded", path, "Resolver nesting exceeds the configured limit")
		entry = CONDITION_RESOLVER_REGISTRY.get((value["family"], value["operation"]))
		if not entry or not entry.get("condition_operand_allowed"):
			_fail("resolver_not_allowed", path, "Resolver operation is not approved as a condition operand")
		config = value.get("config")
		if not isinstance(config, dict):
			_fail("invalid_resolver_config", f"{path}.config", "Resolver config must be an object")
		entry["validate_config"](
			config, f"{path}.config", allowed, resolver_depth + 1, flexvalue_depth + 1
		)
		return entry["output_type"]

	if mode == "template":
		_exact_keys(value, {"mode", "segments"}, set(), path)
		segments = value.get("segments")
		if not isinstance(segments, list) or not segments or len(segments) > MAX_TEMPLATE_SEGMENTS:
			_fail("invalid_template_segments", f"{path}.segments", "Template segments must be a non-empty bounded list")
		for index, segment in enumerate(segments):
			segment_path = f"{path}.segments[{index}]"
			if not isinstance(segment, Mapping):
				_fail("invalid_template_segment", segment_path, "Template segment must be an object")
			if segment.get("type") == "text":
				_exact_keys(segment, {"type", "value"}, set(), segment_path)
				if not isinstance(segment.get("value"), str):
					_fail("invalid_template_text", f"{segment_path}.value", "Text segment value must be a string")
			elif segment.get("type") == "value":
				_exact_keys(segment, {"type", "value"}, set(), segment_path)
				output_type = validate_flex_value(
					segment.get("value"),
					path=f"{segment_path}.value",
					allowed_scopes=allowed,
					resolver_depth=resolver_depth,
					flexvalue_depth=flexvalue_depth + 1,
				)
				if output_type in {"list", "object"}:
					_fail("invalid_template_value_type", f"{segment_path}.value", "Template values must be scalar")
			else:
				_fail("unknown_template_segment", f"{segment_path}.type", "Expected text or value segment")
		return "string"

	_fail("unknown_flex_value_mode", f"{path}.mode", "Unsupported FlexValue mode")


def parse_static_value(value_type: str, value: Any) -> Any:
	"""Convert a validated static payload to its typed runtime representation."""
	if value_type == "decimal":
		return Decimal(value)
	if value_type == "date":
		return date.fromisoformat(value)
	if value_type == "datetime":
		return datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
	if value_type == "time":
		return time.fromisoformat(value)
	return value


def safe_read_segment(value: Any, segment: str) -> Any:
	"""Read a mapping key or Frappe Document field without arbitrary attribute access."""
	if isinstance(value, Mapping):
		return value.get(segment, MISSING)
	if getattr(value, "doctype", None) and callable(getattr(value, "get", None)):
		if segment == "name":
			return getattr(value, "name", MISSING)
		try:
			meta = getattr(value, "meta", None)
			if meta is not None and meta.has_field(segment):
				return value.get(segment)
		except Exception:
			return MISSING
	return MISSING


def resolve_variable(scope: str, segments: tuple[str, ...], context: dict, path: str = "$") -> Any:
	"""Resolve an explicit scope/path. Missing never falls back to another scope."""
	if scope not in context:
		return MISSING
	value = context[scope]
	for segment in segments:
		value = safe_read_segment(value, segment)
		if value is MISSING:
			return MISSING
	return value


def format_template_value(value: Any, path: str = "$") -> str:
	"""Format only explicitly supported scalar values; do not coerce arbitrary objects."""
	if value is None:
		return ""
	if type(value) is bool:
		return "true" if value else "false"
	if isinstance(value, str):
		return value
	if type(value) is int:
		return str(value)
	if isinstance(value, Decimal):
		return format(value, "f")
	if isinstance(value, (date, datetime, time)):
		return value.isoformat()
	if isinstance(value, float) and math.isfinite(value):
		return str(value)
	raise ConditionEvaluationError(
		"invalid_template_runtime_type", path, "Template segment resolved to a non-scalar value"
	)


class _Missing:
	"""Unique sentinel used to distinguish missing paths from an explicit null."""

	def __repr__(self):
		return "MISSING"


MISSING = _Missing()
