# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
ConditionEvaluator - Evaluates JSON-based rule conditions
Supports nested AND/OR logic, field comparisons, and various operators
"""

import json
import operator
import re
from typing import Any, ClassVar

import frappe
from frappe.utils import cint, flt, getdate


class ConditionEvaluator:
	"""Evaluates rule conditions against a document"""

	# Operator mapping
	OPERATORS: ClassVar[dict[str, Any]] = {
		"==": operator.eq,
		"!=": operator.ne,
		">": operator.gt,
		"<": operator.lt,
		">=": operator.ge,
		"<=": operator.le,
		"in": lambda a, b: a in b if b else False,
		"not_in": lambda a, b: a not in b if b else True,
		"contains": lambda a, b: b in str(a) if a else False,
		"not_contains": lambda a, b: b not in str(a) if a else True,
		"is_set": lambda a, b: a is not None and a != "",
		"is_not_set": lambda a, b: a is None or a == "",
		"regex": lambda a, b: bool(re.search(b, str(a))) if a and b else False,
	}

	def __init__(self, conditions_json: str):
		"""
		Initialize evaluator with conditions JSON

		Args:
		        conditions_json: JSON string containing conditions array
		"""
		self.conditions = json.loads(conditions_json) if conditions_json else []

	def evaluate(self, doc, row=None) -> bool:
		"""
		Evaluate all conditions against a document

		Args:
		        doc: Frappe document
		        row: Current row document (if in collection context)

		Returns:
		        bool: True if all conditions pass
		"""
		if not self.conditions:
			return True

		# Root evaluation always starts with doc as primary context
		return self._evaluate_group(self.conditions, doc, row)

	def _evaluate_group(self, conditions: list, doc, row=None, op="AND") -> bool:
		"""
		Evaluate a group of conditions with AND/OR logic
		"""
		if not conditions:
			return True

		op = op.upper()
		if op not in ["AND", "OR"]:
			op = "AND"

		# Initialize result and operator based on group type
		# For AND group: start with True, join first item with AND
		# For OR group: start with False, join first item with OR
		result = True if op == "AND" else False
		current_operator = op

		for condition in conditions:
			# 1. Detect Type
			if "collection" in condition and "where" in condition:
				# Collection Node
				group_result = self._evaluate_collection(condition, doc, row)
			elif "conditions" in condition:
				# Recursive evaluation for nested groups
				# Pass the explicit 'op' or 'logical_operator' of the nested group
				nested_op = condition.get("op", condition.get("logical_operator", "AND")).upper()
				group_result = self._evaluate_group(condition["conditions"], doc, row, nested_op)
			else:
				# Evaluate single condition
				group_result = self._evaluate_single(condition, doc, row)

			# 2. Apply Logical Operator
			if current_operator == "AND":
				result = result and group_result
			else:  # OR
				result = result or group_result

			# 3. Get next operator
			# Link to the next condition using 'logical_operator' (AND/OR)
			current_operator = condition.get("logical_operator", op).upper()
			if current_operator not in ["AND", "OR"]:
				current_operator = op

		return result

	def _evaluate_collection(self, node: dict, doc, row=None) -> bool:
		"""
		Evaluate collection logic (any/all/none)
		Example: { "op": "any", "collection": "items", "where": { "op": "and", "conditions": [...] } }
		"""
		from flexirule.ruleflow.utils.field_resolver import FieldResolver

		collection_path = node.get("collection")
		logic = node.get("op", "any").lower()
		where = node.get("where")

		if not collection_path or not where:
			return True

		# Resolve collection rows
		rows = FieldResolver.resolve(doc, collection_path)
		if not isinstance(rows, list):
			return False

		if logic == "any":
			return any(self._evaluate_group([where], doc, r) for r in rows)
		elif logic == "all":
			return all(self._evaluate_group([where], doc, r) for r in rows) if rows else True
		elif logic == "none":
			return not any(self._evaluate_group([where], doc, r) for r in rows)

		return False

	def _evaluate_single(self, condition: dict, doc, row=None) -> bool:
		"""
		Evaluate a single condition
		"""
		# DEBUG START
		# print(f"DEBUG_START_SINGLE: {condition}")
		try:
			# Get left value
			left = self._resolve_value(condition.get("left"), doc, row)

			# Get operator
			op = condition.get("op", condition.get("operator", "=="))

			# Special case for operators that don't need right value
			if op in ["is_set", "is_not_set"]:
				return self.OPERATORS[op](left, None)

			# Get right value
			right = self._resolve_value(condition.get("right"), doc, row)

			# Special Handling for Link/Dynamic Link Tuples
			# right might be ["DocType", "Value"] or ["DocType", ["V1", "V2"]]
			if isinstance(right, list | tuple) and len(right) == 2 and isinstance(right[0], str):
				# It is likely a Link Tuple (DocType, Value)

				# Refinement: If op is 'in' or 'not_in', it must have a list as the second element to be a Link Tuple
				# This prevents treating ["Value1", "Value2"] as a Link Tuple for 'in' operator
				is_link_tuple = False
				if op in ["==", "!="]:
					is_link_tuple = True
				elif op in ["in", "not_in", "not in"] and isinstance(right[1], list | tuple):
					is_link_tuple = True

				if is_link_tuple:
					return check_link_match(left, right, op)

			# Get operator function
			op_func = self.OPERATORS.get(op)
			if not op_func:
				# Try with spaces (compiler uses 'not in')
				op_func = self.OPERATORS.get(op.replace(" ", "_"))

			if not op_func:
				frappe.log_error(f"Unknown operator: {op}", "ConditionEvaluator")
				return False

			# Evaluate
			return op_func(left, right)

		except Exception as e:
			condition_repr = json.dumps(condition, default=str)[:500]
			message = f"Single condition evaluation failed.\nCondition: {condition_repr}\nError: {e!s}"
			frappe.logger("flexirule.eval").warning(message)
			frappe.log_error(
				title="FlexiRule Condition Evaluation Error",
				message=message,
			)
			return False

	def _resolve_value(self, value_def: Any, doc, row=None) -> Any:
		"""
		Resolve a value from its definition
		Support new "ref"/"value" structure and older "type"/"value" structure
		"""
		if value_def is None:
			return None

		# If it's a simple scalar, return as-is
		if not isinstance(value_def, dict):
			return value_def

		# 1. New Structure: { "ref": "doc.status" } | { "value": 10 }
		if "ref" in value_def:
			ref_path = value_def["ref"]
			if not ref_path:
				return None

			parts = ref_path.split(".")
			scope = parts[0]
			subpath = ".".join(parts[1:]) if len(parts) > 1 else ""

			if scope == "doc":
				return self._get_field_value(doc, subpath)
			elif scope == "row" and row:
				return self._get_field_value(row, subpath)
			elif scope == "old_doc":
				old_doc = getattr(doc, "_doc_before_save", None) or (
					doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
				)
				return self._get_field_value(old_doc, subpath) if old_doc else None

			# Dynamic alias support: If scope is not doc/old_doc/vars and we have a row,
			# assume it's an alias for the row
			if row:
				if not subpath:
					return row  # Alias itself refers to the row
				return self._get_field_value(row, subpath)

			# Fallback for paths without scope prefix or unknown scopes
			return self._get_field_value(row or doc, ref_path)

		if "value" in value_def and "ref" not in value_def:
			# Detect if this is new {value: x} or old {type: literal, value: x}
			if "type" in value_def:
				value_type = value_def.get("type", "literal")
				value = value_def.get("value")

				if value_type == "field":
					if not value:
						return None
					return self._get_field_value(row or doc, str(value))
				elif value_type == "literal":
					return value
				elif value_type == "method":
					# SECURITY: Removed frappe.call to prevent arbitrary method execution
					# during condition evaluation. This could cause side effects.
					frappe.log_error(
						title="FlexiRule Deprecation Warning",
						message=f"'method' value type is no longer supported in conditions. Value: {value}",
					)
					return None
			else:
				# New {value: x}
				return value_def["value"]

		return None

	def _get_field_value(self, doc, fieldname: str) -> Any:
		"""
		Get field value from document, supports dot notation and aggregates

		Args:
		        doc: Frappe document
		        fieldname: Field name (supports dot notation and aggregates)

		Returns:
		        Field value
		"""
		if not fieldname:
			return None

		# Use FieldResolver for advanced resolution
		from flexirule.ruleflow.utils.field_resolver import FieldResolver

		return FieldResolver.resolve(doc, fieldname)


def check_link_match(lhs, rhs, op="=="):
	"""
	Helper to compare a Link/Dynamic Link field (lhs) with a Tuple value (rhs).
	rhs format: ["DocType", Value] or ["DocType", [Values]]

	Logic:
	1. If LHS is None/Empty, handle based on Op.
	2. Unpack RHS.
	3. Perform standard comparison on values.
	"""
	if not rhs or not isinstance(rhs, list | tuple) or len(rhs) < 2:
		return False

	# rhs format: [DocType, Value] - DocType is included for completeness but not validated here
	target_value = rhs[1]

	# Mapping standard operators
	ops = {
		"==": lambda a, b: a == b,
		"!=": lambda a, b: a != b,
		"in": lambda a, b: a in b if b else False,
		"not in": lambda a, b: a not in b if b else True,
		"not_in": lambda a, b: a not in b if b else True,
	}

	op_func = ops.get(op) or ops.get(op.replace(" ", "_"))

	if not op_func:
		return False

	return op_func(lhs, target_value)


def evaluate_condition(expression: str, context: dict) -> bool:
	"""Evaluate a compiled Python condition expression."""
	from flexirule.ruleflow.core.engine import RuleEngine

	engine = RuleEngine(None)
	return engine._evaluate_python_condition(expression, context)
