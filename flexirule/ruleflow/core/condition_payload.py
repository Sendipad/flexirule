# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

CONDITION_CONFIG_KEYS = ("condition", "condition_tree", "condition_json")


def parse_condition_payload(value: Any) -> dict | list | None:
	"""Parse a condition payload from dict/list/JSON string.

	Returns None when the payload is missing or invalid.
	"""
	if value in (None, ""):
		return None

	if isinstance(value, Mapping):
		return dict(value)

	if isinstance(value, list):
		return list(value)

	if not isinstance(value, str):
		return None

	try:
		parsed = json.loads(value)
		# Support double-encoded JSON payloads
		if isinstance(parsed, str):
			try:
				parsed = json.loads(parsed)
			except Exception:
				pass
		if isinstance(parsed, Mapping):
			return dict(parsed)
		if isinstance(parsed, list):
			return list(parsed)
	except Exception:
		return None

	return None


def extract_condition_payload_from_config(config_value: Any) -> dict | list | None:
	"""Extract condition payload from Action.config.

	Supports:
	- direct condition tree in config
	- nested keys: condition / condition_tree / condition_json
	"""
	config_payload = parse_condition_payload(config_value)
	if isinstance(config_payload, list):
		return config_payload

	if not isinstance(config_payload, Mapping):
		return None

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


def get_condition_payload(action_or_dict: Any) -> dict | list | None:
	"""Resolve the effective condition payload for a Condition action.

	Canonical source: action.config
	Legacy fallback: action.condition_json
	"""
	config_payload = extract_condition_payload_from_config(_safe_get(action_or_dict, "config"))
	if config_payload is not None:
		return config_payload

	return parse_condition_payload(_safe_get(action_or_dict, "condition_json"))


def set_condition_payload_on_action(action_or_dict: Any, payload: dict | list) -> None:
	"""Persist canonical condition payload to Action.config."""
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
