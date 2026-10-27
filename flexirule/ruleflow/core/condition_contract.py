"""
Canonical Condition Contract and Operator Registry

Implements canonical condition schema validation, node definitions, and the backend-owned
operator registry.
"""

from collections.abc import Callable
from typing import Any, ClassVar

from flexirule.ruleflow.core.flexvalue_contract import (
	MAX_CONDITION_DEPTH,
	MAX_CONDITION_NODES,
	FlexValueValidationError,
	validate_flex_value,
)

VALID_NODE_TYPES = {"comparison", "group", "collection_predicate"}
VALID_GROUP_OPERATORS = {"and", "or"}
VALID_COLLECTION_QUANTIFIERS = {"any", "all", "none"}


class ConditionValidationError(ValueError):
	"""Raised when a condition payload fails canonical contract validation."""

	def __init__(self, message: str, path: str = "$"):
		super().__init__(f"{path}: {message}" if path else message)
		self.message = message
		self.path = path


class CanonicalOperatorRegistry:
	"""Backend-owned registry for canonical condition operators and metadata."""

	_operators: ClassVar[dict[str, dict[str, Any]]] = {}

	@classmethod
	def register(
		cls,
		operator_id: str,
		arity: int,
		label: str,
		description: str,
		accepted_value_types: list[str] | None = None,
		is_metadata_operator: bool = False,
		handler: Callable | None = None,
	):
		cls._operators[operator_id] = {
			"id": operator_id,
			"arity": arity,
			"label": label,
			"description": description,
			"accepted_value_types": accepted_value_types or ["any"],
			"is_metadata_operator": is_metadata_operator,
			"handler": handler,
		}

	@classmethod
	def get(cls, operator_id: str) -> dict[str, Any] | None:
		return cls._operators.get(operator_id)

	@classmethod
	def exists(cls, operator_id: str) -> bool:
		return operator_id in cls._operators

	@classmethod
	def list_operators(cls) -> list[dict[str, Any]]:
		return [dict(op) for op in cls._operators.values()]


# Register stable canonical operators
def _init_default_operators():
	# Binary comparisons
	for op_id, label in [
		("eq", "Equals"),
		("ne", "Does Not Equal"),
		("gt", "Greater Than"),
		("gte", "Greater Than or Equal"),
		("lt", "Less Than"),
		("lte", "Less Than or Equal"),
		("in", "In"),
		("not_in", "Not In"),
		("contains", "Contains"),
		("not_contains", "Does Not Contain"),
		("starts_with", "Starts With"),
		("ends_with", "Ends With"),
	]:
		CanonicalOperatorRegistry.register(
			op_id, arity=2, label=label, description=f"Binary {label} comparison"
		)

	# Unary presence / state checks
	for op_id, label in [
		("is_set", "Is Set"),
		("is_not_set", "Is Not Set"),
		("is_null", "Is Null"),
		("is_not_null", "Is Not Null"),
		("is_empty", "Is Empty"),
		("is_not_empty", "Is Not Empty"),
	]:
		CanonicalOperatorRegistry.register(op_id, arity=1, label=label, description=f"Unary {label} check")

	# Length operators (binary: left operand + numeric right threshold)
	for op_id, label in [
		("length_eq", "Length Equals"),
		("length_gt", "Length Greater Than"),
		("length_gte", "Length Greater Than or Equal"),
		("length_lt", "Length Less Than"),
		("length_lte", "Length Less Than or Equal"),
	]:
		CanonicalOperatorRegistry.register(
			op_id, arity=2, label=label, description=f"Length comparison ({label})"
		)

	# Explicit metadata operators
	CanonicalOperatorRegistry.register(
		"is_submittable",
		arity=1,
		label="Is Submittable DocType",
		description="Checks if the specified DocType is submittable in metadata",
		accepted_value_types=["string"],
		is_metadata_operator=True,
	)
	CanonicalOperatorRegistry.register(
		"has_field",
		arity=2,
		label="Has Field in DocType",
		description="Checks if the specified field exists on the specified DocType",
		accepted_value_types=["string"],
		is_metadata_operator=True,
	)


_init_default_operators()


def validate_condition_payload(
	node: Any,
	path: str = "$",
	current_depth: int = 1,
	node_counter: list[int] | None = None,
	allowed_scopes: set[str] | None = None,
) -> None:
	"""
	Strictly validates a canonical condition node payload according to the contract.
	Does NOT mutate node. Rejects unknown keys, invalid arity, transient UI IDs, etc.
	"""
	if node_counter is None:
		node_counter = [0]

	node_counter[0] += 1
	if node_counter[0] > MAX_CONDITION_NODES:
		raise ConditionValidationError(
			f"Exceeded maximum condition node count of {MAX_CONDITION_NODES}", path
		)

	if current_depth > MAX_CONDITION_DEPTH:
		raise ConditionValidationError(f"Exceeded maximum condition depth of {MAX_CONDITION_DEPTH}", path)

	if not isinstance(node, dict):
		raise ConditionValidationError("Condition node must be a JSON object", path)

	# Strictly disallow transient/unknown top-level keys like 'id', 'schema', 'version', 'root'
	keys = set(node.keys())
	if "id" in keys:
		raise ConditionValidationError(
			"Transient UI property 'id' is strictly forbidden in saved conditions", path
		)
	if "schema" in keys or "version" in keys or "root" in keys:
		raise ConditionValidationError(
			"Envelope properties ('schema', 'version', 'root') are forbidden", path
		)

	if "type" not in keys:
		raise ConditionValidationError("Condition node requires 'type'", path)

	node_type = node["type"]
	if node_type not in VALID_NODE_TYPES:
		raise ConditionValidationError(f"Invalid condition node type '{node_type}'", path)

	effective_scopes = allowed_scopes if allowed_scopes is not None else {"doc", "vars", "system", "env"}

	if node_type == "comparison":
		_validate_comparison_node(node, keys, path, effective_scopes)

	elif node_type == "group":
		_validate_group_node(node, keys, path, current_depth, node_counter, effective_scopes)

	elif node_type == "collection_predicate":
		_validate_collection_predicate_node(node, keys, path, current_depth, node_counter, effective_scopes)


def _validate_comparison_node(node: dict, keys: set, path: str, allowed_scopes: set[str]) -> None:
	allowed_keys = {"type", "operator", "left", "right"}
	unknown = keys - allowed_keys
	if unknown:
		raise ConditionValidationError(f"Unknown key(s) in comparison node: {sorted(list(unknown))}", path)

	if "operator" not in keys:
		raise ConditionValidationError("Comparison node requires 'operator'", path)
	if "left" not in keys:
		raise ConditionValidationError("Comparison node requires 'left'", path)

	op_id = node["operator"]
	if not isinstance(op_id, str) or not CanonicalOperatorRegistry.exists(op_id):
		raise ConditionValidationError(f"Unknown or invalid operator '{op_id}'", path)

	op_meta = CanonicalOperatorRegistry.get(op_id)
	if op_meta is None:
		raise ConditionValidationError(f"Unknown or invalid operator '{op_id}'", path)

	arity = op_meta["arity"]

	# Validate left operand
	try:
		validate_flex_value(node["left"], f"{path}.left", allowed_scopes)
	except FlexValueValidationError as e:
		raise ConditionValidationError(e.message, e.path)

	if arity == 1:
		if "right" in keys:
			raise ConditionValidationError(f"Unary operator '{op_id}' must not have a 'right' operand", path)
	elif arity == 2:
		if "right" not in keys:
			raise ConditionValidationError(f"Binary operator '{op_id}' requires a 'right' operand", path)
		try:
			validate_flex_value(node["right"], f"{path}.right", allowed_scopes)
		except FlexValueValidationError as e:
			raise ConditionValidationError(e.message, e.path)


def _validate_group_node(
	node: dict,
	keys: set,
	path: str,
	current_depth: int,
	node_counter: list[int],
	allowed_scopes: set[str],
) -> None:
	allowed_keys = {"type", "operator", "children"}
	unknown = keys - allowed_keys
	if unknown:
		raise ConditionValidationError(f"Unknown key(s) in group node: {sorted(list(unknown))}", path)

	if "operator" not in keys:
		raise ConditionValidationError("Group node requires 'operator'", path)
	if "children" not in keys:
		raise ConditionValidationError("Group node requires 'children'", path)

	group_op = node["operator"]
	if group_op not in VALID_GROUP_OPERATORS:
		raise ConditionValidationError(f"Invalid group operator '{group_op}'. Must be 'and' or 'or'", path)

	children = node["children"]
	if not isinstance(children, list):
		raise ConditionValidationError("Group 'children' must be a list", path)
	if len(children) < 2:
		raise ConditionValidationError("Group node must contain at least two children", path)

	for idx, child in enumerate(children):
		validate_condition_payload(
			child, f"{path}.children[{idx}]", current_depth + 1, node_counter, allowed_scopes
		)


def _validate_collection_predicate_node(
	node: dict,
	keys: set,
	path: str,
	current_depth: int,
	node_counter: list[int],
	allowed_scopes: set[str],
) -> None:
	allowed_keys = {"type", "source", "quantifier", "as", "where"}
	unknown = keys - allowed_keys
	if unknown:
		raise ConditionValidationError(
			f"Unknown key(s) in collection_predicate node: {sorted(list(unknown))}", path
		)

	for req in ("source", "quantifier", "as", "where"):
		if req not in keys:
			raise ConditionValidationError(f"Collection predicate requires '{req}'", path)

	# Validate source FlexValue
	try:
		validate_flex_value(node["source"], f"{path}.source", allowed_scopes)
	except FlexValueValidationError as e:
		raise ConditionValidationError(e.message, e.path)

	quantifier = node["quantifier"]
	if quantifier not in VALID_COLLECTION_QUANTIFIERS:
		raise ConditionValidationError(f"Invalid collection quantifier '{quantifier}'", path)

	alias = node["as"]
	if not isinstance(alias, str) or not alias or alias.startswith("__"):
		raise ConditionValidationError("Collection alias 'as' must be a non-empty, non-dunder string", path)

	# Extend allowed scopes inside 'where' clause to include local alias
	where_scopes = set(allowed_scopes) | {alias}
	validate_condition_payload(node["where"], f"{path}.where", current_depth + 1, node_counter, where_scopes)
