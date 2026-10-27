# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from flexirule.ruleflow.core.condition_errors import ConditionValidationError
from flexirule.ruleflow.core.flexvalue_contract import MAX_CONDITION_PAYLOAD_BYTES

CONDITION_CONFIG_KEYS = ("condition", "condition_tree", "condition_json")


def detect_canonical_condition_payload(value: Any) -> tuple[bool, dict | None]:
	"""Detect a canonical direct-node payload without guessing or legacy fallback.

	An object with a type discriminant is always treated as canonical, even when
	the type is unknown; strict validation then rejects it. Historical envelopes
	are deliberately rejected rather than silently unwrapped or reinterpreted.
	"""
	candidate = value
	if isinstance(candidate, Mapping):
		if "type" in candidate:
			return True, dict(candidate)
		try:
			encoded = json.dumps(
				candidate, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
			).encode("utf-8")
		except (TypeError, ValueError, RecursionError) as exc:
			raise ConditionValidationError(
				"invalid_json_value", "$", "Condition payload must be a finite, acyclic JSON value"
			) from exc
		if len(encoded) > MAX_CONDITION_PAYLOAD_BYTES:
			raise ConditionValidationError(
				"condition_payload_too_large", "$", "Condition payload exceeds the configured byte limit"
			)
		if {"schema", "version", "root"} & set(candidate):
			raise ConditionValidationError(
				"unsupported_condition_envelope", "$",
				"Canonical conditions must be stored as a direct node without an envelope",
			)
		return False, None

	if not isinstance(candidate, str):
		return False, None
	text = candidate.strip()
	if len(text.encode("utf-8")) > MAX_CONDITION_PAYLOAD_BYTES:
		raise ConditionValidationError(
			"condition_payload_too_large", "$", "Condition payload exceeds the configured byte limit"
		)
	if not text or text[0] not in "{[":
		return False, None
	try:
		parsed = json.loads(text)
		if isinstance(parsed, str) and parsed.strip().startswith(("{", "[")):
			parsed = json.loads(parsed)
	except Exception as exc:
		raise ConditionValidationError(
			"invalid_json", "$", "Structured condition JSON is malformed"
		) from exc
	if isinstance(parsed, Mapping):
		if "type" in parsed:
			return True, dict(parsed)
		if {"schema", "version", "root"} & set(parsed):
			raise ConditionValidationError(
				"unsupported_condition_envelope", "$",
				"Canonical conditions must be stored as a direct node without an envelope",
			)
	return False, None


def parse_condition_payload(value: Any) -> dict | list | str | None:
	"""Parse a condition payload from dict, list, JSON string, or raw Python expression string.

	Contract:
	- Dict or list payloads return as dict or list.
	- JSON strings starting with '{' or '[' are parsed as structured condition trees.
	  If parsing fails on a string starting with '{' or '[', ValueError is raised for malformed JSON.
	- Non-JSON strings (not starting with '{' or '[') are treated as raw Python condition expression strings.
	- None or empty/whitespace strings return None.
	"""
	if value in (None, ""):
		return None

	if isinstance(value, Mapping):
		return dict(value)

	if isinstance(value, list):
		return list(value)

	if not isinstance(value, str):
		raise ConditionValidationError(
			"invalid_condition_payload_type", "$", "Condition payload must be an object, array, or string"
		)
	if len(value.encode("utf-8")) > MAX_CONDITION_PAYLOAD_BYTES:
		raise ConditionValidationError(
			"condition_payload_too_large", "$", "Condition payload exceeds the configured byte limit"
		)

	val_str = value.strip()
	if not val_str:
		return None

	if val_str.startswith(("{", "[")):
		try:
			parsed = json.loads(val_str)
			# Support double-encoded JSON payloads
			if isinstance(parsed, str) and parsed.strip().startswith(("{", "[")):
				try:
					parsed = json.loads(parsed)
				except Exception:
					pass
			if isinstance(parsed, Mapping):
				return dict(parsed)
			if isinstance(parsed, list):
				return list(parsed)
			if isinstance(parsed, str) and parsed.strip():
				return parsed.strip()
		except Exception as exc:
			raise ConditionValidationError(
				"invalid_json", "$", "Structured condition JSON is malformed"
			) from exc

	return val_str


def extract_condition_payload_from_config(config_value: Any) -> dict | list | str | None:
	"""Extract condition payload from Action.config.

	Supports:
	- direct condition tree or raw string in config
	- nested keys: condition / condition_tree / condition_json
	"""
	config_payload = parse_condition_payload(config_value)
	if isinstance(config_payload, list | str):
		return config_payload

	if not isinstance(config_payload, Mapping):
		return None

	# Canonical conditions are persisted as the direct node, not under a wrapper.
	# Even an unknown type is returned to strict validation and cannot reach legacy compilation.
	if "type" in config_payload:
		return dict(config_payload)
	if {"schema", "version", "root"} & set(config_payload):
		raise ConditionValidationError(
			"unsupported_condition_envelope", "$",
			"Canonical conditions must be stored as a direct node without an envelope",
		)

	for key in CONDITION_CONFIG_KEYS:
		if key not in config_payload:
			continue
		candidate = parse_condition_payload(config_payload.get(key))
		if candidate is not None:
			return candidate

	if (
		"conditions" in config_payload
		or "left" in config_payload
		or ("collection" in config_payload and "where" in config_payload)
	):
		return dict(config_payload)

	return None


def get_condition_payload(action_or_dict: Any) -> dict | list | str | None:
	"""Resolve the effective condition payload for a Condition action.

	Canonical source: action.config
	Legacy fallback: action.condition_json
	"""
	config_payload = extract_condition_payload_from_config(_safe_get(action_or_dict, "config"))
	if config_payload is not None:
		return config_payload

	return parse_condition_payload(_safe_get(action_or_dict, "condition_json"))


def set_condition_payload_on_action(action_or_dict: Any, payload: dict | list | str) -> None:
	"""Persist canonical condition payload to Action.config."""
	if isinstance(payload, str):
		val = payload.strip()
		try:
			parsed = json.loads(val)
			if isinstance(parsed, dict | list):
				serialized = json.dumps(parsed, ensure_ascii=False)
			else:
				serialized = json.dumps({"condition": val}, ensure_ascii=False)
		except Exception:
			serialized = json.dumps({"condition": val}, ensure_ascii=False)
	else:
		serialized = json.dumps(payload, ensure_ascii=False)

	_safe_set(action_or_dict, "config", serialized)


def _safe_get(obj: Any, key: str, default=None):
	if obj is None:
		return default
	if isinstance(obj, Mapping):
		return obj.get(key, default)
	if hasattr(obj, "get"):
		return obj.get(key, default)
	return getattr(obj, key, default)


def _safe_set(obj: Any, key: str, value: Any) -> None:
	if obj is None:
		return
	if isinstance(obj, dict):
		obj[key] = value
		return
	if hasattr(obj, "set"):
		obj.set(key, value)
		return
	setattr(obj, key, value)
