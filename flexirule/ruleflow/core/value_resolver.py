# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

import frappe
from frappe import _

from flexirule.ruleflow.core.condition_errors import ConditionEvaluationError, ConditionValidationError
from flexirule.ruleflow.core.flexvalue_contract import (
	BASE_SCOPES,
	CONDITION_RESOLVER_REGISTRY,
	FRAPPE_VALUE_TYPES,
	MAX_FLEXVALUE_DEPTH,
	MAX_PATH_SEGMENTS,
	MAX_RESOLVER_DEPTH,
	MAX_STATIC_ITEMS,
	MAX_TEMPLATE_OUTPUT_CHARS,
	MAX_TEMPLATE_SEGMENTS,
	MISSING,
	VALUE_TYPES,
	_exact_keys,
	_fail,
	_validate_json_value,
	_validate_path,
	format_template_value,
	parse_static_value,
	resolve_variable,
	safe_read_segment,
)
from flexirule.ruleflow.core.flexvalue_contract import (
	MAX_COLLECTION_ROWS as CONDITION_MAX_COLLECTION_ROWS,
)
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
		self.offset_compiled: CompiledResolver | None
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

		if (
			unit == "days"
			and isinstance(base_date, datetime.date)
			and not isinstance(base_date, datetime.datetime)
		):
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
			return (
				frappe.utils.get_datetime(start_d).replace(hour=0, minute=0, second=0, microsecond=0)
				if is_datetime
				else start_d
			)

		if btype == "end_of_week":
			start_d = frappe.utils.getdate(frappe.utils.get_first_day_of_week(val))
			end_d = start_d + datetime.timedelta(days=6)
			return (
				frappe.utils.get_datetime(end_d).replace(hour=23, minute=59, second=59, microsecond=0)
				if is_datetime
				else end_d
			)

		if btype == "start_of_month":
			start_d = frappe.utils.getdate(frappe.utils.get_first_day(val))
			return (
				frappe.utils.get_datetime(start_d).replace(hour=0, minute=0, second=0, microsecond=0)
				if is_datetime
				else start_d
			)

		if btype == "end_of_month":
			end_d = frappe.utils.getdate(frappe.utils.get_last_day(val))
			return (
				frappe.utils.get_datetime(end_d).replace(hour=23, minute=59, second=59, microsecond=0)
				if is_datetime
				else end_d
			)

		if btype == "start_of_quarter":
			start_d = frappe.utils.getdate(frappe.utils.get_quarter_start(val))
			return (
				frappe.utils.get_datetime(start_d).replace(hour=0, minute=0, second=0, microsecond=0)
				if is_datetime
				else start_d
			)

		if btype == "end_of_quarter":
			q_start = frappe.utils.getdate(frappe.utils.get_quarter_start(val))
			end_d = frappe.utils.add_to_date(q_start, months=3, days=-1, as_string=False)
			return (
				frappe.utils.get_datetime(end_d).replace(hour=23, minute=59, second=59, microsecond=0)
				if is_datetime
				else end_d
			)

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

	MAX_COLLECTION_ROWS = CONDITION_MAX_COLLECTION_ROWS

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
		self._canonical_condition = None
		self._compiled_evaluator = None

		if self.condition:
			from flexirule.ruleflow.core.condition_contract import validate_condition_node
			from flexirule.ruleflow.core.condition_payload import detect_canonical_condition_payload

			is_canonical, canonical_node = detect_canonical_condition_payload(self.condition)
			if is_canonical:
				validate_condition_node(canonical_node)
				self._canonical_condition = canonical_node
			else:
				from flexirule.ruleflow.core.evaluator import ConditionEvaluator

				cond_list = self.condition if isinstance(self.condition, list) else [self.condition]
				self._compiled_evaluator = ConditionEvaluator(json.dumps(cond_list))

	def _resolve_child_doctype(self, parent_doctype: str | None) -> str | None:
		if not parent_doctype or not self.source:
			return None
		source_str = str(self.source).strip()
		if source_str.startswith("doc."):
			segments = source_str.split(".")[1:]
			scope = "doc"
		elif source_str.startswith("vars."):
			return None
		elif "." in source_str:
			parts = source_str.split(".")
			scope = parts[0]
			segments = parts[1:]
		else:
			scope = "doc"
			segments = [source_str]

		if scope != "doc":
			return None

		import frappe

		try:
			meta = frappe.get_meta(parent_doctype)
			current_meta = meta
			field = None
			for seg in segments:
				field = current_meta.get_field(seg)
				if not field:
					raise ConditionValidationError(
						"unknown_field",
						"$.source",
						f"Collection source field '{seg}' does not exist on DocType '{parent_doctype}'",
					)
				if seg != segments[-1]:
					if field.fieldtype in {"Table", "Table MultiSelect"}:
						current_meta = frappe.get_meta(field.options)
					else:
						raise ConditionValidationError(
							"invalid_collection_source",
							"$.source",
							"Collection source path continues through a scalar field",
						)
			if field and field.fieldtype in {"Table", "Table MultiSelect"}:
				child_dt = field.options
				if not child_dt:
					raise ConditionValidationError(
						"unknown_doctype",
						"$.source",
						f"Child DocType is not configured for table field '{field.fieldname}'",
					)
				# Authoritative check: child DocType must exist
				try:
					frappe.get_meta(child_dt)
				except Exception as exc:
					raise ConditionValidationError(
						"unknown_doctype",
						"$.source",
						f"Could not resolve metadata for child DocType '{child_dt}'",
					) from exc
				return child_dt
			elif field:
				raise ConditionValidationError(
					"collection_source_not_table",
					"$.source",
					f"Collection source '{self.source}' must reference a table/list field",
				)
		except ConditionValidationError:
			raise
		except Exception as exc:
			raise ConditionValidationError(
				"unknown_doctype",
				"$.source",
				f"Could not resolve metadata for DocType '{parent_doctype}'",
			) from exc
		return None

	def resolve(self, context: dict) -> Any:
		doc = context.get("doc")
		condition_doctype = getattr(doc, "doctype", None)
		if not condition_doctype and isinstance(doc, dict):
			condition_doctype = doc.get("doctype")
		condition_doctype = condition_doctype or context.get("doctype")

		source_str = str(self.source or "").strip()
		is_doc_backed = source_str.startswith("doc.") or (
			not source_str.startswith("vars.") and "." not in source_str
		)
		has_condition = bool(
			self._canonical_condition is not None or self._compiled_evaluator or self.condition
		)

		if is_doc_backed and has_condition and not condition_doctype:
			from flexirule.ruleflow.core.condition_errors import ConditionValidationError

			raise ConditionValidationError(
				"unknown_doctype",
				"$.source",
				f"Parent DocType metadata is required to validate collection predicate for '{self.source}'",
			)

		child_doctype = self._resolve_child_doctype(condition_doctype)
		scope_doctypes: dict[str, str | None] | None = {"row": child_doctype} if child_doctype else None

		prepared_condition = None
		if self._canonical_condition is not None:
			from flexirule.ruleflow.core.condition_evaluator import prepare_condition

			prepared_condition = prepare_condition(
				self._canonical_condition,
				doctype=condition_doctype,
				scope_doctypes=scope_doctypes,
			)

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

		condition_evaluation_budget = {"collection_row_visits": 0}

		def _matches(r) -> bool:
			if self._canonical_condition is not None:
				from flexirule.ruleflow.core.condition_evaluator import (
					consume_collection_row_visit,
					evaluate_prepared_condition,
				)

				consume_collection_row_visit(condition_evaluation_budget, "CollectionResolver.condition")
				row_context = dict(context)
				row_context["doc"] = doc
				row_context["row"] = r
				return evaluate_prepared_condition(
					prepared_condition,
					row_context,
					doctype=condition_doctype,
					_evaluation_budget=condition_evaluation_budget,
				)
			if not self._compiled_evaluator:
				return True
			return self._compiled_evaluator.evaluate(doc, row=r)

		op = self.operation

		if op == "count":
			if self._canonical_condition is None and not self._compiled_evaluator:
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
			if self._canonical_condition is None and not self._compiled_evaluator:
				return len(rows) > 0
			return any(_matches(r) for r in rows)

		if op == "all":
			if self._canonical_condition is None and not self._compiled_evaluator:
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
	Single authoritative registry, validation, compilation, and runtime resolution pipeline.
	"""

	REGISTRY = CONDITION_RESOLVER_REGISTRY
	_REGISTRY_FINGERPRINT_CACHE: ClassVar[str | None] = None

	@classmethod
	def register_resolver(
		cls,
		family: str,
		operation: str,
		*,
		label: str,
		output_type: str,
		config_schema: dict[str, Any],
		permission_policy: str,
		validate_config: Callable[[dict, str, set[str], int, int], None],
		factory: Callable[[dict, Any], CompiledResolver],
		supported_consumers: set[str] | None = None,
		condition_operand_allowed: bool = False,
		required_capability: str = "condition_operand",
	):
		"""Register a reviewed resolver operation."""
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
			or not isinstance(condition_operand_allowed, bool)
			or not isinstance(required_capability, str)
			or not required_capability
		):
			raise ValueError("Invalid resolver registration")
		try:
			config_schema_copy = json.loads(
				json.dumps(config_schema, sort_keys=True, allow_nan=False, separators=(",", ":"))
			)
		except (TypeError, ValueError, RecursionError) as exc:
			raise ValueError("Resolver config_schema must be JSON-serializable") from exc
		if not callable(validate_config) or not callable(factory):
			raise ValueError("Resolver validator and factory must be callable")

		key = (family, operation)
		cls.REGISTRY[key] = {
			"family": family,
			"operation": operation,
			"label": label,
			"output_type": output_type,
			"config_schema": config_schema_copy,
			"permission_policy": permission_policy,
			"required_capability": required_capability,
			"condition_operand_allowed": bool(condition_operand_allowed),
			"supported_consumers": set(supported_consumers or {"all"}),
			"validate_config": validate_config,
			"factory": factory,
			"resolve": lambda cfg, ctx: factory(cfg, None).resolve(ctx),
		}
		cls._REGISTRY_FINGERPRINT_CACHE = None

	@classmethod
	def registry_fingerprint(cls) -> str:
		"""Stable cache key material; implementation callables stay private."""
		if cls._REGISTRY_FINGERPRINT_CACHE is None:
			payload = json.dumps(
				cls.resolver_contract_dto(),
				sort_keys=True,
				ensure_ascii=False,
				separators=(",", ":"),
				allow_nan=False,
			)
			cls._REGISTRY_FINGERPRINT_CACHE = hashlib.sha256(payload.encode("utf-8")).hexdigest()
		return cls._REGISTRY_FINGERPRINT_CACHE

	@classmethod
	def resolver_contract_dto(cls) -> list[dict[str, Any]]:
		"""Return public metadata only; internal functions are never exposed."""
		return [
			{
				"family": item["family"],
				"operation": item["operation"],
				"label": item["label"],
				"output_type": item["output_type"],
				"config_schema": json.loads(json.dumps(item["config_schema"], sort_keys=True)),
				"permission_policy": item["permission_policy"],
				"required_capability": item["required_capability"],
				"condition_operand_allowed": bool(item["condition_operand_allowed"]),
				"supported_consumers": sorted(item.get("supported_consumers", ["all"])),
			}
			for _, item in sorted(cls.REGISTRY.items())
		]

	@classmethod
	def validate_flex_value(
		cls,
		value: Any,
		*,
		path: str = "$",
		allowed_scopes: set[str] | None = None,
		consumer: str | None = None,
		resolver_depth: int = 0,
		flexvalue_depth: int = 0,
	) -> str | None:
		"""Validate canonical FlexValue structure and return known output type."""
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

			if val is None:
				if value_type == "null":
					return "null"
				return str(value_type)

			if value_type in {
				"string",
				"Data",
				"Small Text",
				"Text",
				"Text Editor",
				"Code",
				"Select",
				"Link",
				"Dynamic Link",
			} and not isinstance(val, str):
				_fail("invalid_static_type", f"{path}.value", "Expected a string")
			elif value_type in {"integer", "Int"} and not (
				isinstance(val, int) and not isinstance(val, bool)
			):
				_fail("invalid_static_type", f"{path}.value", "Expected an integer (not a boolean)")
			elif value_type == "decimal":
				if not isinstance(val, str):
					_fail(
						"invalid_static_type", f"{path}.value", "Decimal values must be serialized as strings"
					)
				try:
					number = Decimal(val)
				except (InvalidOperation, ValueError):
					_fail("invalid_decimal", f"{path}.value", "Decimal value is not valid")
				if not number.is_finite():
					_fail("invalid_decimal", f"{path}.value", "Decimal value must be finite")
			elif value_type in {"Float", "Currency", "Percent"}:
				if isinstance(val, int | float) and not isinstance(val, bool):
					if isinstance(val, float) and not math.isfinite(val):
						_fail("invalid_decimal", f"{path}.value", "Decimal value must be finite")
				elif isinstance(val, str):
					try:
						number = Decimal(val)
					except (InvalidOperation, ValueError):
						_fail("invalid_decimal", f"{path}.value", "Decimal value is not valid")
					if not number.is_finite():
						_fail("invalid_decimal", f"{path}.value", "Decimal value must be finite")
				else:
					_fail(
						"invalid_static_type",
						f"{path}.value",
						"Numeric values must be numbers or decimal strings",
					)
			elif value_type == "boolean" and not isinstance(val, bool):
				_fail("invalid_static_type", f"{path}.value", "Expected a boolean")
			elif value_type == "Check" and val not in (0, 1):
				_fail("invalid_static_type", f"{path}.value", "Check values must be Frappe-compatible 0 or 1")
			elif value_type == "null" and val is not None:
				_fail("invalid_static_type", f"{path}.value", "Null values must be JSON null")
			elif value_type in {"date", "Date"}:
				if not isinstance(val, str):
					_fail("invalid_static_type", f"{path}.value", "Dates must be ISO strings")
				try:
					if date.fromisoformat(val).isoformat() != val:
						raise ValueError
				except ValueError:
					_fail("invalid_date", f"{path}.value", "Expected an ISO date in YYYY-MM-DD format")
			elif value_type in {"datetime", "Datetime"}:
				if not isinstance(val, str):
					_fail("invalid_static_type", f"{path}.value", "Datetimes must be ISO strings")
				try:
					datetime.fromisoformat(val[:-1] + "+00:00" if val.endswith("Z") else val)
				except ValueError:
					_fail("invalid_datetime", f"{path}.value", "Expected a valid ISO datetime")
			elif value_type in {"time", "Time", "Duration"}:
				if not isinstance(val, str):
					_fail("invalid_static_type", f"{path}.value", "Times must be ISO strings")
				try:
					time.fromisoformat(val)
				except ValueError:
					_fail("invalid_time", f"{path}.value", "Expected a valid ISO time")
			elif value_type in {"list", "Table", "Table MultiSelect"}:
				if not isinstance(val, list):
					_fail("invalid_static_type", f"{path}.value", "Expected a list")
				_validate_json_value(val, f"{path}.value")
			elif value_type in {"object", "JSON"}:
				if not isinstance(val, dict | list | str | int | float | bool):
					_fail("invalid_static_type", f"{path}.value", "Expected a valid JSON value")
				_validate_json_value(val, f"{path}.value")
			return str(value_type)

		if mode == "variable":
			_exact_keys(value, {"mode", "path"}, set(), path)
			_validate_path(value.get("path"), f"{path}.path", allowed)
			return None

		if mode == "resolver":
			_exact_keys(value, {"mode", "family", "operation", "config"}, {"value_type"}, path)
			family = value.get("family")
			operation = value.get("operation")
			if not isinstance(family, str) or not family:
				_fail("invalid_resolver_family", f"{path}.family", "Resolver family is required")
			if not isinstance(operation, str) or not operation:
				_fail("invalid_resolver_operation", f"{path}.operation", "Resolver operation is required")
			if resolver_depth >= MAX_RESOLVER_DEPTH:
				_fail("resolver_depth_exceeded", path, "Resolver nesting exceeds the configured limit")

			entry = cls.REGISTRY.get((family, operation))
			if not entry:
				_fail("resolver_not_allowed", path, f"Resolver {family}.{operation} is not registered")

			if consumer == "condition" and not entry.get("condition_operand_allowed"):
				_fail(
					"resolver_not_allowed", path, "Resolver operation is not approved as a condition operand"
				)

			supported = entry.get("supported_consumers", {"all"})
			if consumer and "all" not in supported and consumer not in supported:
				if not (consumer == "condition" and entry.get("condition_operand_allowed")):
					_fail(
						"resolver_consumer_unsupported", path, f"Resolver not allowed for consumer {consumer}"
					)

			config = value.get("config")
			if not isinstance(config, dict):
				_fail("invalid_resolver_config", f"{path}.config", "Resolver config must be an object")

			declared_vt = value.get("value_type")
			if declared_vt and declared_vt not in VALUE_TYPES:
				_fail("unknown_value_type", f"{path}.value_type", "Unknown declared resolver output type")

			entry["validate_config"](
				config, f"{path}.config", allowed, resolver_depth + 1, flexvalue_depth + 1
			)
			return entry["output_type"]

		if mode == "template":
			_exact_keys(value, {"mode", "segments"}, set(), path)
			segments = value.get("segments")
			if not isinstance(segments, list) or not segments or len(segments) > MAX_TEMPLATE_SEGMENTS:
				_fail(
					"invalid_template_segments",
					f"{path}.segments",
					"Template segments must be a non-empty bounded list",
				)
			for index, segment in enumerate(segments):
				segment_path = f"{path}.segments[{index}]"
				if not isinstance(segment, Mapping):
					_fail("invalid_template_segment", segment_path, "Template segment must be an object")
				if segment.get("type") == "text":
					_exact_keys(segment, {"type", "value"}, set(), segment_path)
					if not isinstance(segment.get("value"), str):
						_fail(
							"invalid_template_text",
							f"{segment_path}.value",
							"Text segment value must be a string",
						)
				elif segment.get("type") == "value":
					_exact_keys(segment, {"type", "value"}, set(), segment_path)
					output_type = cls.validate_flex_value(
						segment.get("value"),
						path=f"{segment_path}.value",
						allowed_scopes=allowed,
						consumer=consumer,
						resolver_depth=resolver_depth,
						flexvalue_depth=flexvalue_depth + 1,
					)
					if output_type in {"list", "object", "Table", "Table MultiSelect"}:
						_fail(
							"invalid_template_value_type",
							f"{segment_path}.value",
							"Template values must be scalar",
						)
				else:
					_fail(
						"unknown_template_segment", f"{segment_path}.type", "Expected text or value segment"
					)
			return "Data"

		_fail("unknown_flex_value_mode", f"{path}.mode", "Unsupported FlexValue mode")

	@classmethod
	def compile_flex_value(
		cls,
		flex_value: Any,
		*,
		context_metadata: dict[str, Any] | None = None,
		path: str = "$",
		consumer: str | None = None,
	) -> CompiledResolver:
		"""
		Authoritative compilation pipeline for canonical FlexValue.
		Validates structure and compiles once into an immutable CompiledResolver.
		"""
		if not isinstance(flex_value, Mapping):
			if flex_value is None:
				return StaticResolver(None)
			return StaticResolver(flex_value)

		mode = flex_value.get("mode")

		# Direct compilation of canonical modes
		if mode == "static":
			cls.validate_flex_value(flex_value, path=path, consumer=consumer)
			value_type = flex_value.get("value_type", "Data")
			parsed = parse_static_value(value_type, flex_value.get("value"))
			return StaticResolver(parsed)

		if mode == "variable":
			cls.validate_flex_value(flex_value, path=path, consumer=consumer)
			path_val = flex_value.get("path", {})
			scope = path_val.get("scope")
			segments = tuple(path_val.get("segments") or ())
			return CanonicalVariableResolver(scope, segments)

		if mode == "resolver":
			cls.validate_flex_value(flex_value, path=path, consumer=consumer)
			family = flex_value["family"]
			operation = flex_value["operation"]
			config = flex_value.get("config", {})
			entry = cls.REGISTRY[(family, operation)]
			return entry["factory"](config, context_metadata)

		if mode == "template":
			cls.validate_flex_value(flex_value, path=path, consumer=consumer)
			compiled_segments: list[tuple[str, Any]] = []
			for idx, segment in enumerate(flex_value.get("segments", [])):
				seg_type = segment.get("type")
				if seg_type == "text":
					compiled_segments.append(("text", segment.get("value", "")))
				else:
					child_compiled = cls.compile_flex_value(
						segment.get("value"),
						context_metadata=context_metadata,
						path=f"{path}.segments[{idx}].value",
						consumer=consumer,
					)
					compiled_segments.append(("value", child_compiled))
			return CanonicalTemplateResolver(tuple(compiled_segments))

		# Strict canonical compilation: unknown modes or structures fail directly
		_fail("unknown_flex_value_mode", f"{path}.mode", f"Unsupported FlexValue mode: {mode}")

	@staticmethod
	def compile(val: Any) -> CompiledResolver:
		"""Legacy compile entrypoint preserved for backward compatibility during migration."""
		if val is None:
			return NoneResolver()

		if isinstance(val, dict):
			mode = val.get("mode")

			if mode in ("static", "link", "dynamic_link"):
				return StaticResolver(val.get("value"))

			if mode == "variable":
				path = val.get("path")
				if isinstance(path, dict) and "scope" in path:
					return CanonicalVariableResolver(path["scope"], tuple(path.get("segments", ())))
				path_str = val.get("path") or val.get("value") or ""
				return VariableResolver(path_str)

			if mode == "resolver":
				family = val.get("family")
				operation = val.get("operation")
				config = val.get("config")
				if isinstance(config, dict):
					inner_family = family or config.get("family") or config.get("kind")
					inner_op = operation or config.get("operation") or config.get("agg_op")
					merged = {**config}
					if inner_family:
						merged["family"] = inner_family
					if inner_op:
						merged["operation"] = inner_op
					return ValueResolver.compile_resolver_config(merged)
				if family and operation and (family, operation) in ValueResolver.REGISTRY:
					return ValueResolver.REGISTRY[(family, operation)]["factory"](val, None)
				return ValueResolver.compile_resolver_config(val)

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
				mode in ("formatter", "normalize", "format", "normalization")
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
			if any(
				val.startswith(p)
				for p in ("doc.", "vars.", "item.", "row.", "loop.", "caller.", "rule.", "ctx.")
			):
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
		operation = config.get("operation") or inner_dict.get("operation")
		kind = config.get("kind") or inner_dict.get("kind")

		# Check if registered in unified REGISTRY
		if family and operation and (family, operation) in ValueResolver.REGISTRY:
			cfg = inner_dict if raw_inner else config
			return ValueResolver.REGISTRY[(family, operation)]["factory"](cfg, None)

		if family == "collection" or kind == "collection":
			source = inner_dict.get("source") or config.get("source")
			op = inner_dict.get("operation") or config.get("operation") or "any"
			condition = inner_dict.get("condition") if "condition" in inner_dict else config.get("condition")
			target_field = inner_dict.get("target_field") or config.get("target_field")
			return CollectionResolver(
				source=source,
				operation=op,
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
			op = (
				inner_dict.get("operation")
				or inner_dict.get("agg_op")
				or config.get("agg_op")
				or config.get("operation")
				or "sum"
			)
			condition = inner_dict.get("condition") if "condition" in inner_dict else config.get("condition")
			return CollectionResolver(
				source=source,
				operation=op,
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
					diff_start_type=inner_dict.get("diff_start_type") or config.get("diff_start_type"),
					diff_start_field=inner_dict.get("diff_start_field") or config.get("diff_start_field"),
					diff_end_type=inner_dict.get("diff_end_type") or config.get("diff_end_type"),
					diff_end_field=inner_dict.get("diff_end_field") or config.get("diff_end_field"),
					diff_unit=inner_dict.get("diff_unit") or config.get("diff_unit", "days"),
					start_source=inner_dict.get("start_source")
					if "start_source" in inner_dict
					else config.get("start_source"),
					end_source=inner_dict.get("end_source")
					if "end_source" in inner_dict
					else config.get("end_source"),
				)
			if op == "extract":
				return DateExtractResolver(
					source=inner_dict.get("source")
					if "source" in inner_dict
					else (config.get("source") or inner_dict.get("base_field") or config.get("base_field")),
					component=inner_dict.get("component") or config.get("component", "year"),
				)
			if op == "boundary":
				return DateBoundaryResolver(
					source=inner_dict.get("source")
					if "source" in inner_dict
					else (config.get("source") or inner_dict.get("base_field") or config.get("base_field")),
					boundary_type=inner_dict.get("boundary_type")
					or config.get("boundary_type", "start_of_month"),
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


class CanonicalVariableResolver(CompiledResolver):
	"""Fast, structured variable resolution without dot-string parsing at runtime."""

	__slots__ = ("scope", "segments")

	def __init__(self, scope: str, segments: tuple[str, ...]):
		self.scope = scope
		self.segments = segments

	def resolve(self, context: dict) -> Any:
		return resolve_variable(self.scope, self.segments, context)


class CanonicalTemplateResolver(CompiledResolver):
	"""Fast template resolver concatenating pre-compiled text and scalar values."""

	__slots__ = ("segments",)

	def __init__(self, segments: tuple[tuple[str, Any], ...]):
		self.segments = segments

	def resolve(self, context: dict) -> str:
		parts: list[str] = []
		output_length = 0
		for seg_type, seg_val in self.segments:
			if seg_type == "text":
				parts.append(seg_val)
				output_length += len(seg_val)
			else:
				resolved = seg_val.resolve(context)
				if resolved is MISSING or resolved is None:
					part = ""
				else:
					part = format_template_value(resolved)
				parts.append(part)
				output_length += len(part)

			if output_length > MAX_TEMPLATE_OUTPUT_CHARS:
				raise ConditionEvaluationError(
					"template_output_too_large",
					"$",
					"Resolved template exceeds the configured output limit",
				)
		return "".join(parts)


def get_compiled_resolver(action, key: str, value_payload: Any) -> CompiledResolver:
	"""
	Retrieve or create a request-local compiled ValueResolver object for extreme execution efficiency.
	Accounts for action, key, and registry fingerprint.
	"""
	if not hasattr(frappe.local, "flexirule_compiled_resolvers"):
		frappe.local.flexirule_compiled_resolvers = {}

	action_name = getattr(action, "name", "action") or "action"
	fp = ValueResolver.registry_fingerprint()
	cache_key = f"{action_name}_{key}_{fp}"

	if cache_key not in frappe.local.flexirule_compiled_resolvers:
		if isinstance(value_payload, dict) and "mode" in value_payload:
			mode = value_payload.get("mode")
			is_canonical = (
				(mode == "static" and "value_type" in value_payload)
				or (mode == "variable" and isinstance(value_payload.get("path"), dict))
				or (mode == "resolver" and "family" in value_payload and "operation" in value_payload)
				or (mode == "template" and "segments" in value_payload)
			)
			if is_canonical:
				# Strict canonical compilation without fallback
				frappe.local.flexirule_compiled_resolvers[cache_key] = ValueResolver.compile_flex_value(
					value_payload
				)
			else:
				# Explicit legacy payload conversion
				frappe.local.flexirule_compiled_resolvers[cache_key] = ValueResolver.compile(value_payload)
		else:
			frappe.local.flexirule_compiled_resolvers[cache_key] = ValueResolver.compile(value_payload)

	return frappe.local.flexirule_compiled_resolvers[cache_key]


def _register_builtins():
	# Concrete operation-specific config validators

	def _validate_path_str(p_val: Any, field_name: str, path: str, allowed_scopes: set[str]):
		if not isinstance(p_val, str) or not p_val.strip():
			_fail(
				"invalid_field_path",
				f"{path}.{field_name}",
				f"Field {field_name} must be a non-empty string path",
			)
		parts = p_val.strip().split(".")
		scope = parts[0]
		if scope not in allowed_scopes:
			_fail("unknown_scope", f"{path}.{field_name}", f"Scope '{scope}' is not allowed in {field_name}")
		for seg in parts[1:]:
			if not seg or not re.fullmatch(r"[A-Za-z0-9_]+", seg) or "__" in seg:
				_fail(
					"invalid_path_segment",
					f"{path}.{field_name}",
					f"Invalid path segment in {field_name}: '{seg}'",
				)

	# date_time.current
	def _val_dt_current(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"token"}, path)
		token = cfg.get("token", "date")
		if token is not None and token not in {"date", "datetime", "now", "time"}:
			_fail("invalid_token", f"{path}.token", f"Unsupported token for date_time.current: {token}")

	ValueResolver.register_resolver(
		"date_time",
		"current",
		label="Current Date/Time",
		output_type="Date",
		config_schema={"type": "object", "properties": {"token": {"type": "string"}}},
		permission_policy="no_data_access",
		validate_config=_val_dt_current,
		factory=lambda cfg, meta: DateCurrentResolver(cfg.get("token") or "date"),
		condition_operand_allowed=True,
	)

	# date_time.calculate
	def _val_dt_calculate(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(
			cfg,
			set(),
			{"base_type", "base_field", "offset_value", "offset_unit", "offset_sign", "source"},
			path,
		)
		if "base_type" in cfg and cfg["base_type"] not in {
			"today",
			"current_date",
			"current_datetime",
			"now",
			"current_time",
			"doc_field",
			None,
		}:
			_fail("invalid_base_type", f"{path}.base_type", f"Invalid base_type: {cfg['base_type']}")
		if "offset_unit" in cfg and cfg["offset_unit"] not in {
			"days",
			"months",
			"years",
			"hours",
			"minutes",
			"seconds",
			None,
		}:
			_fail("invalid_offset_unit", f"{path}.offset_unit", f"Invalid offset_unit: {cfg['offset_unit']}")
		if "offset_sign" in cfg and cfg["offset_sign"] not in {"+", "-", None}:
			_fail("invalid_offset_sign", f"{path}.offset_sign", f"Invalid offset_sign: {cfg['offset_sign']}")
		if "source" in cfg and cfg["source"] is not None:
			if isinstance(cfg["source"], dict) and "mode" in cfg["source"]:
				ValueResolver.validate_flex_value(
					cfg["source"],
					path=f"{path}.source",
					allowed_scopes=allowed_scopes,
					resolver_depth=r_depth,
					flexvalue_depth=fv_depth,
				)
			elif isinstance(cfg["source"], str):
				_validate_path_str(cfg["source"], "source", path, allowed_scopes)
		if "offset_value" in cfg and cfg["offset_value"] is not None:
			if isinstance(cfg["offset_value"], dict) and "mode" in cfg["offset_value"]:
				ValueResolver.validate_flex_value(
					cfg["offset_value"],
					path=f"{path}.offset_value",
					allowed_scopes=allowed_scopes,
					resolver_depth=r_depth,
					flexvalue_depth=fv_depth,
				)
			elif not isinstance(cfg["offset_value"], int | float | str):
				_fail(
					"invalid_offset_value",
					f"{path}.offset_value",
					"Offset value must be numeric, string, or FlexValue",
				)

	ValueResolver.register_resolver(
		"date_time",
		"calculate",
		label="Calculate Date/Time",
		output_type="Date",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_dt_calculate,
		factory=lambda cfg, meta: DateFormulaResolver(
			base_type=cfg.get("base_type"),
			base_field=cfg.get("base_field"),
			offset_value=cfg.get("offset_value", 0),
			offset_unit=cfg.get("offset_unit", "days"),
			offset_sign=cfg.get("offset_sign", "+"),
			source=cfg.get("source"),
		),
		condition_operand_allowed=True,
	)

	# date_time.diff
	def _val_dt_diff(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(
			cfg,
			set(),
			{
				"diff_start_type",
				"diff_start_field",
				"diff_end_type",
				"diff_end_field",
				"diff_unit",
				"start_source",
				"end_source",
			},
			path,
		)
		if "diff_unit" in cfg and cfg["diff_unit"] not in {
			"days",
			"months",
			"years",
			"hours",
			"minutes",
			"seconds",
			None,
		}:
			_fail("invalid_diff_unit", f"{path}.diff_unit", f"Invalid diff_unit: {cfg['diff_unit']}")
		for src_key in ("start_source", "end_source"):
			if src_key in cfg and cfg[src_key] is not None:
				if isinstance(cfg[src_key], dict) and "mode" in cfg[src_key]:
					ValueResolver.validate_flex_value(
						cfg[src_key],
						path=f"{path}.{src_key}",
						allowed_scopes=allowed_scopes,
						resolver_depth=r_depth,
						flexvalue_depth=fv_depth,
					)
				elif isinstance(cfg[src_key], str):
					_validate_path_str(cfg[src_key], src_key, path, allowed_scopes)

	ValueResolver.register_resolver(
		"date_time",
		"diff",
		label="Date Difference",
		output_type="Int",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_dt_diff,
		factory=lambda cfg, meta: DateDiffResolver(
			diff_start_type=cfg.get("diff_start_type"),
			diff_start_field=cfg.get("diff_start_field"),
			diff_end_type=cfg.get("diff_end_type"),
			diff_end_field=cfg.get("diff_end_field"),
			diff_unit=cfg.get("diff_unit", "days"),
			start_source=cfg.get("start_source"),
			end_source=cfg.get("end_source"),
		),
		condition_operand_allowed=True,
	)

	# date_time.extract
	def _val_dt_extract(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"source", "base_field", "component"}, path)
		if "component" in cfg and cfg["component"] not in {
			"year",
			"month",
			"day",
			"weekday",
			"quarter",
			"hour",
			"minute",
			"second",
			None,
		}:
			_fail("invalid_component", f"{path}.component", f"Invalid extract component: {cfg['component']}")
		for src_key in ("source", "base_field"):
			if src_key in cfg and cfg[src_key] is not None:
				if isinstance(cfg[src_key], dict) and "mode" in cfg[src_key]:
					ValueResolver.validate_flex_value(
						cfg[src_key],
						path=f"{path}.{src_key}",
						allowed_scopes=allowed_scopes,
						resolver_depth=r_depth,
						flexvalue_depth=fv_depth,
					)
				elif isinstance(cfg[src_key], str):
					_validate_path_str(cfg[src_key], src_key, path, allowed_scopes)

	ValueResolver.register_resolver(
		"date_time",
		"extract",
		label="Extract Date Component",
		output_type="Int",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_dt_extract,
		factory=lambda cfg, meta: DateExtractResolver(
			source=cfg.get("source") or cfg.get("base_field"),
			component=cfg.get("component", "year"),
		),
		condition_operand_allowed=True,
	)

	# date_time.boundary
	def _val_dt_boundary(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"source", "base_field", "boundary_type"}, path)
		allowed_btypes = {
			"start_of_day",
			"end_of_day",
			"start_of_week",
			"end_of_week",
			"start_of_month",
			"end_of_month",
			"start_of_quarter",
			"end_of_quarter",
			"start_of_year",
			"end_of_year",
			None,
		}
		if "boundary_type" in cfg and cfg["boundary_type"] not in allowed_btypes:
			_fail(
				"invalid_boundary_type",
				f"{path}.boundary_type",
				f"Invalid boundary_type: {cfg['boundary_type']}",
			)
		for src_key in ("source", "base_field"):
			if src_key in cfg and cfg[src_key] is not None:
				if isinstance(cfg[src_key], dict) and "mode" in cfg[src_key]:
					ValueResolver.validate_flex_value(
						cfg[src_key],
						path=f"{path}.{src_key}",
						allowed_scopes=allowed_scopes,
						resolver_depth=r_depth,
						flexvalue_depth=fv_depth,
					)
				elif isinstance(cfg[src_key], str):
					_validate_path_str(cfg[src_key], src_key, path, allowed_scopes)

	ValueResolver.register_resolver(
		"date_time",
		"boundary",
		label="Date Boundary",
		output_type="Date",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_dt_boundary,
		factory=lambda cfg, meta: DateBoundaryResolver(
			source=cfg.get("source") or cfg.get("base_field"),
			boundary_type=cfg.get("boundary_type", "start_of_month"),
		),
		condition_operand_allowed=True,
	)

	# date_time.format
	def _val_dt_format(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"fmt_field", "fmt_config", "source"}, path)
		if "fmt_field" in cfg and cfg["fmt_field"] is not None:
			_validate_path_str(str(cfg["fmt_field"]), "fmt_field", path, allowed_scopes)
		if "fmt_config" in cfg and cfg["fmt_config"] is not None and not isinstance(cfg["fmt_config"], str):
			_fail("invalid_fmt_config", f"{path}.fmt_config", "Format configuration must be a string")

	ValueResolver.register_resolver(
		"date_time",
		"format",
		label="Format Date",
		output_type="Data",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_dt_format,
		factory=lambda cfg, meta: FormatResolver(
			fmt_op="format_date",
			fmt_field=cfg.get("fmt_field"),
			fmt_config=cfg.get("fmt_config", "YYYY-MM-DD"),
		),
		condition_operand_allowed=True,
	)

	# math.formula
	def _val_math_formula(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(
			cfg, set(), {"field_a", "math_op", "field_b_type", "field_b", "constant_b", "precision"}, path
		)
		if "math_op" in cfg and cfg["math_op"] not in {"+", "-", "*", "/", None}:
			_fail("invalid_math_op", f"{path}.math_op", f"Invalid math_op: {cfg['math_op']}")
		if cfg.get("field_a"):
			_validate_path_str(str(cfg["field_a"]), "field_a", path, allowed_scopes)
		if cfg.get("field_b_type") == "field" and cfg.get("field_b"):
			_validate_path_str(str(cfg["field_b"]), "field_b", path, allowed_scopes)
		if "precision" in cfg and cfg["precision"] is not None:
			if not isinstance(cfg["precision"], int) or cfg["precision"] < 0 or cfg["precision"] > 10:
				_fail(
					"invalid_precision", f"{path}.precision", "Precision must be an integer between 0 and 10"
				)

	ValueResolver.register_resolver(
		"math",
		"formula",
		label="Math Formula",
		output_type="Float",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_math_formula,
		factory=lambda cfg, meta: MathFormulaResolver(
			field_a=cfg.get("field_a"),
			math_op=cfg.get("math_op", "+"),
			field_b_type=cfg.get("field_b_type", "field"),
			field_b=cfg.get("field_b"),
			constant_b=cfg.get("constant_b", 0),
			precision=cfg.get("precision", 2),
		),
		condition_operand_allowed=True,
	)

	# text.combine
	def _val_text_combine(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"str_op", "str_a_type", "str_a", "str_b_type", "str_b"}, path)
		if cfg.get("str_a_type") == "field" and cfg.get("str_a"):
			_validate_path_str(str(cfg["str_a"]), "str_a", path, allowed_scopes)
		if cfg.get("str_b_type") == "field" and cfg.get("str_b"):
			_validate_path_str(str(cfg["str_b"]), "str_b", path, allowed_scopes)

	ValueResolver.register_resolver(
		"text",
		"combine",
		label="Text Combine",
		output_type="Data",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_text_combine,
		factory=lambda cfg, meta: StringFormulaResolver(
			str_op="concat",
			str_a_type=cfg.get("str_a_type", "field"),
			str_a=cfg.get("str_a"),
			str_b_type=cfg.get("str_b_type", "constant"),
			str_b=cfg.get("str_b"),
		),
		condition_operand_allowed=True,
	)

	# text.case
	def _val_text_case(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"case_mode", "field"}, path)
		if "case_mode" in cfg and cfg["case_mode"] not in {
			"uppercase",
			"lowercase",
			"titlecase",
			"upper",
			"lower",
			None,
		}:
			_fail("invalid_case_mode", f"{path}.case_mode", f"Invalid case_mode: {cfg['case_mode']}")
		if cfg.get("field"):
			_validate_path_str(str(cfg["field"]), "field", path, allowed_scopes)

	ValueResolver.register_resolver(
		"text",
		"case",
		label="Text Case",
		output_type="Data",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_text_case,
		factory=lambda cfg, meta: StringFormulaResolver(
			str_op=cfg.get("case_mode", "uppercase"),
			str_a_type="field",
			str_a=cfg.get("field"),
			str_b_type="constant",
			str_b="",
		),
		condition_operand_allowed=True,
	)

	# text.normalize
	def _val_text_normalize(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"norm_field", "norm_profile", "norm_pipeline", "norm_op"}, path)
		if cfg.get("norm_field"):
			_validate_path_str(str(cfg["norm_field"]), "norm_field", path, allowed_scopes)
		if "norm_pipeline" in cfg and cfg["norm_pipeline"] is not None:
			if not isinstance(cfg["norm_pipeline"], list):
				_fail(
					"invalid_norm_pipeline", f"{path}.norm_pipeline", "Normalization pipeline must be a list"
				)

	ValueResolver.register_resolver(
		"text",
		"normalize",
		label="Text Normalize",
		output_type="Data",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_text_normalize,
		factory=lambda cfg, meta: NormalizationResolver(
			norm_field=cfg.get("norm_field"),
			norm_profile=cfg.get("norm_profile"),
			norm_pipeline=cfg.get("norm_pipeline"),
			norm_op=cfg.get("norm_op"),
		),
		condition_operand_allowed=True,
	)

	# text.format
	def _val_text_format(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"fmt_field", "fmt_config"}, path)
		if cfg.get("fmt_field"):
			_validate_path_str(str(cfg["fmt_field"]), "fmt_field", path, allowed_scopes)
		if "fmt_config" in cfg and cfg["fmt_config"] is not None and not isinstance(cfg["fmt_config"], str):
			_fail("invalid_fmt_config", f"{path}.fmt_config", "fmt_config must be a string")

	ValueResolver.register_resolver(
		"text",
		"format",
		label="Text Format",
		output_type="Data",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_text_format,
		factory=lambda cfg, meta: FormatResolver(
			fmt_op="format",
			fmt_field=cfg.get("fmt_field"),
			fmt_config=cfg.get("fmt_config", ""),
		),
		condition_operand_allowed=True,
	)

	# lookup.fetch
	def _val_lookup_fetch(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(
			cfg,
			set(),
			{
				"doctype_mode",
				"target_doctype",
				"linked_doctype",
				"doctype_source",
				"record_field",
				"link_field",
				"fetch_field",
				"record_source_type",
			},
			path,
		)
		mode = cfg.get("doctype_mode", "static")
		if mode not in {"static", "dynamic", None}:
			_fail("invalid_doctype_mode", f"{path}.doctype_mode", f"Invalid doctype_mode: {mode}")
		if mode == "dynamic" and not cfg.get("doctype_source"):
			_fail(
				"missing_doctype_source",
				f"{path}.doctype_source",
				"doctype_source is required for dynamic mode",
			)
		elif mode != "dynamic" and not (cfg.get("target_doctype") or cfg.get("linked_doctype")):
			_fail(
				"missing_target_doctype",
				f"{path}.target_doctype",
				"target_doctype is required for static lookup",
			)
		rec_field = cfg.get("record_field") or cfg.get("link_field")
		if rec_field:
			_validate_path_str(str(rec_field), "record_field", path, allowed_scopes)
		fetch_fld = cfg.get("fetch_field")
		if not fetch_fld or not isinstance(fetch_fld, str):
			_fail("missing_fetch_field", f"{path}.fetch_field", "fetch_field is required")

	ValueResolver.register_resolver(
		"lookup",
		"fetch",
		label="Lookup Record Field",
		output_type="Data",
		config_schema={"type": "object"},
		permission_policy="authorized_read",
		validate_config=_val_lookup_fetch,
		factory=lambda cfg, meta: LookupResolver(
			doctype_mode=cfg.get("doctype_mode", "static"),
			target_doctype=cfg.get("target_doctype") or cfg.get("linked_doctype"),
			doctype_source=cfg.get("doctype_source"),
			record_field=cfg.get("record_field") or cfg.get("link_field"),
			fetch_field=cfg.get("fetch_field"),
		),
		supported_consumers={"assignment", "query_records", "action"},
		condition_operand_allowed=False,
	)

	def _val_collection(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(
			cfg, set(), {"source", "condition", "target_field", "agg_field", "operation", "kind"}, path
		)
		if cfg.get("source"):
			_validate_path_str(str(cfg["source"]), "source", path, allowed_scopes)
		if cfg.get("condition"):
			from flexirule.ruleflow.core.condition_contract import validate_condition_node
			from flexirule.ruleflow.core.condition_payload import detect_canonical_condition_payload

			is_canonical, canonical_node = detect_canonical_condition_payload(cfg["condition"])
			if is_canonical and canonical_node:
				validate_condition_node(canonical_node)

	def _make_col_factory(op_name: str) -> Callable[[dict, Any], CompiledResolver]:
		def _factory(cfg: dict, meta: Any) -> CompiledResolver:
			return CollectionResolver(
				source=cfg.get("source"),
				operation=op_name,
				condition=cfg.get("condition"),
				target_field=cfg.get("target_field") or cfg.get("agg_field"),
			)

		return _factory

	# collection operations
	for col_op in ["any", "all", "count", "sum", "avg", "first", "last", "filter", "pluck", "unique"]:
		out_type = (
			"Float"
			if col_op in ("sum", "avg")
			else ("Int" if col_op == "count" else ("Check" if col_op in ("any", "all") else "Table"))
		)
		ValueResolver.register_resolver(
			"collection",
			col_op,
			label=f"Collection {col_op.capitalize()}",
			output_type=out_type,
			config_schema={"type": "object"},
			permission_policy="no_data_access",
			validate_config=_val_collection,
			factory=_make_col_factory(col_op),
			condition_operand_allowed=True,
		)

	# system_context.get
	def _val_system_context(cfg, path, allowed_scopes, r_depth, fv_depth):
		_exact_keys(cfg, set(), {"sys_token", "sys_role"}, path)
		tok = cfg.get("sys_token", "user")
		if tok not in {"user", "role_check", None}:
			_fail("invalid_sys_token", f"{path}.sys_token", f"Invalid sys_token: {tok}")

	ValueResolver.register_resolver(
		"system_context",
		"get",
		label="System Context",
		output_type="Data",
		config_schema={"type": "object"},
		permission_policy="no_data_access",
		validate_config=_val_system_context,
		factory=lambda cfg, meta: SystemContextResolver(
			sys_token=cfg.get("sys_token", "user"),
			sys_role=cfg.get("sys_role", ""),
		),
		condition_operand_allowed=True,
	)


_register_builtins()
