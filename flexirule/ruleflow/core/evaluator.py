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

			raw_next = (
				condition.get("logical_operator", default_op)
				if isinstance(condition, Mapping)
				else default_op
			)
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
					metadata_available, link_field, expected_doctype, is_dynamic_link = (
						self._get_link_field_metadata(condition.get("left"), context)
					)
					if link_field is not None:
						return check_link_match(
							left,
							right,
							op,
							expected_doctype,
							validate_doctype=True,
							dynamic_link=is_dynamic_link,
						)
					if not metadata_available:
						# Preserve older typed-link payloads whose LHS has no resolvable
						# DocType metadata, while validating normal DocType fields above.
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
		except frappe.ValidationError:
			raise
		except Exception as exc:
			condition_repr = json.dumps(condition, default=str)[:500]
			message = "\\n".join(
				[
					_("Single condition evaluation failed."),
					_("Condition: {0}").format(condition_repr),
					_("Error: {0}").format(str(exc)),
				]
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
			parts = ref_path.split(".", 1)
			scope = parts[0]
			if len(parts) == 2:
				field_path = parts[1]
				if scope in {"doc", "old_doc", "row", "item", "loop"}:
					return self._get_field_value(context.get(scope), field_path)
				if scope in context and scope not in {"vars", "caller", "rule", "ctx", "doctype"}:
					return self._get_field_value(context.get(scope), field_path)
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
						message=_(
							"The 'method' value type is no longer supported in conditions. Value: {0}"
						).format(str(value)),
					)
					return None

			value = value_def.get("value")
			if isinstance(value, Mapping) and any(key in value for key in ("mode", "kind", "family")):
				from flexirule.ruleflow.core.value_resolver import ValueResolver

				return ValueResolver.compile(dict(value)).resolve(context)
			return value

		return None

	@staticmethod
	def _object_value(target: Any, key: str | None) -> Any:
		"""Read one value from a Frappe document or mapping without coercion."""
		if target is None or not key:
			return None
		if isinstance(target, Mapping):
			return target.get(key)
		getter = getattr(target, "get", None)
		if callable(getter):
			return getter(key)
		return getattr(target, key, None)

	@classmethod
	def _get_link_field_metadata(
		cls, left_definition: Any, context: dict
	) -> tuple[bool, Any, str | None, bool]:
		"""Resolve whether a left-hand field is Link/Dynamic Link and its target DocType.

		Returns (metadata_available, field, target_doctype, is_dynamic_link).
		A Dynamic Link's target DocType comes from its configured reference field
		on the same document/row; it is therefore evaluated per record.
		"""
		if not isinstance(left_definition, Mapping):
			return False, None, None, False
		reference = left_definition.get("ref")
		if not isinstance(reference, str) or "." not in reference:
			return False, None, None, False

		scope, field_path = reference.split(".", 1)
		source = context.get(scope)
		doctype = cls._object_value(source, "doctype")
		if not doctype or not field_path:
			return False, None, None, False

		meta = frappe.get_meta(doctype)
		parts = field_path.split(".")
		field = None
		for index, fieldname in enumerate(parts):
			field = meta.get_field(fieldname)
			if field is None:
				return True, None, None, False
			if index == len(parts) - 1:
				break

			fieldtype = getattr(field, "fieldtype", None)
			options = getattr(field, "options", None)
			if fieldtype in {"Table", "Link"} and options:
				meta = frappe.get_meta(options)
			elif fieldtype == "Dynamic Link" and options:
				nested_doctype = cls._object_value(source, options)
				if not nested_doctype:
					return True, None, None, False
				meta = frappe.get_meta(nested_doctype)
			else:
				return True, None, None, False

		fieldtype = getattr(field, "fieldtype", None)
		if fieldtype == "Link":
			return True, field, getattr(field, "options", None), False
		if fieldtype == "Dynamic Link":
			target_fieldname = getattr(field, "options", None)
			target_doctype = cls._object_value(source, target_fieldname)
			return True, field, target_doctype, True
		return True, None, None, False

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


def check_link_match(
	lhs,
	rhs,
	op="==",
	expected_doctype: str | None = None,
	*,
	validate_doctype: bool = False,
	dynamic_link: bool = False,
):
	"""
	Compare a Link/Dynamic Link value with a typed RHS.

	The typed operand is [target_doctype, value] (or [target_doctype, values]
	for membership). Runtime tree evaluation passes field metadata so fixed Link
	targets are validated. Dynamic Link target types are record data, so a different
	target DocType is a normal non-match rather than a malformed condition. The
	three-argument form remains for compiled legacy conditions without metadata.
	"""
	if not rhs or not isinstance(rhs, list | tuple) or len(rhs) < 2:
		return False

	target_doctype, target_value = rhs[0], rhs[1]
	canonical_op = normalize_operator(op)
	if canonical_op not in {"==", "!=", "in", "not in"}:
		return False

	if validate_doctype:
		if not isinstance(target_doctype, str) or not target_doctype.strip():
			raise ValueError(_("Link comparison requires a target DocType."))
		if dynamic_link and target_doctype != expected_doctype:
			return canonical_op in {"!=", "not in"}
		if not dynamic_link:
			if not expected_doctype:
				raise ValueError(_("Could not determine the target DocType for this Link field."))
			if target_doctype != expected_doctype:
				raise ValueError(
					_("Link operand DocType '{0}' does not match the field target '{1}'.").format(
						target_doctype, expected_doctype
					)
				)

	return compare_values(lhs, canonical_op, target_value)


def evaluate_condition(expression: str, context: dict) -> bool:
	"""Evaluate a compiled Python condition expression."""
	from flexirule.ruleflow.core.engine import RuleEngine

	engine = RuleEngine(None)
	return engine._evaluate_python_condition(expression, context)
