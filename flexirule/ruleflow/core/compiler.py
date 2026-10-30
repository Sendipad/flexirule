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

		from flexirule.ruleflow.core.condition_payload import parse_condition_payload

		parsed = parse_condition_payload(conditions)
		if parsed is None:
			return ""

		if isinstance(parsed, str):
			is_valid, err = self.validate(parsed)
			if not is_valid:
				raise ValueError(f"Invalid condition expression: {err}")
			return parsed

		if isinstance(parsed, list):
			conditions_tree = {"op": "and", "conditions": parsed}
		elif isinstance(parsed, dict):
			conditions_tree = parsed
		else:
			raise ValueError(f"Unsupported condition payload type: {type(conditions).__name__}")

		compiled = self._compile_node(
			conditions_tree, scopes={"doc", "old_doc", "row", "vars", "item", "caller", "rule", "doctype"}
		)
		result = compiled if compiled else "True"
		is_valid, err = self.validate(result)
		if not is_valid:
			raise ValueError(f"Invalid compiled condition expression: {err}")
		return result

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

	LEGACY_VALID_OPERATORS: ClassVar[set[str]] = {
		"==",
		"!=",
		">",
		"<",
		">=",
		"<=",
		"in",
		"not in",
		"not_in",
		"is",
		"is not",
		"and",
		"or",
		"like",
		"not like",
		"is_set",
		"is_not_set",
		"is_submittable",
		"has_field",
		"has_changed",
		"contains",
		"not_contains",
		"is_empty",
		"is_not_empty",
		"length_eq",
		"length_gt",
		"length_gte",
		"length_lt",
		"length_lte",
	}

	UNARY_LEGACY_OPERATORS: ClassVar[set[str]] = {
		"is_set",
		"is_not_set",
		"is_empty",
		"is_not_empty",
		"is_submittable",
		"has_changed",
	}

	def compile_legacy_guard(self, raw_guard: Any, path: str = "$") -> str:
		"""Strictly validate and compile a legacy condition guard into a Python expression.

		Rejects unknown shapes, empty groups, malformed JSON, and unsupported operators/operands.
		Never falls back to 'True' for invalid or dropped conditions.
		"""
		from flexirule.ruleflow.core.condition_errors import ConditionValidationError
		from flexirule.ruleflow.core.condition_payload import parse_condition_payload

		if raw_guard in (None, ""):
			return ""

		try:
			parsed = parse_condition_payload(raw_guard)
		except ConditionValidationError:
			raise
		except Exception as exc:
			raise ConditionValidationError("invalid_json", path, "Structured condition JSON is malformed") from exc

		if parsed in (None, ""):
			return ""

		if isinstance(parsed, str):
			is_valid, err = self.validate(parsed)
			if not is_valid:
				raise ConditionValidationError(
					"invalid_when_expression", path, f"Invalid condition expression: {err}"
				)
			return parsed

		self._validate_legacy_structure(parsed, path)

		compiled = self.compile(parsed)
		if not compiled or compiled.strip() in ("", "True"):
			raise ConditionValidationError(
				"empty_legacy_guard", path, "Legacy condition produced an empty expression"
			)

		is_valid, err = self.validate(compiled)
		if not is_valid:
			raise ConditionValidationError(
				"invalid_compiled_expression", path, f"Invalid compiled condition: {err}"
			)

		return compiled

	def _validate_legacy_structure(self, node: Any, path: str) -> None:
		from flexirule.ruleflow.core.condition_errors import ConditionValidationError

		if isinstance(node, list):
			if not node:
				raise ConditionValidationError(
					"empty_legacy_group", path, "Legacy condition group cannot be empty"
				)
			for index, item in enumerate(node):
				self._validate_legacy_structure(item, f"{path}[{index}]")
			return

		if isinstance(node, dict):
			if "conditions" in node:
				conditions = node.get("conditions")
				if not isinstance(conditions, list) or len(conditions) == 0:
					raise ConditionValidationError(
						"empty_legacy_group", f"{path}.conditions", "Legacy condition group cannot be empty"
					)
				op = node.get("op", node.get("logical_operator", "and"))
				if not isinstance(op, str) or op.lower() not in ("and", "or"):
					raise ConditionValidationError(
						"unknown_group_operator", f"{path}.op", f"Invalid group operator '{op}'"
					)
				for index, item in enumerate(conditions):
					self._validate_legacy_structure(item, f"{path}.conditions[{index}]")
				return

			if "collection" in node:
				if "where" not in node:
					raise ConditionValidationError(
						"missing_key", f"{path}.where", "Collection condition requires 'where' node"
					)
				collection = node.get("collection")
				if not isinstance(collection, str) or not collection.strip():
					raise ConditionValidationError(
						"invalid_collection_source",
						f"{path}.collection",
						"Collection reference must be a non-empty string",
					)
				op = node.get("op", "any")
				if not isinstance(op, str) or op.lower() not in ("any", "all", "none"):
					raise ConditionValidationError(
						"unknown_collection_quantifier", f"{path}.op", f"Invalid collection quantifier '{op}'"
					)
				self._validate_legacy_structure(node["where"], f"{path}.where")
				return

			if "left" in node:
				op = node.get("op", "==")
				if not isinstance(op, str) or op not in self.LEGACY_VALID_OPERATORS:
					raise ConditionValidationError(
						"unknown_operator", f"{path}.op", f"Unknown legacy condition operator '{op}'"
					)
				self._validate_legacy_operand(node.get("left"), f"{path}.left")
				if op not in self.UNARY_LEGACY_OPERATORS:
					if "right" not in node:
						raise ConditionValidationError(
							"missing_operand", f"{path}.right", f"Operator '{op}' requires right operand"
						)
					self._validate_legacy_operand(node.get("right"), f"{path}.right")
				return

			raise ConditionValidationError(
				"unknown_legacy_guard_shape", path, "Unknown or unsupported legacy condition shape"
			)

		if isinstance(node, str):
			is_valid, err = self.validate(node)
			if not is_valid:
				raise ConditionValidationError(
					"invalid_when_expression", path, f"Invalid condition expression: {err}"
				)
			return

		raise ConditionValidationError(
			"invalid_legacy_node", path, f"Unsupported legacy condition payload type: {type(node).__name__}"
		)

	def _validate_legacy_operand(self, operand: Any, path: str) -> None:
		from flexirule.ruleflow.core.condition_errors import ConditionValidationError

		if not isinstance(operand, dict):
			raise ConditionValidationError("invalid_operand", path, "Operand must be an object")

		if "ref" in operand:
			ref = operand.get("ref")
			if not isinstance(ref, str) or not ref.strip():
				raise ConditionValidationError(
					"invalid_operand_ref", f"{path}.ref", "Operand ref must be a non-empty string"
				)
			return

		if "value" in operand or "mode" in operand:
			return

		raise ConditionValidationError("invalid_operand", path, "Operand must specify 'ref', 'value', or 'mode'")

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
		right_value = right.get("value") if isinstance(right, dict) else None

		# Link/Dynamic Link Tuple Handling
		# _compile_operand returns repr(list) for our tuples, so it looks like "['DocType', 'Value']"
		# We need to distinguish between ['DocType', 'Value'] and ['Val1', 'Val2']
		if (
			isinstance(right_value, list | tuple)
			and len(right_value) == 2
			and isinstance(right_value[0], str)
		):
			val = right_value
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
			return self._compile_operand_value(operand["value"], scopes)

		return "''"

	def _compile_operand_value(self, value, scopes):
		"""Compile a literal/structured operand payload into Python code."""
		# Structured payload from unified FlexValueControl.
		if isinstance(value, dict) and "mode" in value:
			mode = (value.get("mode") or "static").strip().lower()

			if mode in {"static", "link", "dynamic_link"}:
				return self._compile_operand_value(value.get("value"), scopes)

			if mode == "variable":
				path = value.get("path") or value.get("value") or ""
				return self._resolve_ref(path, scopes)

			if mode in {"resolver", "formula", "format", "formatter", "normalize", "normalization"}:
				expr = value.get("value") or value.get("expression") or value.get("resolver") or ""
				return self._compile_dynamic_expression(expr, scopes)

			if mode == "expression":
				return self._compile_mixed_expression(value.get("value"), scopes)

			return self._compile_operand_value(value.get("value"), scopes)

		# Frappe-compatible output: None -> '', False -> 0, True -> 1
		if value is None:
			return "''"
		if value is True:
			return "1"
		if value is False:
			return "0"

		# Preserve tuples/lists for link semantics and IN operators.
		if isinstance(value, list | tuple):
			return repr(value)

		return repr(value)

	def _compile_dynamic_expression(self, expression: Any, scopes) -> str:
		"""Compile dynamic resolver/formula expression payload."""
		if expression is None:
			return "''"

		if isinstance(expression, bool):
			return "1" if expression else "0"

		if isinstance(expression, int | float):
			return repr(expression)

		if not isinstance(expression, str):
			return repr(expression)

		expr = expression.strip()
		if not expr:
			return "''"

		# "{...}" safe-eval style expression.
		if expr.startswith("{") and expr.endswith("}") and expr.count("{") == 1:
			inner = expr[1:-1].strip()
			return inner or "''"

		# Bare context reference (doc.x / vars.y / alias.z).
		if "." in expr and expr.split(".", 1)[0] in scopes:
			return self._resolve_ref(expr, scopes)

		return repr(expr)

	def _compile_mixed_expression(self, segments: Any, scopes) -> str:
		"""Compile mixed text/tokens expression payload."""
		if not isinstance(segments, list) or not segments:
			return "''"

		parts: list[str] = []
		for seg in segments:
			if not isinstance(seg, dict):
				continue

			seg_type = seg.get("type")
			if seg_type == "text":
				parts.append(repr(seg.get("value", "")))
				continue

			attrs = seg.get("attrs") or {}
			if seg_type == "variableToken":
				ref_code = self._resolve_ref(attrs.get("path") or "", scopes)
				parts.append(f"str({ref_code} or '')")
				continue

			if seg_type in {"resolverToken", "formulaToken", "normalizeToken", "formatToken"}:
				expr_code = self._compile_dynamic_expression(
					attrs.get("expression") or attrs.get("resolver") or "", scopes
				)
				parts.append(f"str({expr_code} or '')")
				continue

		if not parts:
			return "''"
		if len(parts) == 1:
			return parts[0]
		return "(" + " + ".join(parts) + ")"

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
