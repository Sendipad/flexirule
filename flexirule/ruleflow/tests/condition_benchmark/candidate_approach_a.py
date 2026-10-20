# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import time
from typing import Any, Optional

import frappe
from frappe.utils.safe_exec import WHITELISTED_SAFE_EVAL_GLOBALS, FrappeTransformer
from RestrictedPython import compile_restricted

from flexirule.ruleflow.core.compiler import ConditionCompiler
from flexirule.ruleflow.core.evaluator import check_link_match
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
	EvaluationResult,
	PreparedCondition,
)


def _build_safe_locals(document_context: Any, execution_context: dict | None = None) -> dict:
	"""Construct runtime locals for safe_eval in production rule engine format."""
	locals_dict = {}

	# Document primary context
	doc = document_context
	old_doc = None
	row = None

	if isinstance(document_context, dict) and "doc" in document_context:
		doc = document_context.get("doc")
		old_doc = document_context.get("old_doc")
		row = document_context.get("row")

	locals_dict["doc"] = doc or frappe._dict()
	locals_dict["old_doc"] = old_doc or frappe._dict()
	locals_dict["row"] = row or frappe._dict()
	locals_dict["vars"] = frappe._dict()
	locals_dict["item"] = row or frappe._dict()
	locals_dict["caller"] = frappe._dict()
	locals_dict["rule"] = frappe._dict()
	locals_dict["doctype"] = getattr(doc, "doctype", "") or ""

	if execution_context:
		for k, v in execution_context.items():
			locals_dict[k] = v

	# Global / scope resolution helper for nested child fields
	def resolve(obj, path):
		if not obj or not path:
			return None
		from flexirule.ruleflow.utils.field_resolver import FieldResolver

		return FieldResolver.resolve(obj, path)

	def is_empty_value(val):
		if val is None or val == "":
			return True
		if isinstance(val, str) and not val.strip():
			return True
		if isinstance(val, list | tuple | dict | set) and len(val) == 0:
			return True
		return False

	def is_submittable(val_or_dt):
		if not val_or_dt:
			return False
		dt = getattr(val_or_dt, "doctype", val_or_dt) if not isinstance(val_or_dt, str) else val_or_dt
		meta = frappe.get_meta(dt) if dt else None
		return bool(getattr(meta, "is_submittable", 0))

	def has_field(val_or_dt, fieldname):
		if not val_or_dt or not fieldname:
			return False
		dt = getattr(val_or_dt, "doctype", val_or_dt) if not isinstance(val_or_dt, str) else val_or_dt
		meta = frappe.get_meta(dt) if dt else None
		return bool(meta.has_field(fieldname)) if meta else False

	def length_of(val):
		if val is None:
			return 0
		if isinstance(val, str):
			return len(val.strip())
		if hasattr(val, "__len__"):
			return len(val)
		return 0

	locals_dict["resolve"] = resolve
	locals_dict["is_empty_value"] = is_empty_value
	locals_dict["is_submittable"] = is_submittable
	locals_dict["has_field"] = has_field
	locals_dict["length_of"] = length_of
	locals_dict["check_link_match"] = check_link_match
	locals_dict["any"] = any
	locals_dict["all"] = all
	locals_dict["len"] = len
	locals_dict["str"] = str

	return locals_dict


def _build_eval_globals(safe_locals: dict) -> dict:
	"""Construct eval globals including WHITELISTED_SAFE_EVAL_GLOBALS."""
	eval_globals: dict = {"__builtins__": {}}
	eval_globals.update(safe_locals)
	eval_globals.update(WHITELISTED_SAFE_EVAL_GLOBALS)
	return eval_globals


class ApproachACandidate(BaseConditionCandidate):
	"""Approach A: Precompiled Python expression evaluated via frappe.safe_eval().

	Measures the actual production frappe.safe_eval path using a pre-generated
	expression string. Internal work performed by safe_eval (parsing, syntax check,
	and restricted compilation on each call) remains included in execution timing.
	"""

	candidate_name = "Approach A (frappe.safe_eval)"

	def __init__(self):
		self.compiler = ConditionCompiler()

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		expression = self.compiler.compile(condition_payload)
		prep_time = time.perf_counter() - start_time

		return PreparedCondition(
			candidate_name=self.candidate_name,
			prepared_object=expression,
			preparation_time_seconds=prep_time,
			metadata={"expression_string": expression},
		)

	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		expression = prepared_condition.prepared_object
		if not expression:
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=True,
				execution_time_seconds=0.0,
			)

		safe_locals = _build_safe_locals(document_context, execution_context)
		eval_globals = _build_eval_globals(safe_locals)

		start_time = time.perf_counter()
		try:
			raw_res = frappe.safe_eval(expression, eval_globals, safe_locals)
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(raw_res),
				execution_time_seconds=exec_time,
			)
		except Exception as exc:
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=exec_time,
				error=str(exc),
			)


class ApproachAExperimentalCodeObjectCandidate(BaseConditionCandidate):
	"""Approach A (Experimental Diagnostic): Restricted pre-compiled Python code object.

	Measures evaluating an already-compiled RestrictedPython code object via Python eval().
	This is an isolated experimental diagnostic that demonstrates execution time when
	AST parsing and RestrictedPython compilation overheads are eliminated.
	"""

	candidate_name = "Approach A (Experimental Restricted Code Object)"

	def __init__(self):
		self.compiler = ConditionCompiler()

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		expression = self.compiler.compile(condition_payload)

		code_object = None
		if expression:
			code_object = compile_restricted(
				expression, filename="<safe_eval>", policy=FrappeTransformer, mode="eval"
			)

		prep_time = time.perf_counter() - start_time

		return PreparedCondition(
			candidate_name=self.candidate_name,
			prepared_object=code_object,
			preparation_time_seconds=prep_time,
			metadata={"expression_string": expression, "is_code_object": True},
		)

	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		code_object = prepared_condition.prepared_object
		if code_object is None:
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=True,
				execution_time_seconds=0.0,
			)

		safe_locals = _build_safe_locals(document_context, execution_context)
		eval_globals = _build_eval_globals(safe_locals)

		start_time = time.perf_counter()
		try:
			raw_res = eval(code_object, eval_globals, safe_locals)
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(raw_res),
				execution_time_seconds=exec_time,
			)
		except Exception as exc:
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=exec_time,
				error=str(exc),
			)
