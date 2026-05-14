# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Utilities for input/output mapping in Rule Actions
"""

import json
from typing import Any


def apply_input_mapping(context: dict, mapping_json: str, config: dict) -> dict:
	"""
	Apply input mapping to merge context variables into config

	Structure: {"target_config_field": "source_context_path"}
	Example: {"threshold": "doc.total_amount"}

	Args:
	    context: Execution context with variables
	    mapping_json: JSON string
	    config: Original configuration dict

	Returns:
	    Updated config with mapped values
	"""
	if not mapping_json:
		return config

	mapping = _parse_mapping(mapping_json)
	if not isinstance(mapping, dict):
		return config

	result = dict(config)
	for target_field, source_path in mapping.items():
		# Source is a path in context (e.g. "doc.items")
		val = resolve_path(context, source_path)
		if val is not None:
			result[target_field] = val

	return result


def apply_output_mapping(result: Any, mapping_json: str, context: dict) -> dict:
	"""
	Apply output mapping to store result in context

	Structure: {"source_result_key": "target_context_var"}
	Example: {"fraud_score": "vars.score"}

	Args:
	    result: Method execution result
	    mapping_json: JSON string
	    context: Execution context to update

	Returns:
	    Updated context
	"""
	if not mapping_json:
		return context

	mapping = _parse_mapping(mapping_json)
	if not isinstance(mapping, dict):
		return context

	for source_key, target_var in mapping.items():
		value_to_map = None

		# Determine value to map
		if source_key == "__self__" or source_key == "result" or source_key == "":
			value_to_map = result
		elif isinstance(result, dict) and source_key in result:
			value_to_map = result[source_key]
		elif hasattr(result, source_key):
			value_to_map = getattr(result, source_key)

		if value_to_map is not None:
			# Target is a variable name in context (usually vars.X)
			# We support simple assignment to vars dict or top-level
			update_context(context, target_var, value_to_map)

	return context


def resolve_path(data: Any, path: str) -> Any:
	"""
	Resolve a dot-notation path in a dict/object
	e.g. resolve_path(ctx, "doc.items")
	"""
	if not path:
		return None

	parts = path.split(".")
	current = data

	for part in parts:
		if current is None:
			return None

		if isinstance(current, dict):
			current = current.get(part)
		elif isinstance(current, list) and part.isdigit():
			idx = int(part)
			if idx < 0 or idx >= len(current):
				return None
			current = current[idx]
		else:
			current = getattr(current, part, None)

	return current


def update_context(context: dict, path: str, value: Any):
	"""
	Update context variable supporting basic dot-notation for 'vars'
	e.g. "vars.my_score" -> context['vars']['my_score'] = value
	"""
	if not path:
		return

	parts = path.split(".")

	# Secure: Only allow updating 'vars' or direct context keys if strictly needed
	# Ideally we only write to 'vars' layer

	if len(parts) == 1:
		# Top-level (Not recommended to overwrite 'doc' etc, but allowed by engine constraints if pure?)
		# Let's write to vars by default if top-level? No, explicitly respect path.
		context[parts[0]] = value
	elif len(parts) == 2 and parts[0] == "vars":
		# vars.key
		if "vars" not in context:
			context["vars"] = {}
		context["vars"][parts[1]] = value
	else:
		# Complex path set: simplistic support for dicts
		target = context
		for part in parts[:-1]:
			if part not in target or not isinstance(target[part], dict):
				target[part] = {}
			target = target[part]
		target[parts[-1]] = value


def _parse_mapping(mapping_json: Any) -> dict | None:
	"""Parse mapping payload from JSON string or dict."""
	if isinstance(mapping_json, dict):
		return mapping_json

	if not isinstance(mapping_json, str):
		return None

	try:
		parsed = json.loads(mapping_json)
	except (json.JSONDecodeError, TypeError):
		return None

	return parsed if isinstance(parsed, dict) else None
