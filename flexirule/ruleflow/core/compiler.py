import json
from typing import TYPE_CHECKING, Any, ClassVar

import frappe
from frappe import _


class ConditionCompiler:
	"""
	Compiles Standardized JSON conditions into optimized Python expressions.
	Schema:
	- Group: { "op": "and|or", "conditions": [...] }
	- Condition: { "left": Operand, "op": "==", "right": Operand }
	- Collection: { "op": "any|all", "collection": "path", "alias": "x", "where": Group }
	- Operand: { "ref": "scope.path" } | { "value": <literal> }
	"""

	OPERATOR_MAP: ClassVar[dict[str, str]] = {
		"==": "==",
		"!=": "!=",
		">": ">",
		"<": "<",
		">=": ">=",
		"<=": "<=",
		"in": "in",
		"not in": "not in",
		"is": "is",
		"is not": "is not",
		# Logical (Group)
		"and": "and",
		"or": "or",
	}

	# Operator labels for UI display
	OPERATOR_LABELS: ClassVar[dict[str, str]] = {
		"==": "equals",
		"!=": "not equals",
		">": "greater than",
		"<": "less than",
		">=": "greater or equal",
		"<=": "less or equal",
		"in": "in list",
		"not in": "not in list",
		"like": "contains",
		"not like": "not contains",
		"is_set": "is set",
		"is_not_set": "is not set",
		"is_submittable": "is submittable",
		"has_field": "has field",
		"contains": "contains",
		"not_contains": "not contains",
		"is_empty": "is empty",
		"is_not_empty": "is not empty",
		"length_eq": "length equals",
		"length_gt": "length greater than",
		"length_gte": "length greater or equal",
		"length_lt": "length less than",
		"length_lte": "length less or equal",
	}

	# Fieldtype to valid operators mapping
	FIELDTYPE_OPERATORS: ClassVar[dict[str, list[str]]] = {
		# Text fields
		"Data": [
			"==",
			"!=",
			"in",
			"not in",
			"like",
			"not like",
			"is_set",
			"is_not_set",
		],
		"Text": ["==", "!=", "like", "not like", "is_set", "is_not_set"],
		"Small Text": ["==", "!=", "like", "not like", "is_set", "is_not_set"],
		"Long Text": ["==", "!=", "like", "not like", "is_set", "is_not_set"],
		"Text Editor": ["==", "!=", "like", "not like", "is_set", "is_not_set"],
		"Code": ["==", "!=", "like", "not like", "is_set", "is_not_set"],
		"Password": ["is_set", "is_not_set"],
		# Selection fields
		"Select": ["==", "!=", "in", "not in", "is_set", "is_not_set"],
		"Link": ["==", "!=", "in", "not in", "is_set", "is_not_set"],
		"Dynamic Link": ["==", "!=", "in", "not in", "is_set", "is_not_set"],
		# Numeric fields
		"Int": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		"Float": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		"Currency": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		"Percent": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		"Rating": ["==", "!=", ">", "<", ">=", "<="],
		# Boolean
		"Check": ["==", "!="],  # Only 0 or 1
		# Date/Time
		"Date": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		"Datetime": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		"Time": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		"Duration": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
		# Special
		"Attach": ["is_set", "is_not_set"],
		"Attach Image": ["is_set", "is_not_set"],
		"Signature": ["is_set", "is_not_set"],
		"Color": ["==", "!=", "is_set", "is_not_set"],
		"Geolocation": ["is_set", "is_not_set"],
		"JSON": ["is_set", "is_not_set"],
		# Table (not directly comparable)
		"Table": [
			"is_set",
			"is_not_set",
			"is_empty",
			"is_not_empty",
			"length_eq",
			"length_gt",
			"length_gte",
			"length_lt",
			"length_lte",
		],
		"Table MultiSelect": [
			"is_set",
			"is_not_set",
			"is_empty",
			"is_not_empty",
			"length_eq",
			"length_gt",
			"length_gte",
			"length_lt",
			"length_lte",
		],
		# Default fallback
		"_default": ["==", "!=", "is_set", "is_not_set", "is_empty", "is_not_empty"],
	}

	def compile(self, conditions) -> str:
		if not conditions:
			return ""

		if isinstance(conditions, str):
			try:
				conditions = json.loads(conditions)
				# Handle double-encoded JSON (e.g. '"{\\"op\\": ...}"')
				if isinstance(conditions, str):
					try:
						conditions = json.loads(conditions)
					except Exception:
						pass
			except Exception as e:
				raise ValueError(f"Invalid JSON format: {e!s}")

		# Wrap list in AND group (legacy/root support)
		if isinstance(conditions, list):
			conditions = {"op": "and", "conditions": conditions}

		if not isinstance(conditions, dict):
			raise ValueError("Condition must be a dictionary or list")

		return self._compile_node(
			conditions, scopes={"doc", "old_doc", "row", "vars", "item", "caller", "rule", "doctype"}
		)

	def _compile_node(self, node, scopes=None):
		if not isinstance(node, dict):
			return ""

		if scopes is None:
			scopes = {"doc", "old_doc", "row", "vars", "item", "caller", "rule", "doctype"}

		# 1. Detect Type
		# Collection
		if "collection" in node and "where" in node:
			return self._compile_collection(node, scopes)

		# Group (has 'conditions' list)
		if "conditions" in node and isinstance(node["conditions"], list):
			return self._compile_group(node, scopes)

		# Condition (has 'left')
		if "left" in node:
			return self._compile_condition(node, scopes)

		# Fallback/Empty
		return ""

	def _compile_group(self, node, scopes):
		subs = node.get("conditions", [])
		if not subs:
			return ""

		default_op = node.get("op", node.get("logical_operator", "and")).lower()
		if default_op not in ["and", "or"]:
			default_op = "and"

		result_parts: list[str] = []
		for i, sub in enumerate(subs):
			compiled_sub = self._compile_node(sub, scopes)
			if not compiled_sub:
				continue

			if not result_parts:
				# First node, just add it
				result_parts.append(compiled_sub)
			else:
				# Subsequent nodes, get operator from PREVIOUS node for joining
				# Actually, standard behavior is that the item itself says how it joins with the previous one,
				# or the previous one says how it joins with the next.
				# In flexirule, we use condition.get('logical_operator') to join with the NEXT.
				# So we look at the operator of the previous node.
				prev_node = subs[i - 1]
				op = prev_node.get("logical_operator", default_op).lower()
				if op not in ["and", "or"]:
					op = default_op

				result_parts.extend([" ", op, " ", compiled_sub])

		if not result_parts:
			return ""

		return f"({''.join(result_parts)})"

	def _compile_condition(self, node, scopes):
		left = node.get("left")
		right = node.get("right")
		op = node.get("op", "==")

		lhs_code = self._compile_operand(left, scopes)

		# Special Unary/Method Operators
		if op == "is_set":
			return f"({lhs_code} is not None and {lhs_code} != '')"
		if op == "is_not_set":
			return f"({lhs_code} is None or {lhs_code} == '')"
		if op == "is_empty":
			return f"is_empty_value({lhs_code})"
		if op == "is_not_empty":
			return f"(not is_empty_value({lhs_code}))"
		if op == "is_submittable":
			return f"is_submittable({lhs_code})"
		if op == "has_field":
			rhs_code = self._compile_operand(right, scopes)
			return f"has_field({lhs_code}, {rhs_code})"
		if op == "has_changed":
			# DEPRECATED: has_changed in conditions is architecturally incorrect.
			# Change detection should use the 'On Field Change' Process instead.
			# This operator is kept for backward compatibility but always returns True.
			# Existing rules using this should be migrated.
			import warnings

			warnings.warn(
				"has_changed condition operator is deprecated. Use 'On Field Change' Process instead.",
				DeprecationWarning,
				stacklevel=2,
			)
			return "True"  # Always pass - migration required

		rhs_code = self._compile_operand(right, scopes)
		py_op = self.OPERATOR_MAP.get(op, "==")

		# Link/Dynamic Link Tuple Handling
		# _compile_operand returns repr(list) for our tuples, so it looks like "['DocType', 'Value']"
		# We need to distinguish between ['DocType', 'Value'] and ['Val1', 'Val2']
		if (
			isinstance(right.get("value"), list | tuple)
			and len(right.get("value")) == 2
			and isinstance(right.get("value")[0], str)
		):
			val = right.get("value")
			is_link_tuple = False
			if op in ["==", "!="]:
				is_link_tuple = True
			elif op in ["in", "not in", "not_in"] and isinstance(val[1], list | tuple):
				is_link_tuple = True

			if is_link_tuple:
				return f"check_link_match({lhs_code}, {rhs_code}, '{op}')"

		# Contains/Not Contains logic
		if op == "contains":
			return f"({rhs_code} in str({lhs_code}) if {lhs_code} else False)"
		if op == "not_contains":
			return f"({rhs_code} not in str({lhs_code}) if {lhs_code} else True)"
		if op in {"length_eq", "length_gt", "length_gte", "length_lt", "length_lte"}:
			length_operator_map = {
				"length_eq": "==",
				"length_gt": ">",
				"length_gte": ">=",
				"length_lt": "<",
				"length_lte": "<=",
			}
			return f"(length_of({lhs_code}) {length_operator_map[op]} {rhs_code})"

		return f"{lhs_code} {py_op} {rhs_code}"

	def _compile_collection(self, node, scopes):
		# { "op": "any", "collection": "doc.items", "alias": "item", "where": {...} }
		collection_ref = node.get("collection")  # "doc.items"
		op = node.get("op", "any")  # any | all | none
		alias = node.get("alias", "row")
		where = node.get("where")

		# Validate collection reference is not empty
		if not collection_ref or not collection_ref.strip():
			raise ValueError("Collection condition requires a valid collection reference (e.g., 'doc.items')")

		iterator = self._resolve_ref(collection_ref, scopes)

		# Validate iterator is not empty (would produce invalid expression)
		if not iterator or iterator == "''":
			raise ValueError(
				f"Invalid collection reference: '{collection_ref}'. Must be a valid path like 'doc.items'"
			)

		# Push alias to active scopes
		new_scopes = scopes.copy()
		new_scopes.add(alias)

		condition_code = self._compile_node(where, new_scopes) or "True"

		func = "any"
		prefix = ""
		if op == "all":
			func = "all"
		if op == "none":
			func = "any"
			prefix = "not "

		# Expression: any(condition for alias in collection)
		return f"{prefix}{func}({condition_code} for {alias} in ({iterator} or []))"

	def validate(self, expression: str) -> tuple:
		"""
		Validate a compiled expression is syntactically valid and safe.
		Returns (is_valid, error_message)
		"""
		if not expression or expression.strip() == "":
			return True, None

		# Check for obviously invalid patterns
		invalid_patterns = [
			("('' or [])", "Empty collection reference detected"),
			("resolve(, ", "Invalid resolve() call with empty scope"),
			(".get('')", "Empty field name in get()"),
		]

		for pattern, error in invalid_patterns:
			if pattern in expression:
				return False, error

		# Try to compile as Python AST
		try:
			import ast

			ast.parse(expression, mode="eval")

			from flexirule.ruleflow.core.permissions import validate_safe_eval

			frappe.flags.in_validate_safe_eval = True
			try:
				if not validate_safe_eval(expression):
					return False, "Expression contains forbidden pattern"
			finally:
				frappe.flags.in_validate_safe_eval = False

		except SyntaxError as e:
			return False, f"Invalid Python syntax: {e}"

		return True, None

	def _compile_operand(self, operand, scopes):
		# { "ref": "doc.status" } or { "value": "x" }
		if not isinstance(operand, dict):
			return "''"

		if "ref" in operand:
			return self._resolve_ref(operand["ref"], scopes)

		if "value" in operand:
			val = operand["value"]
			# Frappe-compatible output: None -> '', False -> 0, True -> 1
			if val is None:
				return "''"
			if val is True:
				return "1"
			if val is False:
				return "0"

			# Handle Link Tuples (List/Tuple)
			if isinstance(val, list | tuple):
				return repr(val)

			# For strings use repr, for numbers use direct
			if isinstance(val, str):
				return repr(val)
			return repr(val)

		return "''"

	def _resolve_ref(self, path, scopes):
		"""
		Resolve field reference to a Python expression compatible with frappe.safe_eval.

		Simple paths (doc.field) -> direct attribute access: doc.get('field')
		Nested paths (doc.child.field) -> resolve() function for child table traversal
		"""
		if not path:
			return "''"

		parts = path.split(".")
		scope = parts[0]  # doc, old_doc, row, vars, item or collection alias

		if scope not in scopes:
			return "''"

		if len(parts) == 1:
			# Just the scope itself (rare but valid)
			return scope

		if len(parts) == 2:
			# Simple field access: doc.field_name -> doc.get('fieldname')
			# This is directly compatible with frappe.safe_eval
			fieldname = parts[1]
			return f"{scope}.get('{fieldname}')"

		# Nested path (child table or deep reference): use resolve() helper
		# resolve() is injected into safe_eval context by engine/coordinator
		subpath = ".".join(parts[1:])
		return f"resolve({scope}, '{subpath}')"
