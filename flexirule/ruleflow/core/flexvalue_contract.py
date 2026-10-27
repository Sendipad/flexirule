# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from flexirule.ruleflow.core.exceptions import RuleEngineError

# Central resource limits
MAX_CONDITION_DEPTH = 32
MAX_CONDITION_NODES = 1000
MAX_RESOLVER_NESTING = 16
MAX_PATH_SEGMENTS = 32
MAX_TEMPLATE_SEGMENTS = 1000
MAX_COLLECTION_ROWS = 10000

CANONICAL_SCOPES = {
	"doc",
	"old_doc",
	"vars",
	"item",
	"loop",
	"row",
	"caller",
	"rule",
	"doctype",
}

VALID_VALUE_TYPES = {
	"string",
	"integer",
	"decimal",
	"boolean",
	"null",
	"date",
	"datetime",
	"time",
	"list",
	"object",
}

ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_TIME_REGEX = re.compile(r"^\d{2}:\d{2}(:\d{2}(\.\d+)?)?$")
ISO_DATETIME_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$")


class FlexValueError(RuleEngineError):
	"""Raised when a FlexValue contract validation fails."""

	def __init__(self, message: str, code: str = "INVALID_FLEXVALUE", path: str = "$"):
		super().__init__(message)
		self.message = message
		self.code = code
		self.path = path

	def to_dict(self) -> dict[str, Any]:
		return {
			"error": self.message,
			"code": self.code,
			"path": self.path,
		}


def validate_flexvalue(
	data: Any,
	path: str = "$",
	resolver_depth: int = 0,
) -> None:
	"""
	Strictly validate a FlexValue payload according to the canonical contract.

	Rejects unknown keys (including transient 'id'), enforces mode-specific
	properties and types, and verifies resource limits. Does NOT mutate data.
	"""
	if not isinstance(data, dict):
		raise FlexValueError(
			f"FlexValue at '{path}' must be a dictionary, got {type(data).__name__}",
			code="TYPE_MISMATCH",
			path=path,
		)

	if "mode" not in data:
		raise FlexValueError(
			f"FlexValue at '{path}' is missing required key 'mode'",
			code="MISSING_KEY",
			path=path,
		)

	mode = data["mode"]
	if mode == "static":
		_validate_static_flexvalue(data, path)
	elif mode == "variable":
		_validate_variable_flexvalue(data, path)
	elif mode == "resolver":
		_validate_resolver_flexvalue(data, path, resolver_depth=resolver_depth)
	elif mode == "template":
		_validate_template_flexvalue(data, path, resolver_depth=resolver_depth)
	else:
		raise FlexValueError(
			f"Invalid FlexValue mode '{mode}' at '{path}'",
			code="INVALID_MODE",
			path=f"{path}.mode",
		)


def _validate_keys(data: dict, allowed_keys: set[str], path: str) -> None:
	extra_keys = set(data.keys()) - allowed_keys
	if extra_keys:
		key_str = ", ".join(sorted(extra_keys))
		raise FlexValueError(
			f"FlexValue at '{path}' contains unknown or forbidden key(s): {key_str}",
			code="UNKNOWN_KEY",
			path=path,
		)


def _validate_static_flexvalue(data: dict, path: str) -> None:
	_validate_keys(data, {"mode", "value_type", "value"}, path)

	if "value_type" not in data:
		raise FlexValueError(
			f"Static FlexValue at '{path}' missing required key 'value_type'",
			code="MISSING_KEY",
			path=f"{path}.value_type",
		)

	v_type = data["value_type"]
	if v_type not in VALID_VALUE_TYPES:
		raise FlexValueError(
			f"Static FlexValue at '{path}' has unknown value_type '{v_type}'",
			code="INVALID_VALUE_TYPE",
			path=f"{path}.value_type",
		)

	if "value" not in data:
		raise FlexValueError(
			f"Static FlexValue at '{path}' missing required key 'value'",
			code="MISSING_KEY",
			path=f"{path}.value",
		)

	val = data["value"]
	_validate_static_value_match(v_type, val, f"{path}.value")


def _validate_static_value_match(v_type: str, val: Any, path: str) -> None:
	if v_type == "null":
		if val is not None:
			raise FlexValueError(
				f"Value at '{path}' must be null for value_type 'null'",
				code="TYPE_MISMATCH",
				path=path,
			)
		return

	if val is None:
		raise FlexValueError(
			f"Value at '{path}' cannot be null for non-null value_type '{v_type}'",
			code="TYPE_MISMATCH",
			path=path,
		)

	if v_type == "string":
		if not isinstance(val, str):
			raise FlexValueError(
				f"Value at '{path}' must be string, got {type(val).__name__}",
				code="TYPE_MISMATCH",
				path=path,
			)
	elif v_type == "integer":
		if type(val) is not int:  # bool is subclass of int in Python
			raise FlexValueError(
				f"Value at '{path}' must be integer, got {type(val).__name__}",
				code="TYPE_MISMATCH",
				path=path,
			)
	elif v_type == "boolean":
		if type(val) is not bool:
			raise FlexValueError(
				f"Value at '{path}' must be boolean, got {type(val).__name__}",
				code="TYPE_MISMATCH",
				path=path,
			)
	elif v_type == "decimal":
		if isinstance(val, (int, float)) and type(val) is not bool:
			val = str(val)
		if not isinstance(val, str) and not isinstance(val, Decimal):
			raise FlexValueError(
				f"Decimal value at '{path}' must be string or Decimal, got {type(val).__name__}",
				code="TYPE_MISMATCH",
				path=path,
			)
		try:
			Decimal(str(val))
		except (InvalidOperation, TypeError, ValueError):
			raise FlexValueError(
				f"Value '{val}' at '{path}' is not a valid Decimal representation",
				code="INVALID_DECIMAL",
				path=path,
			)
	elif v_type == "date":
		if not isinstance(val, str) or not ISO_DATE_REGEX.match(val):
			raise FlexValueError(
				f"Value at '{path}' must be an ISO date string (YYYY-MM-DD)",
				code="TYPE_MISMATCH",
				path=path,
			)
	elif v_type == "datetime":
		if not isinstance(val, str) or not ISO_DATETIME_REGEX.match(val):
			raise FlexValueError(
				f"Value at '{path}' must be an ISO datetime string",
				code="TYPE_MISMATCH",
				path=path,
			)
	elif v_type == "time":
		if not isinstance(val, str) or not ISO_TIME_REGEX.match(val):
			raise FlexValueError(
				f"Value at '{path}' must be an ISO time string (HH:MM:SS)",
				code="TYPE_MISMATCH",
				path=path,
			)
	elif v_type == "list":
		if type(val) is not list:
			raise FlexValueError(
				f"Value at '{path}' must be a list, got {type(val).__name__}",
				code="TYPE_MISMATCH",
				path=path,
			)
	elif v_type == "object":
		if type(val) is not dict:
			raise FlexValueError(
				f"Value at '{path}' must be an object (dict), got {type(val).__name__}",
				code="TYPE_MISMATCH",
				path=path,
			)


def _validate_variable_flexvalue(data: dict, path: str) -> None:
	_validate_keys(data, {"mode", "path"}, path)

	if "path" not in data:
		raise FlexValueError(
			f"Variable FlexValue at '{path}' missing required key 'path'",
			code="MISSING_KEY",
			path=f"{path}.path",
		)

	p_data = data["path"]
	p_path = f"{path}.path"
	if not isinstance(p_data, dict):
		raise FlexValueError(
			f"'path' at '{p_path}' must be a dict",
			code="TYPE_MISMATCH",
			path=p_path,
		)

	_validate_keys(p_data, {"scope", "segments"}, p_path)

	if "scope" not in p_data:
		raise FlexValueError(
			f"Path at '{p_path}' missing required key 'scope'",
			code="MISSING_KEY",
			path=f"{p_path}.scope",
		)

	scope = p_data["scope"]
	if not isinstance(scope, str) or not scope.strip():
		raise FlexValueError(
			f"Scope at '{p_path}.scope' must be a non-empty string",
			code="INVALID_SCOPE",
			path=f"{p_path}.scope",
		)

	if "segments" not in p_data:
		raise FlexValueError(
			f"Path at '{p_path}' missing required key 'segments'",
			code="MISSING_KEY",
			path=f"{p_path}.segments",
		)

	segments = p_data["segments"]
	seg_path = f"{p_path}.segments"
	if type(segments) is not list:
		raise FlexValueError(
			f"Segments at '{seg_path}' must be a list",
			code="TYPE_MISMATCH",
			path=seg_path,
		)

	if not segments:
		raise FlexValueError(
			f"Segments at '{seg_path}' cannot be empty",
			code="EMPTY_SEGMENTS",
			path=seg_path,
		)

	if len(segments) > MAX_PATH_SEGMENTS:
		raise FlexValueError(
			f"Segments count ({len(segments)}) at '{seg_path}' exceeds limit of {MAX_PATH_SEGMENTS}",
			code="LIMIT_EXCEEDED",
			path=seg_path,
		)

	for idx, seg in enumerate(segments):
		s_path = f"{seg_path}[{idx}]"
		if not isinstance(seg, str) or not seg.strip():
			raise FlexValueError(
				f"Path segment at '{s_path}' must be a non-empty string",
				code="INVALID_SEGMENT",
				path=s_path,
			)
		if seg.startswith("__") or "(" in seg or ")" in seg or "[" in seg or "]" in seg:
			raise FlexValueError(
				f"Path segment '{seg}' at '{s_path}' contains invalid syntax or dunder",
				code="FORBIDDEN_SEGMENT",
				path=s_path,
			)


def _validate_resolver_flexvalue(data: dict, path: str, resolver_depth: int) -> None:
	if resolver_depth >= MAX_RESOLVER_NESTING:
		raise FlexValueError(
			f"Resolver nesting at '{path}' exceeds limit of {MAX_RESOLVER_NESTING}",
			code="LIMIT_EXCEEDED",
			path=path,
		)

	_validate_keys(data, {"mode", "family", "operation", "config"}, path)

	for key in ("family", "operation"):
		if key not in data:
			raise FlexValueError(
				f"Resolver FlexValue at '{path}' missing required key '{key}'",
				code="MISSING_KEY",
				path=f"{path}.{key}",
			)
		val = data[key]
		if not isinstance(val, str) or not val.strip():
			raise FlexValueError(
				f"Resolver '{key}' at '{path}.{key}' must be a non-empty string",
				code="INVALID_RESOLVER",
				path=f"{path}.{key}",
			)

	if "config" not in data:
		raise FlexValueError(
			f"Resolver FlexValue at '{path}' missing required key 'config'",
			code="MISSING_KEY",
			path=f"{path}.config",
		)

	config = data["config"]
	if type(config) is not dict:
		raise FlexValueError(
			f"Resolver config at '{path}.config' must be a dictionary",
			code="TYPE_MISMATCH",
			path=f"{path}.config",
		)

	_validate_recursive_flexvalues_in_obj(config, f"{path}.config", resolver_depth=resolver_depth + 1)


def _validate_template_flexvalue(data: dict, path: str, resolver_depth: int) -> None:
	_validate_keys(data, {"mode", "segments"}, path)

	if "segments" not in data:
		raise FlexValueError(
			f"Template FlexValue at '{path}' missing required key 'segments'",
			code="MISSING_KEY",
			path=f"{path}.segments",
		)

	segments = data["segments"]
	seg_path = f"{path}.segments"
	if type(segments) is not list:
		raise FlexValueError(
			f"Template segments at '{seg_path}' must be a list",
			code="TYPE_MISMATCH",
			path=seg_path,
		)

	if len(segments) > MAX_TEMPLATE_SEGMENTS:
		raise FlexValueError(
			f"Template segment count ({len(segments)}) at '{seg_path}' exceeds limit of {MAX_TEMPLATE_SEGMENTS}",
			code="LIMIT_EXCEEDED",
			path=seg_path,
		)

	for idx, item in enumerate(segments):
		item_path = f"{seg_path}[{idx}]"
		if type(item) is not dict:
			raise FlexValueError(
				f"Template segment at '{item_path}' must be a dict",
				code="TYPE_MISMATCH",
				path=item_path,
			)

		if "type" not in item:
			raise FlexValueError(
				f"Template segment at '{item_path}' missing required key 'type'",
				code="MISSING_KEY",
				path=f"{item_path}.type",
			)

		t_type = item["type"]
		if t_type == "text":
			_validate_keys(item, {"type", "text"}, item_path)
			if "text" not in item or not isinstance(item["text"], str):
				raise FlexValueError(
					f"Text segment at '{item_path}' must have string 'text'",
					code="TYPE_MISMATCH",
					path=f"{item_path}.text",
				)
		elif t_type == "value":
			_validate_keys(item, {"type", "value"}, item_path)
			if "value" not in item:
				raise FlexValueError(
					f"Value segment at '{item_path}' missing required key 'value'",
					code="MISSING_KEY",
					path=f"{item_path}.value",
				)
			validate_flexvalue(item["value"], path=f"{item_path}.value", resolver_depth=resolver_depth)
		else:
			raise FlexValueError(
				f"Unknown template segment type '{t_type}' at '{item_path}'",
				code="INVALID_TEMPLATE_SEGMENT",
				path=f"{item_path}.type",
			)


def _validate_recursive_flexvalues_in_obj(obj: Any, current_path: str, resolver_depth: int) -> None:
	"""Helper to walk nested dicts/lists in resolver config looking for FlexValue dicts."""
	if type(obj) is dict:
		if "mode" in obj and isinstance(obj["mode"], str) and obj["mode"] in {"static", "variable", "resolver", "template"}:
			validate_flexvalue(obj, path=current_path, resolver_depth=resolver_depth)
		else:
			for k, v in obj.items():
				_validate_recursive_flexvalues_in_obj(v, f"{current_path}.{k}", resolver_depth=resolver_depth)
	elif type(obj) is list:
		for idx, item in enumerate(obj):
			_validate_recursive_flexvalues_in_obj(item, f"{current_path}[{idx}]", resolver_depth=resolver_depth)
