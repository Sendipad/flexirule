# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
ConditionEvaluator - Evaluates JSON-based rule conditions
Supports nested AND/OR logic, field comparisons, and various operators
"""

import json
import re
from collections.abc import Mapping
from typing import Any, ClassVar

import frappe
from frappe import _

from flexirule.ruleflow.core.condition_operators import (
	SUPPORTED_OPERATOR_TOKENS,
	compare_values,
	normalize_operator,
)


class ConditionEvaluator:
	"""Evaluates rule conditions against a document"""

	# Temporary compatibility path for previously saved regex predicates. The
	# canonical compiled-condition contract rejects regex until its resource policy
	# is defined and a saved-rule inventory/migration has been completed.
	_LEGACY_OPERATORS: ClassVar[dict[str, Any]] = {
		"regex": lambda left, right: bool(re.search(right, str(left))) if left and right else False,
	}

	def __init__(self, conditions_json: Any, *, strict: bool = False):
		"""Initialize from a saved JSON string or an already-parsed condition tree.

		Strict mode is for persisted Rule/Condition runtime boundaries: malformed
		configuration is reported as a translated Frappe ValidationError rather
		than being treated as a condition that happened to be false.
		"""
		self.strict = strict
		self.conditions: Any
		if isinstance(conditions_json, str):
			if not conditions_json:
				self.conditions = []
			else:
				try:
					self.conditions = json.loads(conditions_json)
				except ValueError as exc:
					if strict:
						frappe.throw(
							_("Condition configuration must be valid JSON: {0}").format(str(exc)),
							frappe.ValidationError,
						)
					self.conditions = []
		elif isinstance(conditions_json, Mapping):
			self.conditions = dict(conditions_json)
		elif isinstance(conditions_json, list):
			self.conditions = list(conditions_json)
		elif conditions_json is None:
			self.conditions = []
		else:
			if strict:
				frappe.throw(
					_("Condition configuration must be a condition object or array."),
					frappe.ValidationError,
				)
			self.conditions = []

	def evaluate(self, doc=None, row=None, context: dict | None = None) -> bool:
		"""Evaluate conditions against a document and the supplied Rule context."""
		eval_context = dict(context or {})
		if doc is not None or "doc" not in eval_context:
			eval_context["doc"] = doc
		doc = eval_context.get("doc")
		if row is not None or "row" not in eval_context:
			eval_context["row"] = row
		row = eval_context.get("row")
		eval_context.setdefault("vars", {})

		if not eval_context.get("old_doc") and doc is not None:
			old_doc = getattr(doc, "_doc_before_save", None)
			if old_doc is None and hasattr(doc, "get_doc_before_save"):
				try:
					old_doc = doc.get_doc_before_save()
				except Exception:
					old_doc = None
			eval_context["old_doc"] = old_doc

		if self.strict:
			from flexirule.ruleflow.core.condition_schema import validate_condition_tree

			try:
				tree = validate_condition_tree(self.conditions)
			except ValueError as exc:
				frappe.throw(
					_("Invalid condition configuration: {0}").format(str(exc)),
					frappe.ValidationError,
				)
			return bool(self._evaluate_node(tree, doc, row, eval_context))

		if not self.conditions:
			return True
		if isinstance(self.conditions, Mapping):
			return bool(self._evaluate_node(self.conditions, doc, row, eval_context))
		return bool(self._evaluate_group(self.conditions, doc, row, context=eval_context))

	def _evaluate_node(self, node: Any, doc, row=None, context: dict | None = None) -> bool:
		"""Evaluate one normalized group, collection, or leaf condition."""
		if isinstance(node, list):
			return self._evaluate_group(node, doc, row, context=context)
		if not isinstance(node, Mapping):
			raise ValueError(_("Condition node must be an object."))
		if "collection" in node or "where" in node:
			return self._evaluate_collection(dict(node), doc, row, context)
		if "conditions" in node:
			return self._evaluate_group(
				node.get("conditions") or [],
				doc,
				row,
				op=node.get("op", node.get("logical_operator", "AND")),
				context=context,
			)
		return self._evaluate_single(dict(node), doc, row, context)

	def _evaluate_group(self, conditions: list, doc, row=None, op="AND", context: dict | None = None) -> bool:
		"""Evaluate sibling conditions left-to-right, honoring each saved join."""
		if not conditions:
			return True

		default_op = str(op or "AND").upper()
		if default_op not in {"AND", "OR"}:
			if self.strict:
				frappe.throw(
					_("Invalid logical condition operator: {0}").format(str(op)),
					frappe.ValidationError,
				)
			default_op = "AND"

		result = True if default_op == "AND" else False
		current_operator = default_op
		for condition in conditions:
			group_result = self._evaluate_node(condition, doc, row, context)
			if current_operator == "AND":
				result = result and group_result
			else:
				result = result or group_result

			raw_next = condition.get("logical_operator", default_op) if isinstance(condition, Mapping) else default_op
			next_operator = str(raw_next or default_op).upper()
			if next_operator not in {"AND", "OR"}:
				if self.strict:
					frappe.throw(
						_("Invalid logical condition operator: {0}").format(str(raw_next)),
						frappe.ValidationError,
					)
				next_operator = default_op
			current_operator = next_operator
		return result

	def _evaluate_collection(self, node: dict, doc, row=None, context: dict | None = None) -> bool:
		"""Evaluate any/all/none over rows using the same context/value resolver."""
		from flexirule.ruleflow.core.value_resolver import get_context_value
		from flexirule.ruleflow.utils.field_resolver import FieldResolver

		collection_path = node.get("collection")
		logic = str(node.get("op", "any")).lower()
		where = node.get("where")
		if not collection_path or not where:
			if self.strict:
				frappe.throw(
					_("Collection conditions require a collection path and a where condition."),
					frappe.ValidationError,
				)
			return True

		context = context or {"doc": doc, "row": row, "vars": {}}
		rows = get_context_value(context, str(collection_path))
		if rows is None and isinstance(collection_path, str):
			path = collection_path.strip()
			if path.startswith("doc."):
				rows = FieldResolver.resolve(doc, path[4:])
			elif "." not in path and path not in context:
				rows = FieldResolver.resolve(doc, path)

		if not isinstance(rows, list):
			return False

		alias = node.get("alias", "row")
		def row_matches(candidate) -> bool:
			row_context = dict(context)
			row_context["row"] = candidate
			row_context[alias] = candidate
			return self._evaluate_node(where, doc, candidate, row_context)

		if logic == "any":
			return any(row_matches(candidate) for candidate in rows)
		if logic == "all":
			return all(row_matches(candidate) for candidate in rows)
		if logic == "none":
			return not any(row_matches(candidate) for candidate in rows)
		if self.strict:
			frappe.throw(
				_("Unsupported collection operation: {0}").format(logic),
				frappe.ValidationError,
			)
		return False

	def _evaluate_single(self, condition: dict, doc, row=None, context: dict | None = None) -> bool:
		"""Resolve operands and compare through the canonical operator registry."""
		context = context or {"doc": doc, "row": row, "vars": {}}
		try:
			left = self._resolve_value(condition.get("left"), doc, row, context)
			raw_operator = condition.get("op", condition.get("operator", "=="))
			if not isinstance(raw_operator, str) or not raw_operator.strip():
				raise ValueError(_("Condition operator must be a non-empty string."))
			op = normalize_operator(raw_operator)

			if op in {"is_set", "is_not_set", "is_empty", "is_not_empty"}:
				return compare_values(left, op)

			right = self._resolve_value(condition.get("right"), doc, row, context)

			if op == "has_field":
				doctype = left if isinstance(left, str) else getattr(left, "doctype", None)
				if not doctype or not isinstance(right, str) or not right:
					raise ValueError(_("has_field requires a DocType and a field name."))
				return bool(frappe.get_meta(doctype).has_field(right))

			if op == "is_submittable":
				doctype = left if isinstance(left, str) else getattr(left, "doctype", None)
				if not doctype:
					raise ValueError(_("is_submittable requires a DocType reference."))
				return bool(frappe.get_meta(doctype).is_submittable)

			if isinstance(right, list | tuple) and len(right) == 2 and isinstance(right[0], str):
				is_link_tuple = op in {"==", "!="}
				if op in {"in", "not in"} and isinstance(right[1], list | tuple):
					is_link_tuple = True
				if is_link_tuple:
					return check_link_match(left, right, op)

			# regex is deliberately kept out of the canonical registry but remains
			# available to legacy CollectionResolver callers pending migration.
			if op == "regex":
				return self._LEGACY_OPERATORS[op](left, right)

			if op in SUPPORTED_OPERATOR_TOKENS:
				return compare_values(left, op, right)

			if self.strict:
				frappe.throw(
					_("Unsupported condition operator: {0}").format(op),
					frappe.ValidationError,
				)
			frappe.log_error(_("Unknown operator: {0}").format(op), _("ConditionEvaluator"))
			return False
		except Exception as exc:
			condition_repr = json.dumps(condition, default=str)[:500]
			message = _("Single condition evaluation failed.\nCondition: {0}\nError: {1}").format(
				condition_repr, str(exc)
			)
			frappe.logger("flexirule.eval").warning(message)
			frappe.log_error(
				title=_("FlexiRule Condition Evaluation Error"),
				message=message,
			)
			if self.strict:
				frappe.throw(
					_("Condition evaluation failed: {0}").format(str(exc)),
					frappe.ValidationError,
				)
			return False

	def _resolve_value(self, value_def: Any, doc, row=None, context: dict | None = None) -> Any:
		"""Resolve a condition operand using shared FlexValue and context APIs."""
		if value_def is None:
			return None
		if not isinstance(value_def, Mapping):
			return value_def

		context = context or {"doc": doc, "row": row, "vars": {}}
		if "ref" in value_def:
			from flexirule.ruleflow.core.value_resolver import get_context_value

			ref_path = value_def.get("ref")
			if not isinstance(ref_path, str) or not ref_path:
				if self.strict:
					frappe.throw(_("Condition reference must be a non-empty path."), frappe.ValidationError)
				return None
			return get_context_value(context, ref_path)

		if "value" in value_def:
			if "type" in value_def:
				value_type = value_def.get("type", "literal")
				value = value_def.get("value")
				if value_type == "field":
					from flexirule.ruleflow.core.value_resolver import get_context_value

					if not value:
						return None
					path = str(value)
					if path.split(".", 1)[0] in context:
						return get_context_value(context, path)
					return get_context_value(context, f"row.{path}" if row is not None else f"doc.{path}")
				if value_type == "literal":
					return value
				if value_type == "method":
					frappe.log_error(
						title=_("FlexiRule Deprecation Warning"),
						message=_("The 'method' value type is no longer supported in conditions. Value: {0}").format(
							str(value)
						),
					)
					return None

			value = value_def.get("value")
			if isinstance(value, Mapping) and any(key in value for key in ("mode", "kind", "family")):
				from flexirule.ruleflow.core.value_resolver import ValueResolver

				return ValueResolver.compile(dict(value)).resolve(context)
			return value

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

	canonical_op = normalize_operator(op)
	if canonical_op not in {"==", "!=", "in", "not in"}:
		return False

	return compare_values(lhs, canonical_op, target_value)


def evaluate_condition(expression: str, context: dict) -> bool:
	"""Evaluate a compiled Python condition expression."""
	from flexirule.ruleflow.core.engine import RuleEngine

	engine = RuleEngine(None)
	return engine._evaluate_python_condition(expression, context)
