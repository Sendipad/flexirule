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


class ValueSourceResolver(CompiledResolver):
	"""
	Canonical Value Source Resolver handling field, variable, old_field, static, or system_context.
	"""

	def __init__(
		self,
		operation: str = "field",
		path: str | None = None,
		value: Any = None,
		sys_token: str = "user",
		sys_role: str = "",
	):
		self.operation = operation
		self.path = path
		self.value = value
		self.sys_token = sys_token
		self.sys_role = sys_role

	def resolve(self, context: dict) -> Any:
		op = self.operation
		if op == "static":
			return self.value
		if op in ("field", "variable", "old_field"):
			return get_context_value(context, self.path)
		if op == "system_context":
			if self.sys_token == "user":
				return frappe.session.user
			if self.sys_token == "role_check":
				return bool(self.sys_role in frappe.get_roles(frappe.session.user))
			return None
		return get_context_value(context, self.path) if self.path else self.value


class DateResolver(CompiledResolver):
	"""
	Canonical Date Resolver handling add, subtract, and diff operations.
	"""

	def __init__(
		self,
		operation: str = "add",
		base_type: str = "today",
		base_field: str | None = None,
		offset_value: int = 0,
		offset_unit: str = "days",
		offset_sign: str = "+",
		diff_start_type: str = "today",
		diff_start_field: str | None = None,
		diff_end_type: str = "doc_field",
		diff_end_field: str | None = None,
		diff_unit: str = "days",
	):
		self.operation = operation
		self.base_type = base_type
		self.base_field = base_field
		self.offset_value = offset_value
		self.offset_unit = offset_unit
		self.offset_sign = offset_sign
		self.diff_start_type = diff_start_type
		self.diff_start_field = diff_start_field
		self.diff_end_type = diff_end_type
		self.diff_end_field = diff_end_field
		self.diff_unit = diff_unit

	def resolve(self, context: dict) -> Any:
		op = getattr(self, "operation", "add")
		if op in ("add", "subtract"):
			if self.base_type == "today":
				base_date = frappe.utils.nowdate()
			else:
				base_date = get_context_value(context, self.base_field)

			if not base_date:
				return None

			offset = int(self.offset_value or 0)
			if (op == "subtract" or self.offset_sign == "-") and offset > 0:
				offset = -offset

			if offset == 0 or not self.offset_unit:
				return base_date

			if self.offset_unit == "days":
				return frappe.utils.add_days(base_date, offset)

			return frappe.utils.add_to_date(base_date, **{self.offset_unit: offset})

		if op == "diff":
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

			diff_u = getattr(self, "diff_unit", "days")
			if diff_u == "days":
				return frappe.utils.date_diff(end, start)
			if diff_u == "months":
				return frappe.utils.month_diff(end, start)
			return int(frappe.utils.month_diff(end, start) / 12)

		return None


class DateFormulaResolver(DateResolver):
	def __init__(
		self,
		base_type: str,
		base_field: str | None,
		offset_value: int,
		offset_unit: str,
		offset_sign: str = "+",
	):
		super().__init__(
			operation="subtract" if offset_sign == "-" else "add",
			base_type=base_type,
			base_field=base_field,
			offset_value=offset_value,
			offset_unit=offset_unit,
			offset_sign=offset_sign,
		)


class DateDiffResolver(DateResolver):
	def __init__(
		self,
		diff_start_type: str,
		diff_start_field: str | None,
		diff_end_type: str,
		diff_end_field: str | None,
		diff_unit: str,
	):
		super().__init__(
			operation="diff",
			diff_start_type=diff_start_type,
			diff_start_field=diff_start_field,
			diff_end_type=diff_end_type,
			diff_end_field=diff_end_field,
			diff_unit=diff_unit,
		)


class MathResolver(CompiledResolver):
	"""
	Canonical Math Resolver for binary arithmetic (+, -, *, /) and math functions (min, max, round).
	"""

	def __init__(
		self,
		operation: str = "+",
		field_a: str | None = None,
		field_b_type: str = "field",
		field_b: str | None = None,
		constant_b: Any = 0,
		precision: int | None = 2,
		math_op: str | None = None,
	):
		self.operation = math_op or operation
		self.math_op = math_op or operation
		self.field_a = field_a
		self.field_b_type = field_b_type
		self.field_b = field_b
		self.constant_b = constant_b
		self.precision = precision

	def resolve(self, context: dict) -> Any:
		val_a = frappe.utils.flt(get_context_value(context, self.field_a)) if self.field_a else 0.0
		if getattr(self, "field_b_type", "field") == "field":
			val_b = frappe.utils.flt(get_context_value(context, self.field_b)) if self.field_b else 0.0
		else:
			val_b = frappe.utils.flt(getattr(self, "constant_b", 0))

		op = getattr(self, "math_op", getattr(self, "operation", "+"))
		if op in ("+", "add"):
			res = val_a + val_b
		elif op in ("-", "subtract"):
			res = val_a - val_b
		elif op in ("*", "multiply"):
			res = val_a * val_b
		elif op in ("/", "divide"):
			res = val_a / val_b if val_b != 0.0 else 0.0
		elif op == "min":
			res = min(val_a, val_b)
		elif op == "max":
			res = max(val_a, val_b)
		elif op == "round":
			res = val_a
		else:
			res = 0.0

		prec = getattr(self, "precision", None)
		if prec is not None:
			res = frappe.utils.flt(res, prec)
		return res


class MathFormulaResolver(MathResolver):
	def __init__(
		self,
		field_a: str | None,
		math_op: str,
		field_b_type: str,
		field_b: str | None,
		constant_b: Any,
		precision: int | None,
	):
		super().__init__(
			operation=math_op,
			field_a=field_a,
			field_b_type=field_b_type,
			field_b=field_b,
			constant_b=constant_b,
			precision=precision,
			math_op=math_op,
		)


class TextResolver(CompiledResolver):
	"""
	Canonical Text Resolver consolidating concatenation, casing, trim, slug, snake, title,
	normalization pipeline, and string/currency/date formatting.
	"""

	def __init__(
		self,
		operation: str = "concat",
		field_a: str | None = None,
		field_a_type: str = "field",
		field_b: str | None = None,
		field_b_type: str = "constant",
		norm_profile: str | None = None,
		norm_pipeline: list[str] | None = None,
		fmt_config: str | None = None,
		pattern: str | None = None,
		str_op: str | None = None,
		str_a: str | None = None,
		str_a_type: str | None = None,
		str_b: str | None = None,
		str_b_type: str | None = None,
		norm_field: str | None = None,
		norm_op: str | None = None,
		fmt_op: str | None = None,
		fmt_field: str | None = None,
	):
		self.str_op = str_op
		self.norm_op = norm_op
		self.fmt_op = fmt_op
		self.operation = str_op or norm_op or fmt_op or operation
		if norm_profile or norm_pipeline:
			self.operation = "normalize"
		self.field_a = norm_field or fmt_field or str_a or field_a
		self.str_a = self.field_a
		self.norm_field = self.field_a
		self.fmt_field = self.field_a
		self.field_a_type = str_a_type or field_a_type
		self.str_a_type = self.field_a_type
		self.field_b = str_b or field_b
		self.str_b = self.field_b
		self.field_b_type = str_b_type or field_b_type
		self.str_b_type = self.field_b_type
		self.norm_profile = norm_profile
		self.norm_pipeline = norm_pipeline
		self.fmt_config = fmt_config or pattern

	def resolve(self, context: dict) -> Any:
		op = (
			getattr(self, "str_op", None)
			or getattr(self, "norm_op", None)
			or getattr(self, "fmt_op", None)
			or getattr(self, "operation", "concat")
		)

		f_a_type = getattr(self, "str_a_type", getattr(self, "field_a_type", "field"))
		f_a = getattr(
			self,
			"str_a",
			getattr(self, "norm_field", getattr(self, "fmt_field", getattr(self, "field_a", None))),
		)

		f_b_type = getattr(self, "str_b_type", getattr(self, "field_b_type", "constant"))
		f_b = getattr(self, "str_b", getattr(self, "field_b", None))

		if f_a_type == "field":
			val_a = get_context_value(context, f_a)
		else:
			val_a = f_a

		if f_b_type == "field":
			val_b = get_context_value(context, f_b)
		else:
			val_b = f_b

		if op == "concat":
			return str(val_a or "") + str(val_b or "")

		if op in ("upper", "uppercase"):
			return str(val_a or "").upper()

		if op in ("lower", "lowercase"):
			return str(val_a or "").lower()

		if op == "trim":
			return str(val_a or "").strip()

		if (
			op in ("slug", "snake", "title", "normalize")
			or getattr(self, "norm_profile", None)
			or getattr(self, "norm_pipeline", None)
		):
			if val_a is None:
				return None
			from flexirule.ruleflow.utils.normalization import execute_normalization_pipeline

			pipeline = getattr(self, "norm_pipeline", None)
			profile = getattr(self, "norm_profile", None)
			if not profile and not pipeline and op:
				legacy_map = {
					"trim": ["trim"],
					"slug": ["slug"],
					"snake": ["snake_case"],
					"title": ["title_case"],
					"upper": ["uppercase"],
					"uppercase": ["uppercase"],
					"lower": ["lowercase"],
					"lowercase": ["lowercase"],
				}
				pipeline = legacy_map.get(op)

			res = execute_normalization_pipeline(value=val_a, pipeline=pipeline, profile=profile)
			return res.get("normalized_value")

		if op == "format_date":
			if val_a is None:
				return ""
			return frappe.utils.format_date(val_a, getattr(self, "fmt_config", None))

		if op == "fmt_money":
			if val_a is None:
				return ""
			curr = getattr(self, "fmt_config", None) or val_b or ""
			if isinstance(curr, str) and (curr.startswith("doc.") or curr.startswith("vars.")):
				resolved_curr = get_context_value(context, curr)
			else:
				resolved_curr = curr
			return frappe.utils.fmt_money(val_a, currency=resolved_curr)

		if op in ("format", "pattern"):
			if val_a is None:
				return ""
			return (getattr(self, "fmt_config", None) or "").format(val_a)

		if op == "replace":
			return str(val_a or "").replace(str(f_b or ""), str(getattr(self, "fmt_config", None) or ""))

		return val_a


class StringFormulaResolver(TextResolver):
	def __init__(self, str_op: str, str_a_type: str, str_a: str | None, str_b_type: str, str_b: str | None):
		super().__init__(
			operation=str_op,
			str_op=str_op,
			str_a_type=str_a_type,
			str_a=str_a,
			str_b_type=str_b_type,
			str_b=str_b,
		)


class NormalizationResolver(TextResolver):
	def __init__(
		self,
		norm_field: str | None,
		norm_profile: str | None = None,
		norm_pipeline: list[str] | None = None,
		norm_op: str | None = None,
	):
		super().__init__(
			operation=norm_op or "normalize",
			norm_field=norm_field,
			norm_profile=norm_profile,
			norm_pipeline=norm_pipeline,
			norm_op=norm_op,
		)


class FormatResolver(TextResolver):
	def __init__(self, fmt_op: str, fmt_field: str | None, fmt_config: str):
		super().__init__(
			operation=fmt_op,
			fmt_op=fmt_op,
			fmt_field=fmt_field,
			fmt_config=fmt_config,
		)


class AggregateResolver(CompiledResolver):
	"""
	Canonical Aggregate Resolver for evaluating scalar metric reductions (sum, avg, min, max, count)
	over child tables or list collections.
	"""

	def __init__(
		self,
		agg_table: str | None = None,
		agg_field: str | None = None,
		agg_op: str = "sum",
		source: str | None = None,
	):
		self.agg_table = source or agg_table
		self.agg_field = agg_field
		self.agg_op = agg_op

	def resolve(self, context: dict) -> Any:
		rows = get_context_value(context, self.agg_table)
		if not rows or not isinstance(rows, list):
			return 0

		op = getattr(self, "agg_op", "sum")
		if op == "count":
			return len(rows)

		if not self.agg_field:
			return 0

		values = [
			frappe.utils.flt(row.get(self.agg_field))
			for row in rows
			if hasattr(row, "get") and row.get(self.agg_field) is not None
		]

		if op == "sum":
			return sum(values)
		if op == "avg":
			return sum(values) / len(values) if values else 0.0
		if op == "min":
			return min(values) if values else 0.0
		if op == "max":
			return max(values) if values else 0.0

		return 0


class ChildAggregationResolver(AggregateResolver):
	def __init__(self, agg_table: str | None, agg_field: str | None, agg_op: str):
		super().__init__(agg_table=agg_table, agg_field=agg_field, agg_op=agg_op)


class CollectionResolver(CompiledResolver):
	"""
	Compiled resolver strategy for querying, checking, filtering, and extracting
	values from child table collections or list variables.
	"""

	MAX_COLLECTION_ROWS = 10000

	def __init__(
		self,
		source: str | None = None,
		operation: str = "any",
		condition: dict | list | None = None,
		target_field: str | None = None,
	):
		self.source = source
		self.operation = (operation or "any").lower()
		if self.operation == "find":
			self.operation = "first"  # Map UI alias directly to first matching row
		self.condition = condition
		self.target_field = target_field
		self._compiled_evaluator = None

		if self.condition:
			from flexirule.ruleflow.core.evaluator import ConditionEvaluator

			cond_list = self.condition if isinstance(self.condition, list) else [self.condition]
			self._compiled_evaluator = ConditionEvaluator(json.dumps(cond_list))

	def resolve(self, context: dict) -> Any:
		rows = get_context_value(context, self.source)
		if rows is None or not isinstance(rows, list):
			if self.operation == "count":
				return 0
			if self.operation in ("filter", "pluck", "unique"):
				return []
			if self.operation == "all":
				return True if rows is not None and isinstance(rows, list) else False
			if self.operation == "any":
				return False
			return None

		if len(rows) > self.MAX_COLLECTION_ROWS:
			from flexirule.ruleflow.core.exceptions import MethodExecutionError

			raise MethodExecutionError(
				_("Collection '{0}' exceeds maximum execution limit of {1} rows (got {2} rows).").format(
					self.source, self.MAX_COLLECTION_ROWS, len(rows)
				)
			)

		doc = context.get("doc")

		def _matches(r) -> bool:
			if not self._compiled_evaluator:
				return True
			return self._compiled_evaluator.evaluate(doc, row=r)

		op = self.operation

		if op == "count":
			if not self._compiled_evaluator:
				return len(rows)
			return sum(1 for r in rows if _matches(r))

		if op == "any":
			if not self._compiled_evaluator:
				return len(rows) > 0
			return any(_matches(r) for r in rows)

		if op == "all":
			if not self._compiled_evaluator:
				return True
			return all(_matches(r) for r in rows)

		if op == "first":
			for r in rows:
				if _matches(r):
					return r
			return None

		if op == "filter":
			return [r for r in rows if _matches(r)]

		if op == "pluck":
			if not self.target_field:
				return []
			return [self._get_row_field(r, self.target_field) for r in rows if _matches(r)]

		if op == "unique":
			if not self.target_field:
				return []
			seen = set()
			res = []
			for r in rows:
				if _matches(r):
					val = self._get_row_field(r, self.target_field)
					try:
						key = val
						if isinstance(val, dict | list):
							key = json.dumps(val, sort_keys=True)
					except Exception:
						key = str(val)
					if key not in seen:
						seen.add(key)
						res.append(val)
			return res

		return None

	@staticmethod
	def _get_row_field(row: Any, fieldname: str) -> Any:
		if row is None or not fieldname:
			return None
		if isinstance(row, dict) or hasattr(row, "get"):
			return row.get(fieldname)
		return getattr(row, fieldname, None)


class LookupResolver(CompiledResolver):
	"""
	Canonical Lookup Resolver for single-record database fetches or existence checks.
	Backward compatible with FetchResolver.
	"""

	def __init__(
		self,
		link_field: str | None = None,
		fetch_field: str | None = None,
		linked_doctype: str | None = None,
		operation: str = "get",
	):
		self.link_field = link_field
		self.fetch_field = fetch_field
		self.linked_doctype = linked_doctype
		self.operation = operation

	def resolve(self, context: dict) -> Any:
		if not self.link_field or not self.linked_doctype:
			return None

		path = self.link_field
		known_scopes = ("doc.", "vars.", "ctx.", "loop.", "row.", "item.", "caller.", "rule.")
		if not any(path.startswith(s) for s in known_scopes):
			path = f"doc.{path}"

		link_value = get_context_value(context, path)
		if not link_value:
			return False if getattr(self, "operation", "get") == "exists" else None

		if getattr(self, "operation", "get") == "exists":
			return bool(frappe.db.exists(self.linked_doctype, link_value))

		if not self.fetch_field:
			return None

		return frappe.db.get_value(self.linked_doctype, link_value, self.fetch_field)


class FetchResolver(LookupResolver):
	def __init__(self, link_field: str | None, fetch_field: str | None, linked_doctype: str | None):
		super().__init__(
			link_field=link_field,
			fetch_field=fetch_field,
			linked_doctype=linked_doctype,
			operation="get",
		)


class ConditionalResolver(CompiledResolver):
	"""
	Canonical Conditional Resolver evaluating an if-then-else condition structure.
	"""

	def __init__(
		self,
		condition: dict | list | None = None,
		true_value: Any = None,
		false_value: Any = None,
	):
		self.condition = condition
		self.true_value = true_value
		self.false_value = false_value
		self._compiled_evaluator = None

		if self.condition:
			from flexirule.ruleflow.core.evaluator import ConditionEvaluator

			cond_list = self.condition if isinstance(self.condition, list) else [self.condition]
			self._compiled_evaluator = ConditionEvaluator(json.dumps(cond_list))

	def resolve(self, context: dict) -> Any:
		doc = context.get("doc")
		is_true = False
		if self._compiled_evaluator:
			is_true = self._compiled_evaluator.evaluate(doc)

		target_raw = self.true_value if is_true else self.false_value
		return ValueResolver.compile(target_raw).resolve(context)


class TypeConversionResolver(CompiledResolver):
	"""
	Canonical Type Conversion Resolver casting input fields or values into specified types.
	"""

	def __init__(
		self,
		field: str | None = None,
		operation: str = "text",
		value: Any = None,
	):
		self.field = field
		self.operation = operation
		self.value = value

	def resolve(self, context: dict) -> Any:
		val = get_context_value(context, self.field) if self.field else self.value
		op = self.operation

		if op in ("text", "string"):
			return str(val) if val is not None else ""
		if op == "integer":
			return frappe.utils.cint(val)
		if op in ("decimal", "number", "float"):
			return frappe.utils.flt(val)
		if op in ("boolean", "bool"):
			return frappe.utils.cint(val) != 0 if isinstance(val, int | float | str) else bool(val)
		if op == "date":
			return frappe.utils.getdate(val) if val else None
		if op == "datetime":
			return frappe.utils.get_datetime(val) if val else None

		return val


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


class SystemContextResolver(CompiledResolver):
	"""Legacy SystemContextResolver for backward compatibility."""

	def __init__(self, sys_token: str, sys_role: str):
		self.sys_token = sys_token
		self.sys_role = sys_role

	def resolve(self, context: dict) -> Any:
		return ValueSourceResolver(
			operation="system_context", sys_token=self.sys_token, sys_role=self.sys_role
		).resolve(context)


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

		# Canonical Resolvers & Legacy Aliases
		if kind == "value_source":
			return ValueSourceResolver(
				operation=config.get("operation", "field"),
				path=config.get("path"),
				value=config.get("value"),
				sys_token=config.get("sys_token", "user"),
				sys_role=config.get("sys_role", ""),
			)

		if kind in ("date", "date_formula"):
			sign = config.get("offset_sign", "+")
			op = "subtract" if sign == "-" else "add"
			return DateResolver(
				operation=config.get("operation", op),
				base_type=config.get("base_type", "today"),
				base_field=config.get("base_field"),
				offset_value=config.get("offset_value", 0),
				offset_unit=config.get("offset_unit", "days"),
				offset_sign=sign,
			)

		if kind == "date_diff":
			return DateResolver(
				operation="diff",
				diff_start_type=config.get("diff_start_type", "today"),
				diff_start_field=config.get("diff_start_field"),
				diff_end_type=config.get("diff_end_type", "doc_field"),
				diff_end_field=config.get("diff_end_field"),
				diff_unit=config.get("diff_unit", "days"),
			)

		if kind in ("math", "math_formula"):
			return MathResolver(
				operation=config.get("operation", config.get("math_op", "+")),
				field_a=config.get("field_a"),
				field_b_type=config.get("field_b_type", "field"),
				field_b=config.get("field_b"),
				constant_b=config.get("constant_b", 0),
				precision=config.get("precision", 2),
			)

		if kind in ("text", "string_formula", "normalization", "format"):
			f_b = config.get("field_b") or config.get("str_b")
			f_b_type = config.get("field_b_type") or config.get("str_b_type")
			if (
				not f_b_type
				and f_b
				and isinstance(f_b, str)
				and (f_b.startswith("doc.") or f_b.startswith("vars."))
			):
				f_b_type = "field"

			default_op = (
				"normalize" if kind == "normalization" else ("format_date" if kind == "format" else "concat")
			)
			op = (
				config.get("operation")
				or config.get("str_op")
				or config.get("norm_op")
				or config.get("fmt_op")
				or default_op
			)

			return TextResolver(
				operation=op,
				field_a=config.get("field_a")
				or config.get("str_a")
				or config.get("norm_field")
				or config.get("fmt_field"),
				field_a_type=config.get("field_a_type") or config.get("str_a_type", "field"),
				field_b=f_b,
				field_b_type=f_b_type or "constant",
				norm_profile=config.get("norm_profile"),
				norm_pipeline=config.get("norm_pipeline"),
				fmt_config=config.get("fmt_config") or config.get("pattern"),
			)

		if kind in ("aggregate", "child_aggregation"):
			return AggregateResolver(
				agg_table=config.get("agg_table") or config.get("source"),
				agg_field=config.get("agg_field"),
				agg_op=config.get("agg_op", "sum"),
			)

		if kind == "collection":
			return CollectionResolver(
				source=config.get("source"),
				operation=config.get("operation", "any"),
				condition=config.get("condition"),
				target_field=config.get("target_field"),
			)

		if kind in ("lookup", "fetch"):
			return LookupResolver(
				link_field=config.get("link_field"),
				fetch_field=config.get("fetch_field"),
				linked_doctype=config.get("linked_doctype"),
				operation=config.get("operation", "get"),
			)

		if kind == "conditional":
			return ConditionalResolver(
				condition=config.get("condition"),
				true_value=config.get("true_value"),
				false_value=config.get("false_value"),
			)

		if kind == "type_conversion":
			return TypeConversionResolver(
				field=config.get("field"),
				operation=config.get("operation", "text"),
				value=config.get("value"),
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
