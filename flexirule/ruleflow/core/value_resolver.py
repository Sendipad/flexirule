# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe
from frappe import _

from flexirule.ruleflow.utils.field_resolver import FieldResolver


def get_context_value(context: dict, path: str | None) -> Any:
	"""
	Resolve a field or variable value from execution context.
	Supports dot notation like 'doc.status', 'vars.result', 'item.rate', etc.
	"""
	if not path:
		return None
	path_str = str(path).strip()
	if not path_str:
		return None

	parts = path_str.split(".")
	base = parts[0]
	if base == "doc":
		current = context.get("doc")
		parts = parts[1:]
	elif base == "vars":
		current = context.get("vars", {})
		parts = parts[1:]
	elif base == "item":
		current = context.get("item")
		parts = parts[1:]
	elif base == "loop":
		current = context.get("loop")
		parts = parts[1:]
	elif base == "row":
		current = context.get("row")
		parts = parts[1:]
	else:
		# Fallback context lookup if no explicit scope is declared
		# Prioritize 'doc' then 'vars'
		doc = context.get("doc")
		vars_dict = context.get("vars", {})

		if doc is not None and (
			(isinstance(doc, dict) and base in doc) or (hasattr(doc, "get") and doc.get(base) is not None)
		):
			current = doc
		elif isinstance(vars_dict, dict) and base in vars_dict:
			current = vars_dict
		else:
			return None

	for part in parts:
		if current is None:
			return None
		if isinstance(current, dict):
			current = current.get(part)
		elif hasattr(current, "get"):
			current = current.get(part)
		else:
			return None
	return current


class CompiledResolver:
	"""Base class for compiled, highly optimized dynamic value resolvers."""

	def resolve(self, context: dict) -> Any:
		raise NotImplementedError()


class NoneResolver(CompiledResolver):
	def resolve(self, context: dict) -> Any:
		return None


class StaticResolver(CompiledResolver):
	def __init__(self, value: Any):
		self.value = value

	def resolve(self, context: dict) -> Any:
		return self.value


class VariableResolver(CompiledResolver):
	def __init__(self, path: str):
		self.path = path

	def resolve(self, context: dict) -> Any:
		return get_context_value(context, self.path)


class DateFormulaResolver(CompiledResolver):
	def __init__(self, base_type: str, base_field: str | None, offset_value: int, offset_unit: str):
		self.base_type = base_type
		self.base_field = base_field
		self.offset_value = offset_value
		self.offset_unit = offset_unit

	def resolve(self, context: dict) -> Any:
		if self.base_type == "today":
			base_date = frappe.utils.nowdate()
		else:
			base_date = get_context_value(context, self.base_field)

		if not base_date:
			return None

		offset = int(self.offset_value or 0)
		if offset == 0 or not self.offset_unit:
			return base_date

		if self.offset_unit == "days":
			return frappe.utils.add_days(base_date, offset)

		return frappe.utils.add_to_date(base_date, **{self.offset_unit: offset})


class MathFormulaResolver(CompiledResolver):
	def __init__(
		self,
		field_a: str | None,
		math_op: str,
		field_b_type: str,
		field_b: str | None,
		constant_b: Any,
		precision: int | None,
	):
		self.field_a = field_a
		self.math_op = math_op
		self.field_b_type = field_b_type
		self.field_b = field_b
		self.constant_b = constant_b
		self.precision = precision

	def resolve(self, context: dict) -> Any:
		val_a = frappe.utils.flt(get_context_value(context, self.field_a)) if self.field_a else 0.0
		if self.field_b_type == "field":
			val_b = frappe.utils.flt(get_context_value(context, self.field_b)) if self.field_b else 0.0
		else:
			val_b = frappe.utils.flt(self.constant_b)

		if self.math_op == "+":
			res = val_a + val_b
		elif self.math_op == "-":
			res = val_a - val_b
		elif self.math_op == "*":
			res = val_a * val_b
		elif self.math_op == "/":
			res = val_a / val_b if val_b != 0.0 else 0.0
		else:
			res = 0.0

		if self.precision is not None:
			res = frappe.utils.flt(res, self.precision)
		return res


class DateDiffResolver(CompiledResolver):
	def __init__(
		self,
		diff_start_type: str,
		diff_start_field: str | None,
		diff_end_type: str,
		diff_end_field: str | None,
		diff_unit: str,
	):
		self.diff_start_type = diff_start_type
		self.diff_start_field = diff_start_field
		self.diff_end_type = diff_end_type
		self.diff_end_field = diff_end_field
		self.diff_unit = diff_unit

	def resolve(self, context: dict) -> Any:
		if self.diff_start_type == "today":
			start = frappe.utils.nowdate()
		else:
			start = get_context_value(context, self.diff_start_field)

		if self.diff_end_type == "today":
			end = frappe.utils.nowdate()
		else:
			end = get_context_value(context, self.diff_end_field)

		if not start or not end:
			return 0

		if self.diff_unit == "days":
			return frappe.utils.date_diff(end, start)
		if self.diff_unit == "months":
			return frappe.utils.month_diff(end, start)
		return int(frappe.utils.month_diff(end, start) / 12)


class ChildAggregationResolver(CompiledResolver):
	def __init__(self, agg_table: str | None, agg_field: str | None, agg_op: str):
		self.agg_table = agg_table
		self.agg_field = agg_field
		self.agg_op = agg_op

	def resolve(self, context: dict) -> Any:
		rows = get_context_value(context, self.agg_table)
		if not rows or not isinstance(rows, list):
			return 0

		if self.agg_op == "count":
			return len(rows)

		if not self.agg_field:
			return 0

		values = [
			frappe.utils.flt(row.get(self.agg_field))
			for row in rows
			if hasattr(row, "get") and row.get(self.agg_field) is not None
		]

		if self.agg_op == "sum":
			return sum(values)
		if self.agg_op == "avg":
			return sum(values) / len(values) if values else 0.0

		return 0


class StringFormulaResolver(CompiledResolver):
	def __init__(self, str_op: str, str_a_type: str, str_a: str | None, str_b_type: str, str_b: str | None):
		self.str_op = str_op
		self.str_a_type = str_a_type
		self.str_a = str_a
		self.str_b_type = str_b_type
		self.str_b = str_b

	def resolve(self, context: dict) -> Any:
		if self.str_a_type == "field":
			val_a = get_context_value(context, self.str_a)
		else:
			val_a = self.str_a

		if self.str_b_type == "field":
			val_b = get_context_value(context, self.str_b)
		else:
			val_b = self.str_b

		if self.str_op == "concat":
			return str(val_a or "") + str(val_b or "")
		if self.str_op == "uppercase":
			return str(val_a or "").upper()
		if self.str_op == "lowercase":
			return str(val_a or "").lower()
		if self.str_op == "fmt_money":
			return frappe.utils.fmt_money(val_a, currency=val_b)

		return val_a


class NormalizationResolver(CompiledResolver):
	def __init__(
		self,
		norm_field: str | None,
		norm_profile: str | None = None,
		norm_pipeline: list[str] | None = None,
		norm_op: str | None = None,
	):
		self.norm_field = norm_field
		self.norm_profile = norm_profile
		self.norm_pipeline = norm_pipeline
		self.norm_op = norm_op

	def resolve(self, context: dict) -> Any:
		val = get_context_value(context, self.norm_field)
		if val is None:
			return None

		from flexirule.ruleflow.utils.normalization import execute_normalization_pipeline

		# Legacy support
		pipeline = self.norm_pipeline
		if not self.norm_profile and not pipeline and self.norm_op:
			legacy_map = {
				"trim": ["trim"],
				"slug": ["slug"],
				"snake": ["snake_case"],
				"title": ["title_case"],
				"upper": ["uppercase"],
				"lower": ["lowercase"],
			}
			pipeline = legacy_map.get(self.norm_op)

		result = execute_normalization_pipeline(
			value=val, pipeline=pipeline, profile=self.norm_profile
		)
		return result.get("normalized_value")


class FormatResolver(CompiledResolver):
	def __init__(self, fmt_op: str, fmt_field: str | None, fmt_config: str):
		self.fmt_op = fmt_op
		self.fmt_field = fmt_field
		self.fmt_config = fmt_config

	def resolve(self, context: dict) -> Any:
		val = get_context_value(context, self.fmt_field)
		if val is None:
			return ""

		if self.fmt_op == "format_date":
			return frappe.utils.format_date(val, self.fmt_config)

		if self.fmt_op == "fmt_money":
			# Determine if currency is static code or dynamic field
			curr = self.fmt_config or ""
			if curr.startswith("doc.") or curr.startswith("vars."):
				resolved_curr = get_context_value(context, curr)
			else:
				resolved_curr = curr
			return frappe.utils.fmt_money(val, currency=resolved_curr)

		if self.fmt_op == "format":
			return (self.fmt_config or "").format(val)

		return str(val)


class SystemContextResolver(CompiledResolver):
	def __init__(self, sys_token: str, sys_role: str):
		self.sys_token = sys_token
		self.sys_role = sys_role

	def resolve(self, context: dict) -> Any:
		if self.sys_token == "user":
			return frappe.session.user
		if self.sys_token == "role_check":
			return bool(self.sys_role in frappe.get_roles(frappe.session.user))
		return None


class FetchResolver(CompiledResolver):
	def __init__(self, link_field: str | None, fetch_field: str | None, linked_doctype: str | None):
		self.link_field = link_field
		self.fetch_field = fetch_field
		self.linked_doctype = linked_doctype

	def resolve(self, context: dict) -> Any:
		if not self.link_field or not self.fetch_field or not self.linked_doctype:
			return None

		# Ensure link_field has a scope, default to doc.
		path = self.link_field
		known_scopes = ("doc.", "vars.", "ctx.", "loop.", "row.", "item.", "caller.", "rule.")
		if not any(path.startswith(s) for s in known_scopes):
			path = f"doc.{path}"

		link_value = get_context_value(context, path)
		if not link_value:
			return None

		return frappe.db.get_value(self.linked_doctype, link_value, self.fetch_field)


class JinjaResolver(CompiledResolver):
	"""Fallback resolver that compiles and renders standard Jinja templates."""

	def __init__(self, template: str):
		self.template = template

	def resolve(self, context: dict) -> Any:
		from flexirule.ruleflow.core.action_handlers import ActionHandler

		class DummyActionHandler(ActionHandler):
			def execute(self, action, context, engine):
				return None, None

		handler = DummyActionHandler()
		template_context = handler._build_template_context(context)
		if "value" in context:
			template_context["value"] = context["value"]
		# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
		return frappe.render_template(self.template, template_context)  # nosemgrep: frappe-ssti


class SafeEvalResolver(CompiledResolver):
	"""Fallback resolver that executes Python expressions via safe_eval."""

	def __init__(self, expression: str):
		self.expression = expression

	def resolve(self, context: dict) -> Any:
		from flexirule.ruleflow.core.action_handlers import ActionHandler

		class DummyActionHandler(ActionHandler):
			def execute(self, action, context, engine):
				return None, None

		handler = DummyActionHandler()
		return handler._safe_eval(self.expression, context)


class ExpressionResolver(CompiledResolver):
	"""Mixed mode resolver that resolves multiple non-contiguous segment templates."""

	def __init__(self, segments: list[CompiledResolver]):
		self.segments = segments

	def resolve(self, context: dict) -> Any:
		parts = []
		for seg in self.segments:
			val = seg.resolve(context)
			parts.append(str(val) if val is not None else "")
		return "".join(parts)


class ValueResolver:
	"""
	Unified compiler & runtime registry for FlexValue systems.
	Converts dynamic configuration schemas into optimized CompiledResolver graphs.
	"""

	@staticmethod
	def compile(val: Any) -> CompiledResolver:
		if val is None:
			return NoneResolver()

		if isinstance(val, dict):
			mode = val.get("mode")

			if mode in ("static", "link", "dynamic_link"):
				return StaticResolver(val.get("value"))

			if mode == "variable":
				path = val.get("path") or val.get("value") or ""
				return VariableResolver(path)

			if mode == "expression":
				segments: list[CompiledResolver] = []
				for item in val.get("value") or []:
					seg_type = item.get("type")
					if seg_type == "text":
						segments.append(StaticResolver(item.get("value")))
					elif seg_type == "variableToken":
						segments.append(VariableResolver(item.get("attrs", {}).get("path") or ""))
					elif seg_type == "resolverToken":
						attrs = item.get("attrs", {})
						config = attrs.get("config")
						if config and isinstance(config, dict):
							segments.append(ValueResolver.compile_resolver_config(config))
						else:
							segments.append(
								SafeEvalResolver(attrs.get("expression") or attrs.get("resolver"))
							)
					elif seg_type == "jsonToken":
						segments.append(JinjaResolver(item.get("attrs", {}).get("value") or ""))
				return ExpressionResolver(segments)

			if mode in ("resolver", "formatter", "normalize", "format", "normalization") or "kind" in val:
				config = val.get("config") or val
				if isinstance(config, dict) and "kind" in config:
					return ValueResolver.compile_resolver_config(config)

			if "value" in val:
				return StaticResolver(val.get("value"))

		if isinstance(val, str):
			if "{{" in val or "{%" in val:
				return JinjaResolver(val)
			if val.startswith("{") and val.endswith("}") and val.count("{") == 1:
				return SafeEvalResolver(val[1:-1])
			return StaticResolver(val)

		return StaticResolver(val)

	@staticmethod
	def compile_resolver_config(config: dict) -> CompiledResolver:
		kind = config.get("kind")
		if not kind:
			return NoneResolver()

		if kind == "date_formula":
			return DateFormulaResolver(
				base_type=config.get("base_type", "today"),
				base_field=config.get("base_field"),
				offset_value=config.get("offset_value", 0),
				offset_unit=config.get("offset_unit", "days"),
			)
		if kind == "math_formula":
			return MathFormulaResolver(
				field_a=config.get("field_a"),
				math_op=config.get("math_op", "+"),
				field_b_type=config.get("field_b_type", "field"),
				field_b=config.get("field_b"),
				constant_b=config.get("constant_b", 0),
				precision=config.get("precision", 2),
			)
		if kind == "date_diff":
			return DateDiffResolver(
				diff_start_type=config.get("diff_start_type", "today"),
				diff_start_field=config.get("diff_start_field"),
				diff_end_type=config.get("diff_end_type", "doc_field"),
				diff_end_field=config.get("diff_end_field"),
				diff_unit=config.get("diff_unit", "days"),
			)
		if kind == "child_aggregation":
			return ChildAggregationResolver(
				agg_table=config.get("agg_table"),
				agg_field=config.get("agg_field"),
				agg_op=config.get("agg_op", "sum"),
			)
		if kind == "string_formula":
			return StringFormulaResolver(
				str_op=config.get("str_op", "concat"),
				str_a_type=config.get("str_a_type", "field"),
				str_a=config.get("str_a"),
				str_b_type=config.get("str_b_type", "constant"),
				str_b=config.get("str_b"),
			)
		if kind == "normalization":
			return NormalizationResolver(
				norm_field=config.get("norm_field"),
				norm_profile=config.get("norm_profile"),
				norm_pipeline=config.get("norm_pipeline"),
				norm_op=config.get("norm_op"),
			)
		if kind == "format":
			return FormatResolver(
				fmt_op=config.get("fmt_op", "format_date"),
				fmt_field=config.get("fmt_field"),
				fmt_config=config.get("fmt_config", ""),
			)
		if kind == "fetch":
			return FetchResolver(
				link_field=config.get("link_field"),
				fetch_field=config.get("fetch_field"),
				linked_doctype=config.get("linked_doctype"),
			)
		if kind == "system_context":
			return SystemContextResolver(
				sys_token=config.get("sys_token", "user"), sys_role=config.get("sys_role", "")
			)

		return NoneResolver()


def get_compiled_resolver(action, key: str, value_payload: Any) -> CompiledResolver:
	"""
	Retrieve or create a request-local compiled ValueResolver object for extreme execution efficiency.
	"""
	if not hasattr(frappe.local, "flexirule_compiled_resolvers"):
		frappe.local.flexirule_compiled_resolvers = {}

	cache_key = f"{getattr(action, 'name', 'action')}_{key}"
	if cache_key not in frappe.local.flexirule_compiled_resolvers:
		frappe.local.flexirule_compiled_resolvers[cache_key] = ValueResolver.compile(value_payload)

	return frappe.local.flexirule_compiled_resolvers[cache_key]
