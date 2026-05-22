# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Unified FlexValue compiler/runtime helpers.

Centralizes dynamic value schema normalization and resolution so action handlers
use one deterministic contract.
"""

from __future__ import annotations

import json
import re
from typing import Any

import frappe

FLEX_VALUE_SOURCES = {"literal", "context_path", "jinja"}


class FlexValueCompiler:
	"""Compile heterogeneous authoring payloads into normalized operand specs."""

	@classmethod
	def compile_operand(cls, row: dict, *, requires_value: bool) -> dict[str, Any]:
		if not requires_value:
			return {"value_source": "none", "value_literal": None, "value_template": None, "value_path": None}

		val_obj = row.get("value")
		if isinstance(val_obj, dict) and "mode" in val_obj:
			return cls._compile_structured_mode(val_obj)

		explicit_source = row.get("value_source")
		if explicit_source in FLEX_VALUE_SOURCES:
			return {
				"value_source": explicit_source,
				"value_literal": row.get("value_literal"),
				"value_template": row.get("value_template") or row.get("value"),
				"value_path": cls.normalize_context_path(row.get("value_path")),
			}

		value_template = row.get("value_template") if row.get("value_template") is not None else row.get("value")
		value_ui = row.get("value_template_ui") if isinstance(row.get("value_template_ui"), dict) else {}
		mode = value_ui.get("mode")

		if mode in {"static", "link", "dynamic_link"}:
			return {"value_source": "literal", "value_literal": value_ui.get("value"), "value_template": None, "value_path": None}
		if mode == "variable":
			return {"value_source": "context_path", "value_literal": None, "value_template": None, "value_path": cls.normalize_context_path(value_ui.get("path"))}
		if isinstance(value_template, str):
			contains_jinja = "{{" in value_template or "{%" in value_template
			if mode in {"formula", "resolver"} or contains_jinja:
				return {"value_source": "jinja", "value_literal": None, "value_template": value_template, "value_path": None}
		return {"value_source": "literal", "value_literal": value_template, "value_template": None, "value_path": None}

	@classmethod
	def _compile_structured_mode(cls, val_obj: dict[str, Any]) -> dict[str, Any]:
		mode = val_obj.get("mode")
		if mode in {"static", "link", "dynamic_link"}:
			return {"value_source": "literal", "value_literal": val_obj.get("value"), "value_template": None, "value_path": None}
		if mode == "variable":
			return {"value_source": "context_path", "value_literal": None, "value_template": None, "value_path": cls.normalize_context_path(val_obj.get("path"))}
		return {"value_source": "jinja", "value_literal": None, "value_template": cls.compile_structured_to_jinja(val_obj), "value_path": None}

	@classmethod
	def compile_structured_to_jinja(cls, val: dict[str, Any]) -> str:
		if not val:
			return ""
		mode = val.get("mode")
		if mode in {"static", "link", "dynamic_link"}:
			return str(val.get("value") if val.get("value") is not None else "")
		if mode == "variable":
			path = cls.normalize_context_path(val.get("path"))
			return f"{{{{ {path} }}}}" if path else ""
		if mode == "formula":
			return f"{{{{ {val.get('expression') or ''} }}}}"
		if mode in {"formatter", "normalize", "resolver", "condition"}:
			config = val.get("config") or {}
			return f"{{{{ resolve_dynamic({json.dumps({'mode': mode, 'value': val.get('value'), 'expression': val.get('expression'), 'config': config, 'steps': val.get('steps'), 'formatter': val.get('formatter')})}) }}}}"
		return ""

	@staticmethod
	def normalize_context_path(path: Any) -> str | None:
		if not path:
			return None
		path_str = str(path).strip()
		if not path_str:
			return None
		if path_str.startswith("doc.") or path_str.startswith("vars."):
			return path_str
		return f"vars.{path_str}"


class FlexValueRuntime:
	"""Runtime utilities for expression interpolation and context resolution."""

	@staticmethod
	def resolve_context_path(context: dict, path: str | None):
		if not path:
			return None
		parts = str(path).split(".")
		current = context.get("doc") if parts[0] == "doc" else context.get("vars", {}) if parts[0] == "vars" else None
		for part in parts[1:]:
			if current is None:
				return None
			current = current.get(part) if isinstance(current, dict) or hasattr(current, "get") else None
		return current

	@staticmethod
	def resolve_expressions(value: Any, context: dict, evaluator, ref_label: str):
		if isinstance(value, list):
			return [FlexValueRuntime.resolve_expressions(v, context, evaluator, ref_label) for v in value]
		if isinstance(value, dict):
			return {
				k: FlexValueRuntime.resolve_expressions(v, context, evaluator, f"{ref_label}.{k}") for k, v in value.items()
			}
		if isinstance(value, str) and "{" in value:
			if value.startswith("{") and value.endswith("}") and value.count("{") == 1:
				return evaluator(value[1:-1], context, ref_label)
			return re.sub(r"{(.*?)}", lambda m: str(evaluator(m.group(1), context, ref_label)), value)
		return value
