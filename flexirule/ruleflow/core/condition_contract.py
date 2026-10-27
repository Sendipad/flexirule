# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any, ClassVar, Literal

from flexirule.ruleflow.core.exceptions import RuleEngineError
from flexirule.ruleflow.core.flexvalue_contract import (
	MAX_CONDITION_DEPTH,
	MAX_CONDITION_NODES,
	FlexValueError,
	validate_flexvalue,
)

RESERVED_TOP_LEVEL_SCOPES = {
	"doc",
	"old_doc",
	"vars",
	"caller",
	"rule",
	"doctype",
}


class ConditionContractError(RuleEngineError):
	"""Raised when a condition payload violates the canonical contract."""

	def __init__(self, message: str, code: str = "INVALID_CONDITION", path: str = "$"):
		super().__init__(message)
		self.message = message
		self.code = code
		self.path = path

	def to_dict(self) -> dict[str, Any]:
		return {
			"error": self.message,
			"code": self.code,
			"path": self.path,
		}


class CanonicalOperator:
	"""Metadata definition for a canonical comparison operator."""

	def __init__(
		self,
		operator_id: str,
		label: str,
		arity: int,
		category: str,
		description: str = "",
		accepted_types: list[str] | None = None,
		fieldtypes: list[str] | None = None,
	):
		self.operator_id = operator_id
		self.label = label
		self.arity = arity  # 1 (unary) or 2 (binary)
		self.category = category
		self.description = description
		self.accepted_types = accepted_types or []
		self.fieldtypes = fieldtypes or []

	def to_dict(self) -> dict[str, Any]:
		return {
			"operator_id": self.operator_id,
			"label": self.label,
			"arity": self.arity,
			"category": self.category,
			"description": self.description,
			"accepted_types": self.accepted_types,
			"fieldtypes": self.fieldtypes,
		}


class CanonicalOperatorRegistry:
	"""Authoritative backend registry for canonical condition comparison operators."""

	_registry: ClassVar[dict[str, CanonicalOperator]] = {}
	_initialized: ClassVar[bool] = False

	@classmethod
	def register(cls, op: CanonicalOperator) -> None:
		cls._registry[op.operator_id] = op

	@classmethod
	def _ensure_initialized(cls) -> None:
		if cls._initialized:
			return

		# Equality & Comparison
		cls.register(CanonicalOperator("eq", "Equals", 2, "comparison", "Equal to RHS"))
		cls.register(CanonicalOperator("ne", "Not Equals", 2, "comparison", "Not equal to RHS"))
		cls.register(CanonicalOperator("gt", "Greater Than", 2, "comparison", "Greater than RHS"))
		cls.register(
			CanonicalOperator("gte", "Greater Than or Equal", 2, "comparison", "Greater than or equal to RHS")
		)
		cls.register(CanonicalOperator("lt", "Less Than", 2, "comparison", "Less than RHS"))
		cls.register(
			CanonicalOperator("lte", "Less Than or Equal", 2, "comparison", "Less than or equal to RHS")
		)

		# Membership
		cls.register(
			CanonicalOperator(
				"in", "In List / Set", 2, "membership", "LHS is contained in RHS list or string"
			)
		)
		cls.register(
			CanonicalOperator(
				"not_in", "Not In List / Set", 2, "membership", "LHS is not contained in RHS list or string"
			)
		)

		# Literal Text Matching
		cls.register(
			CanonicalOperator("contains", "Contains Text", 2, "text", "LHS string contains RHS substring")
		)
		cls.register(
			CanonicalOperator(
				"not_contains",
				"Does Not Contain Text",
				2,
				"text",
				"LHS string does not contain RHS substring",
			)
		)
		cls.register(
			CanonicalOperator("starts_with", "Starts With", 2, "text", "LHS string starts with RHS prefix")
		)
		cls.register(
			CanonicalOperator("ends_with", "Ends With", 2, "text", "LHS string ends with RHS suffix")
		)

		# Presence & Nullness
		cls.register(
			CanonicalOperator("is_set", "Is Set", 1, "presence", "Value is present and not null/empty string")
		)
		cls.register(
			CanonicalOperator(
				"is_not_set", "Is Not Set", 1, "presence", "Value is missing, null, or empty string"
			)
		)
		cls.register(CanonicalOperator("is_null", "Is Null", 1, "nullness", "Value is explicitly null"))
		cls.register(
			CanonicalOperator("is_not_null", "Is Not Null", 1, "nullness", "Value is present and not null")
		)

		# Emptiness
		cls.register(
			CanonicalOperator("is_empty", "Is Empty", 1, "emptiness", "Collection or string is empty")
		)
		cls.register(
			CanonicalOperator(
				"is_not_empty", "Is Not Empty", 1, "emptiness", "Collection or string is not empty"
			)
		)

		# Length Operators
		cls.register(
			CanonicalOperator("length_eq", "Length Equals", 2, "length", "Length of LHS equals RHS integer")
		)
		cls.register(
			CanonicalOperator("length_gt", "Length Greater Than", 2, "length", "Length of LHS > RHS integer")
		)
		cls.register(
			CanonicalOperator(
				"length_gte", "Length Greater Than or Equal", 2, "length", "Length of LHS >= RHS integer"
			)
		)
		cls.register(
			CanonicalOperator("length_lt", "Length Less Than", 2, "length", "Length of LHS < RHS integer")
		)
		cls.register(
			CanonicalOperator(
				"length_lte", "Length Less Than or Equal", 2, "length", "Length of LHS <= RHS integer"
			)
		)

		# Frappe Metadata
		cls.register(
			CanonicalOperator("has_field", "Has Field", 1, "metadata", "Document context has specified field")
		)
		cls.register(
			CanonicalOperator(
				"is_submittable", "Is Submittable", 1, "metadata", "Document doctype is submittable"
			)
		)

		cls._initialized = True

	@classmethod
	def get(cls, operator_id: str) -> CanonicalOperator | None:
		cls._ensure_initialized()
		return cls._registry.get(operator_id)

	@classmethod
	def is_registered(cls, operator_id: str) -> bool:
		cls._ensure_initialized()
		return operator_id in cls._registry

	@classmethod
	def get_all(cls) -> list[CanonicalOperator]:
		cls._ensure_initialized()
		return list(cls._registry.values())


def validate_condition_node(
	data: Any,
	path: str = "$",
	depth: int = 0,
	node_count_acc: list[int] | None = None,
) -> None:
	"""
	Strictly validate a canonical condition node according to the shared contract.

	Rejects envelopes, unknown keys (including 'id'), unknown node types, invalid arity,
	empty/one-child groups, and malformed operands.
	"""
	if node_count_acc is None:
		node_count_acc = [0]

	node_count_acc[0] += 1
	if node_count_acc[0] > MAX_CONDITION_NODES:
		raise ConditionContractError(
			f"Total condition node count exceeds limit of {MAX_CONDITION_NODES}",
			code="LIMIT_EXCEEDED",
			path=path,
		)

	if depth > MAX_CONDITION_DEPTH:
		raise ConditionContractError(
			f"Condition depth at '{path}' exceeds maximum allowed depth of {MAX_CONDITION_DEPTH}",
			code="LIMIT_EXCEEDED",
			path=path,
		)

	if not isinstance(data, dict):
		raise ConditionContractError(
			f"Condition node at '{path}' must be a dictionary, got {type(data).__name__}",
			code="TYPE_MISMATCH",
			path=path,
		)

	if "type" not in data:
		raise ConditionContractError(
			f"Condition node at '{path}' is missing required key 'type'",
			code="MISSING_KEY",
			path=f"{path}.type",
		)

	node_type = data["type"]
	if node_type == "comparison":
		_validate_comparison_node(data, path)
	elif node_type == "group":
		_validate_group_node(data, path, depth=depth, node_count_acc=node_count_acc)
	elif node_type == "collection_predicate":
		_validate_collection_predicate_node(data, path, depth=depth, node_count_acc=node_count_acc)
	else:
		raise ConditionContractError(
			f"Unknown condition node type '{node_type}' at '{path}'",
			code="INVALID_NODE_TYPE",
			path=f"{path}.type",
		)


def _validate_keys(data: dict, allowed_keys: set[str], path: str) -> None:
	extra_keys = set(data.keys()) - allowed_keys
	if extra_keys:
		key_str = ", ".join(sorted(extra_keys))
		raise ConditionContractError(
			f"Condition node at '{path}' contains unknown key(s): {key_str}",
			code="UNKNOWN_KEY",
			path=path,
		)


def _validate_comparison_node(data: dict, path: str) -> None:
	_validate_keys(data, {"type", "operator", "left", "right"}, path)

	if "operator" not in data:
		raise ConditionContractError(
			f"Comparison node at '{path}' missing required key 'operator'",
			code="MISSING_KEY",
			path=f"{path}.operator",
		)

	op_id = data["operator"]
	op_meta = CanonicalOperatorRegistry.get(op_id)
	if not op_meta:
		raise ConditionContractError(
			f"Unknown comparison operator '{op_id}' at '{path}.operator'",
			code="UNKNOWN_OPERATOR",
			path=f"{path}.operator",
		)

	if "left" not in data:
		raise ConditionContractError(
			f"Comparison node at '{path}' missing required operand 'left'",
			code="MISSING_OPERAND",
			path=f"{path}.left",
		)

	# Validate left FlexValue
	try:
		validate_flexvalue(data["left"], path=f"{path}.left")
	except FlexValueError as e:
		raise ConditionContractError(e.message, code=e.code, path=e.path) from e

	if op_meta.arity == 1:
		if "right" in data and data["right"] is not None:
			raise ConditionContractError(
				f"Unary operator '{op_id}' at '{path}' does not accept 'right' operand",
				code="INVALID_ARITY",
				path=f"{path}.right",
			)
	elif op_meta.arity == 2:
		if "right" not in data:
			raise ConditionContractError(
				f"Binary operator '{op_id}' at '{path}' requires 'right' operand",
				code="MISSING_OPERAND",
				path=f"{path}.right",
			)
		try:
			validate_flexvalue(data["right"], path=f"{path}.right")
		except FlexValueError as e:
			raise ConditionContractError(e.message, code=e.code, path=e.path) from e


def _validate_group_node(
	data: dict,
	path: str,
	depth: int,
	node_count_acc: list[int],
) -> None:
	_validate_keys(data, {"type", "operator", "children"}, path)

	if "operator" not in data:
		raise ConditionContractError(
			f"Group node at '{path}' missing required key 'operator'",
			code="MISSING_KEY",
			path=f"{path}.operator",
		)

	op = data["operator"]
	if op not in {"and", "or"}:
		raise ConditionContractError(
			f"Group operator at '{path}.operator' must be 'and' or 'or', got '{op}'",
			code="INVALID_GROUP_OPERATOR",
			path=f"{path}.operator",
		)

	if "children" not in data:
		raise ConditionContractError(
			f"Group node at '{path}' missing required key 'children'",
			code="MISSING_KEY",
			path=f"{path}.children",
		)

	children = data["children"]
	c_path = f"{path}.children"
	if not isinstance(children, list):
		raise ConditionContractError(
			f"Group children at '{c_path}' must be a list",
			code="TYPE_MISMATCH",
			path=c_path,
		)

	if len(children) == 0:
		raise ConditionContractError(
			f"Group node at '{path}' cannot be empty",
			code="EMPTY_GROUP",
			path=c_path,
		)

	if len(children) == 1:
		raise ConditionContractError(
			f"Canonical group node at '{path}' cannot have a single child; unwrap single child or add sibling",
			code="ONE_CHILD_GROUP",
			path=c_path,
		)

	for idx, child in enumerate(children):
		validate_condition_node(
			child,
			path=f"{c_path}[{idx}]",
			depth=depth + 1,
			node_count_acc=node_count_acc,
		)


def _validate_collection_predicate_node(
	data: dict,
	path: str,
	depth: int,
	node_count_acc: list[int],
) -> None:
	_validate_keys(data, {"type", "quantifier", "source", "as", "where"}, path)

	if "quantifier" not in data:
		raise ConditionContractError(
			f"Collection predicate at '{path}' missing required key 'quantifier'",
			code="MISSING_KEY",
			path=f"{path}.quantifier",
		)

	quantifier = data["quantifier"]
	if quantifier not in {"any", "all", "none"}:
		raise ConditionContractError(
			f"Invalid collection quantifier '{quantifier}' at '{path}.quantifier'",
			code="INVALID_QUANTIFIER",
			path=f"{path}.quantifier",
		)

	if "source" not in data:
		raise ConditionContractError(
			f"Collection predicate at '{path}' missing required key 'source'",
			code="MISSING_KEY",
			path=f"{path}.source",
		)

	try:
		validate_flexvalue(data["source"], path=f"{path}.source")
	except FlexValueError as e:
		raise ConditionContractError(e.message, code=e.code, path=e.path) from e

	if "as" not in data:
		raise ConditionContractError(
			f"Collection predicate at '{path}' missing required key 'as'",
			code="MISSING_KEY",
			path=f"{path}.as",
		)

	alias = data["as"]
	alias_path = f"{path}.as"
	if not isinstance(alias, str) or not alias.strip():
		raise ConditionContractError(
			f"Collection row alias 'as' at '{alias_path}' must be a non-empty string",
			code="INVALID_ALIAS",
			path=alias_path,
		)

	if alias in RESERVED_TOP_LEVEL_SCOPES:
		raise ConditionContractError(
			f"Collection row alias '{alias}' at '{alias_path}' collides with reserved top-level scope",
			code="FORBIDDEN_ALIAS",
			path=alias_path,
		)

	if "where" not in data:
		raise ConditionContractError(
			f"Collection predicate at '{path}' missing required key 'where'",
			code="MISSING_KEY",
			path=f"{path}.where",
		)

	validate_condition_node(
		data["where"],
		path=f"{path}.where",
		depth=depth + 1,
		node_count_acc=node_count_acc,
	)
