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


class DateCurrentResolver(CompiledResolver):
	def __init__(self, current_token: str = "date"):
		self.current_token = (current_token or "date").lower()

	def resolve(self, context: dict) -> Any:
		if self.current_token in ("datetime", "now"):
			return frappe.utils.get_datetime(frappe.utils.now_datetime())
		if self.current_token == "time":
			return frappe.utils.get_time(frappe.utils.nowtime())
		return frappe.utils.getdate(frappe.utils.nowdate())


class DateFormulaResolver(CompiledResolver):
	def __init__(
		self,
		base_type: str | None = None,
		base_field: str | None = None,
		offset_value: Any = 0,
		offset_unit: str = "days",
		offset_sign: str = "+",
		source: Any = None,
	):
		self.base_type = base_type
		self.base_field = base_field
		self.offset_value = offset_value
		self.offset_unit = offset_unit
		self.offset_sign = offset_sign
		self.source = source

		# Compile base source
		if self.source is not None:
			self.base_compiled = ValueResolver.compile(self.source)
		elif self.base_type in ("today", "current_date"):
			self.base_compiled = DateCurrentResolver("date")
		elif self.base_type in ("current_datetime", "now"):
			self.base_compiled = DateCurrentResolver("datetime")
		elif self.base_type == "current_time":
			self.base_compiled = DateCurrentResolver("time")
		elif self.base_field:
			self.base_compiled = VariableResolver(self.base_field)
		else:
			self.base_compiled = NoneResolver()

		# Compile offset
		if isinstance(self.offset_value, dict) or (
			isinstance(self.offset_value, str)
			and (self.offset_value.startswith("doc.") or self.offset_value.startswith("vars."))
		):
			self.offset_compiled = ValueResolver.compile(self.offset_value)
		else:
			self.offset_compiled = None

	def resolve(self, context: dict) -> Any:
		base_date = self.base_compiled.resolve(context)
		if base_date is None or base_date == "":
			return None

		if self.offset_compiled:
			raw_offset = self.offset_compiled.resolve(context)
		else:
			raw_offset = self.offset_value

		try:
			offset = float(raw_offset) if raw_offset is not None else 0.0
			if offset.is_integer():
				offset = int(offset)
		except (ValueError, TypeError):
			offset = 0

		if self.offset_sign == "-" and offset > 0:
			offset = -offset

		if offset == 0 or not self.offset_unit:
			return base_date

		import datetime

		unit = self.offset_unit.lower()

		if isinstance(base_date, datetime.time):
			dt_dummy = datetime.datetime.combine(datetime.date.today(), base_date)
			res_dt = frappe.utils.add_to_date(dt_dummy, as_string=False, **{unit: offset})
			return res_dt.time()

		if isinstance(base_date, str):
			base_str = base_date.strip()
			if " " in base_str or "T" in base_str:
				base_date = frappe.utils.get_datetime(base_str)
			elif ":" in base_str and len(base_str) <= 8:
				base_date = frappe.utils.get_time(base_str)
				dt_dummy = datetime.datetime.combine(datetime.date.today(), base_date)
				res_dt = frappe.utils.add_to_date(dt_dummy, as_string=False, **{unit: offset})
				return res_dt.time()
			else:
				base_date = frappe.utils.getdate(base_str)

		if unit == "days" and isinstance(base_date, datetime.date) and not isinstance(base_date, datetime.datetime):
			return frappe.utils.add_days(base_date, offset)

		return frappe.utils.add_to_date(base_date, as_string=False, **{unit: offset})


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
		diff_start_type: str | None = None,
		diff_start_field: str | None = None,
		diff_end_type: str | None = None,
		diff_end_field: str | None = None,
		diff_unit: str = "days",
		start_source: Any = None,
		end_source: Any = None,
	):
		self.diff_start_type = diff_start_type
		self.diff_start_field = diff_start_field
		self.diff_end_type = diff_end_type
		self.diff_end_field = diff_end_field
		self.diff_unit = diff_unit or "days"

		if start_source is not None:
			self.start_compiled = ValueResolver.compile(start_source)
		elif self.diff_start_type in ("today", "current_date"):
			self.start_compiled = DateCurrentResolver("date")
		elif self.diff_start_type in ("current_datetime", "now"):
			self.start_compiled = DateCurrentResolver("datetime")
		elif self.diff_start_field:
			self.start_compiled = VariableResolver(self.diff_start_field)
		else:
			self.start_compiled = NoneResolver()

		if end_source is not None:
			self.end_compiled = ValueResolver.compile(end_source)
		elif self.diff_end_type in ("today", "current_date"):
			self.end_compiled = DateCurrentResolver("date")
		elif self.diff_end_type in ("current_datetime", "now"):
			self.end_compiled = DateCurrentResolver("datetime")
		elif self.diff_end_field:
			self.end_compiled = VariableResolver(self.diff_end_field)
		else:
			self.end_compiled = NoneResolver()

	def resolve(self, context: dict) -> Any:
		start = self.start_compiled.resolve(context)
		end = self.end_compiled.resolve(context)

		if start is None or end is None or start == "" or end == "":
			return 0

		unit = self.diff_unit.lower()

		if unit == "days":
			return frappe.utils.date_diff(end, start)
		if unit == "months":
			return frappe.utils.month_diff(end, start)
		if unit == "years":
			return int(frappe.utils.month_diff(end, start) / 12)

		if unit in ("hours", "minutes", "seconds"):
			sec_diff = frappe.utils.time_diff_in_seconds(end, start)
			if unit == "seconds":
				return int(sec_diff)
			if unit == "minutes":
				return float(sec_diff / 60.0)
			if unit == "hours":
				return float(sec_diff / 3600.0)

		return frappe.utils.date_diff(end, start)


class DateExtractResolver(CompiledResolver):
	def __init__(self, source: Any = None, component: str = "year"):
		self.component = (component or "year").lower()
		self.source_compiled = ValueResolver.compile(source) if source is not None else NoneResolver()

	def resolve(self, context: dict) -> Any:
		val = self.source_compiled.resolve(context)
		if val is None or val == "":
			return None

		import datetime

		if isinstance(val, str):
			val_str = val.strip()
			if " " in val_str or "T" in val_str:
				val = frappe.utils.get_datetime(val_str)
			elif ":" in val_str and len(val_str) <= 8:
				val = frappe.utils.get_time(val_str)
			else:
				val = frappe.utils.getdate(val_str)

		comp = self.component

		if comp in ("year", "month", "day", "weekday", "quarter"):
			if isinstance(val, datetime.time) and not isinstance(val, datetime.date):
				return None
			if comp == "year":
				return val.year
			if comp == "month":
				return val.month
			if comp == "day":
				return val.day
			if comp == "weekday":
				# ISO 8601: 1 = Monday .. 7 = Sunday
				return val.isoweekday()
			if comp == "quarter":
				return (val.month - 1) // 3 + 1

		if comp in ("hour", "minute", "second"):
			if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime):
				return None
			if comp == "hour":
				return val.hour
			if comp == "minute":
				return val.minute
			if comp == "second":
				return val.second

		return None


class DateBoundaryResolver(CompiledResolver):
	def __init__(self, source: Any = None, boundary_type: str = "start_of_month"):
		self.boundary_type = (boundary_type or "start_of_month").lower()
		self.source_compiled = ValueResolver.compile(source) if source is not None else NoneResolver()

	def resolve(self, context: dict) -> Any:
		val = self.source_compiled.resolve(context)
		if val is None or val == "":
			return None

		import datetime

		is_datetime = False
		is_time_only = False

		if isinstance(val, datetime.datetime):
			is_datetime = True
		elif isinstance(val, datetime.date):
			is_datetime = False
		elif isinstance(val, str):
			val_str = val.strip()
			if " " in val_str or "T" in val_str:
				val = frappe.utils.get_datetime(val_str)
				is_datetime = True
			elif ":" in val_str and len(val_str) <= 8:
				is_time_only = True
			else:
				val = frappe.utils.getdate(val_str)
				is_datetime = False

		if is_time_only:
			return None

		btype = self.boundary_type

		if btype == "start_of_day":
			if is_datetime:
				return val.replace(hour=0, minute=0, second=0, microsecond=0)
			return val

		if btype == "end_of_day":
			if is_datetime:
				return val.replace(hour=23, minute=59, second=59, microsecond=0)
			return val

		if btype == "start_of_week":
			start_d = frappe.utils.getdate(frappe.utils.get_first_day_of_week(val))
			return frappe.utils.get_datetime(start_d).replace(hour=0, minute=0, second=0, microsecond=0) if is_datetime else start_d

		if btype == "end_of_week":
			start_d = frappe.utils.getdate(frappe.utils.get_first_day_of_week(val))
			end_d = start_d + datetime.timedelta(days=6)
			return frappe.utils.get_datetime(end_d).replace(hour=23, minute=59, second=59, microsecond=0) if is_datetime else end_d

		if btype == "start_of_month":
			start_d = frappe.utils.getdate(frappe.utils.get_first_day(val))
			return frappe.utils.get_datetime(start_d).replace(hour=0, minute=0, second=0, microsecond=0) if is_datetime else start_d

		if btype == "end_of_month":
			end_d = frappe.utils.getdate(frappe.utils.get_last_day(val))
			return frappe.utils.get_datetime(end_d).replace(hour=23, minute=59, second=59, microsecond=0) if is_datetime else end_d

		if btype == "start_of_quarter":
			start_d = frappe.utils.getdate(frappe.utils.get_quarter_start(val))
			return frappe.utils.get_datetime(start_d).replace(hour=0, minute=0, second=0, microsecond=0) if is_datetime else start_d

		if btype == "end_of_quarter":
			q_start = frappe.utils.getdate(frappe.utils.get_quarter_start(val))
			end_d = frappe.utils.add_to_date(q_start, months=3, days=-1, as_string=False)
			return frappe.utils.get_datetime(end_d).replace(hour=23, minute=59, second=59, microsecond=0) if is_datetime else end_d

		if btype == "start_of_year":
			start_d = datetime.date(val.year, 1, 1)
			return datetime.datetime(val.year, 1, 1, 0, 0, 0) if is_datetime else start_d

		if btype == "end_of_year":
			end_d = datetime.date(val.year, 12, 31)
			return datetime.datetime(val.year, 12, 31, 23, 59, 59) if is_datetime else end_d

		return val


class CollectionResolver(CompiledResolver):
	"""
	Compiled resolver strategy for querying, checking, filtering, and extracting
	values from child table collections or list variables.
	"""

	MAX_COLLECTION_ROWS = 10000

	def __init__(
		self,
		source: str | None,
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
			if self.operation in ("sum", "avg"):
				return 0.0 if self.operation == "avg" else 0
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

		if op in ("sum", "avg"):
			if not self.target_field:
				return 0.0 if op == "avg" else 0
			values = [
				frappe.utils.flt(self._get_row_field(r, self.target_field))
				for r in rows
				if _matches(r) and self._get_row_field(r, self.target_field) is not None
			]
			if op == "sum":
				return sum(values) if values else 0
			if op == "avg":
				return sum(values) / len(values) if values else 0.0

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


class ChildAggregationResolver(CompiledResolver):
	def __init__(self, agg_table: str | None, agg_field: str | None, agg_op: str):
		self.agg_table = agg_table
		self.agg_field = agg_field
		self.agg_op = agg_op

	def resolve(self, context: dict) -> Any:
		return CollectionResolver(
			source=self.agg_table,
			operation=self.agg_op,
			target_field=self.agg_field,
		).resolve(context)


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

		result = execute_normalization_pipeline(value=val, pipeline=pipeline, profile=self.norm_profile)
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


class LookupResolver(CompiledResolver):
	"""
	Canonical resolver strategy for fetching record values from another DocType.
	Supports both static target DocType and dynamic DocType resolution (Dynamic Link).
	"""

	def __init__(
		self,
		doctype_mode: str = "static",
		target_doctype: str | None = None,
		doctype_source: str | None = None,
		record_field: str | None = None,
		fetch_field: str | None = None,
		linked_doctype: str | None = None,
		link_field: str | None = None,
	):
		self.doctype_mode = doctype_mode or "static"
		self.target_doctype = target_doctype or linked_doctype
		self.doctype_source = doctype_source
		self.record_field = record_field or link_field
		self.fetch_field = fetch_field

	@staticmethod
	def _resolve_scoped_value(context: dict, path: str | None) -> Any:
		if not path:
			return None
		path_str = str(path).strip()
		if not path_str:
			return None

		known_scopes = ("doc.", "vars.", "ctx.", "loop.", "row.", "item.", "caller.", "rule.")
		if any(path_str.startswith(s) for s in known_scopes):
			return get_context_value(context, path_str)

		if "row" in context and context["row"] is not None:
			val = get_context_value(context, f"row.{path_str}")
			if val is not None:
				return val
		if "item" in context and context["item"] is not None:
			val = get_context_value(context, f"item.{path_str}")
			if val is not None:
				return val

		return get_context_value(context, f"doc.{path_str}")

	def resolve(self, context: dict) -> Any:
		if not self.fetch_field or not self.record_field:
			return None

		# Determine target DocType
		if self.doctype_mode == "dynamic":
			if not self.doctype_source:
				return None
			resolved_doctype = self._resolve_scoped_value(context, self.doctype_source)
		else:
			resolved_doctype = self.target_doctype
			if resolved_doctype and isinstance(resolved_doctype, str):
				known_scopes = ("doc.", "vars.", "ctx.", "loop.", "row.", "item.", "caller.", "rule.")
				if any(resolved_doctype.startswith(s) for s in known_scopes):
					resolved_doctype = get_context_value(context, resolved_doctype)

		if not resolved_doctype or not isinstance(resolved_doctype, str):
			return None

		resolved_doctype = resolved_doctype.strip()
		if not resolved_doctype:
			return None

		# Check permission for non-Administrator sessions
		if (
			hasattr(frappe, "session")
			and frappe.session
			and getattr(frappe.session, "user", None)
			and frappe.session.user != "Administrator"
		):
			if not frappe.has_permission(resolved_doctype, "read"):
				raise frappe.PermissionError(
					_("Insufficient permission to read DocType '{0}'.").format(resolved_doctype)
				)

		# Resolve record name / ID
		link_value = self._resolve_scoped_value(context, self.record_field)
		if not link_value:
			return None

		return frappe.db.get_value(resolved_doctype, link_value, self.fetch_field)


class FetchResolver(LookupResolver):
	"""Legacy alias for LookupResolver."""

	def __init__(self, link_field: str | None, fetch_field: str | None, linked_doctype: str | None):
		super().__init__(
			doctype_mode="static",
			target_doctype=linked_doctype,
			doctype_source=None,
			record_field=link_field,
			fetch_field=fetch_field,
		)


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

			if (
				mode in ("resolver", "formatter", "normalize", "format", "normalization")
				or "kind" in val
				or "family" in val
			):
				config = val.get("config")
				if isinstance(config, dict):
					merged = {**config}
					if "kind" in val and "kind" not in merged:
						merged["kind"] = val["kind"]
					if "family" in val and "family" not in merged:
						merged["family"] = val["family"]
					if "operation" in val and "operation" not in merged:
						merged["operation"] = val["operation"]
					return ValueResolver.compile_resolver_config(merged)
				return ValueResolver.compile_resolver_config(val)

			if "value" in val:
				return StaticResolver(val.get("value"))

		if isinstance(val, str):
			if "{{" in val or "{%" in val:
				return JinjaResolver(val)
			if val.startswith("{") and val.endswith("}") and val.count("{") == 1:
				return SafeEvalResolver(val[1:-1])
			if any(val.startswith(p) for p in ("doc.", "vars.", "item.", "row.", "loop.", "caller.", "rule.", "ctx.")):
				return VariableResolver(val)
			return StaticResolver(val)

		return StaticResolver(val)

	@staticmethod
	def compile_resolver_config(config: dict) -> CompiledResolver:
		if not isinstance(config, dict):
			return NoneResolver()

		raw_inner = config.get("config")
		inner_dict: dict[str, Any] = raw_inner if isinstance(raw_inner, dict) else {}

		family = config.get("family") or inner_dict.get("family")
		kind = config.get("kind") or inner_dict.get("kind")

		if family == "collection" or kind == "collection":
			source = inner_dict.get("source") or config.get("source")
			operation = inner_dict.get("operation") or config.get("operation") or "any"
			condition = inner_dict.get("condition") if "condition" in inner_dict else config.get("condition")
			target_field = inner_dict.get("target_field") or config.get("target_field")
			return CollectionResolver(
				source=source,
				operation=operation,
				condition=condition,
				target_field=target_field,
			)

		if kind == "child_aggregation" or family == "child_aggregation":
			source = (
				inner_dict.get("source")
				or inner_dict.get("agg_table")
				or config.get("agg_table")
				or config.get("source")
			)
			target_field = (
				inner_dict.get("target_field")
				or inner_dict.get("agg_field")
				or config.get("agg_field")
				or config.get("target_field")
			)
			operation = (
				inner_dict.get("operation")
				or inner_dict.get("agg_op")
				or config.get("agg_op")
				or config.get("operation")
				or "sum"
			)
			condition = inner_dict.get("condition") if "condition" in inner_dict else config.get("condition")
			return CollectionResolver(
				source=source,
				operation=operation,
				condition=condition,
				target_field=target_field,
			)

		if family == "text" or kind == "text":
			op = config.get("operation") or inner_dict.get("operation") or "combine"

			if op == "combine":
				return StringFormulaResolver(
					str_op="concat",
					str_a_type=inner_dict.get("str_a_type") or config.get("str_a_type", "field"),
					str_a=inner_dict.get("str_a") or config.get("str_a"),
					str_b_type=inner_dict.get("str_b_type") or config.get("str_b_type", "constant"),
					str_b=inner_dict.get("str_b") or config.get("str_b"),
				)
			if op == "case":
				mode = inner_dict.get("case_mode") or config.get("case_mode", "uppercase")
				fld = inner_dict.get("field") or config.get("field")
				if mode in ("uppercase", "lowercase"):
					return StringFormulaResolver(
						str_op=mode,
						str_a_type="field",
						str_a=fld,
						str_b_type="constant",
						str_b="",
					)
				return NormalizationResolver(
					norm_field=fld,
					norm_pipeline=[mode],
				)
			if op == "normalize":
				return NormalizationResolver(
					norm_field=inner_dict.get("norm_field") or config.get("norm_field"),
					norm_profile=inner_dict.get("norm_profile") or config.get("norm_profile"),
					norm_pipeline=inner_dict.get("norm_pipeline") or config.get("norm_pipeline"),
					norm_op=inner_dict.get("norm_op") or config.get("norm_op"),
				)
			if op == "format":
				return FormatResolver(
					fmt_op="format",
					fmt_field=inner_dict.get("fmt_field") or config.get("fmt_field"),
					fmt_config=inner_dict.get("fmt_config") or config.get("fmt_config", ""),
				)

		if family == "date_time" or kind == "date_time":
			op = config.get("operation") or inner_dict.get("operation") or "calculate"

			if op == "current":
				return DateCurrentResolver(
					current_token=inner_dict.get("token") or config.get("token") or "date"
				)
			if op == "calculate":
				return DateFormulaResolver(
					base_type=inner_dict.get("base_type") or config.get("base_type"),
					base_field=inner_dict.get("base_field") or config.get("base_field"),
					offset_value=inner_dict.get("offset_value")
					if "offset_value" in inner_dict
					else config.get("offset_value", 0),
					offset_unit=inner_dict.get("offset_unit") or config.get("offset_unit", "days"),
					offset_sign=inner_dict.get("offset_sign") or config.get("offset_sign", "+"),
					source=inner_dict.get("source") if "source" in inner_dict else config.get("source"),
				)
			if op == "diff":
				return DateDiffResolver(
					diff_start_type=inner_dict.get("diff_start_type")
					or config.get("diff_start_type"),
					diff_start_field=inner_dict.get("diff_start_field") or config.get("diff_start_field"),
					diff_end_type=inner_dict.get("diff_end_type")
					or config.get("diff_end_type"),
					diff_end_field=inner_dict.get("diff_end_field") or config.get("diff_end_field"),
					diff_unit=inner_dict.get("diff_unit") or config.get("diff_unit", "days"),
					start_source=inner_dict.get("start_source") if "start_source" in inner_dict else config.get("start_source"),
					end_source=inner_dict.get("end_source") if "end_source" in inner_dict else config.get("end_source"),
				)
			if op == "extract":
				return DateExtractResolver(
					source=inner_dict.get("source") if "source" in inner_dict else (config.get("source") or inner_dict.get("base_field") or config.get("base_field")),
					component=inner_dict.get("component") or config.get("component", "year"),
				)
			if op == "boundary":
				return DateBoundaryResolver(
					source=inner_dict.get("source") if "source" in inner_dict else (config.get("source") or inner_dict.get("base_field") or config.get("base_field")),
					boundary_type=inner_dict.get("boundary_type") or config.get("boundary_type", "start_of_month"),
				)
			if op == "format":
				return FormatResolver(
					fmt_op="format_date",
					fmt_field=inner_dict.get("fmt_field") or config.get("fmt_field"),
					fmt_config=inner_dict.get("fmt_config") or config.get("fmt_config", "YYYY-MM-DD"),
				)

		if not kind and not family:
			return NoneResolver()

		if kind == "math_formula":
			return MathFormulaResolver(
				field_a=config.get("field_a"),
				math_op=config.get("math_op", "+"),
				field_b_type=config.get("field_b_type", "field"),
				field_b=config.get("field_b"),
				constant_b=config.get("constant_b", 0),
				precision=config.get("precision", 2),
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
		if family == "lookup" or kind == "lookup" or kind == "fetch":
			doctype_source = inner_dict.get("doctype_source") or config.get("doctype_source")
			doctype_mode = (
				inner_dict.get("doctype_mode")
				or config.get("doctype_mode")
				or ("dynamic" if doctype_source else "static")
			)
			target_doctype = (
				inner_dict.get("target_doctype")
				or inner_dict.get("linked_doctype")
				or config.get("target_doctype")
				or config.get("linked_doctype")
			)
			record_field = (
				inner_dict.get("record_field")
				or inner_dict.get("link_field")
				or config.get("record_field")
				or config.get("link_field")
			)
			fetch_field = inner_dict.get("fetch_field") or config.get("fetch_field")

			return LookupResolver(
				doctype_mode=doctype_mode,
				target_doctype=target_doctype,
				doctype_source=doctype_source,
				record_field=record_field,
				fetch_field=fetch_field,
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
