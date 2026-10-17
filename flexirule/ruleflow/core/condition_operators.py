# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Canonical metadata for the condition comparison contract.

Keep this table small and explicit: it is the source for server validation,
alias normalization, and the Condition Builder's operator metadata. It does
not yet replace the runtime comparator; that migration is tracked separately.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

CONDITION_SEMANTICS_VERSION = 1


@dataclass(frozen=True)
class ConditionOperator:
	"""Metadata for a single comparison token."""

	token: str
	arity: int
	label: str | None = None
	aliases: tuple[str, ...] = ()
	status: str = "supported"
	diagnostic: str | None = None


_DEFINITIONS = (
	ConditionOperator("==", 2, "equals"),
	ConditionOperator("!=", 2, "not equals"),
	ConditionOperator(">", 2, "greater than"),
	ConditionOperator("<", 2, "less than"),
	ConditionOperator(">=", 2, "greater or equal"),
	ConditionOperator("<=", 2, "less or equal"),
	ConditionOperator("in", 2, "in list"),
	ConditionOperator("not in", 2, "not in list", aliases=("not_in",)),
	ConditionOperator("is", 2),
	ConditionOperator("is not", 2),
	ConditionOperator("contains", 2, "contains"),
	ConditionOperator("not_contains", 2, "not contains"),
	ConditionOperator("length_eq", 2, "length equals"),
	ConditionOperator("length_gt", 2, "length greater than"),
	ConditionOperator("length_gte", 2, "length greater or equal"),
	ConditionOperator("length_lt", 2, "length less than"),
	ConditionOperator("length_lte", 2, "length less or equal"),
	ConditionOperator("is_set", 1, "is set"),
	ConditionOperator("is_not_set", 1, "is not set"),
	ConditionOperator("is_empty", 1, "is empty"),
	ConditionOperator("is_not_empty", 1, "is not empty"),
	ConditionOperator("is_submittable", 1, "is submittable"),
	ConditionOperator("has_field", 2, "has field"),
	ConditionOperator(
		"like",
		2,
		"contains",
		status="unsupported",
		diagnostic="is not supported in compiled conditions yet; existing rules need an explicit compatibility migration",
	),
	ConditionOperator(
		"not like",
		2,
		"not contains",
		status="unsupported",
		diagnostic="is not supported in compiled conditions yet; existing rules need an explicit compatibility migration",
	),
	ConditionOperator(
		"regex",
		2,
		status="unsupported",
		diagnostic="is not supported by the compiled condition path",
	),
	ConditionOperator(
		"has_changed",
		1,
		status="unsupported",
		diagnostic="is deprecated; use an On Field Change Process instead",
	),
)

CONDITION_OPERATOR_DEFINITIONS = MappingProxyType({item.token: item for item in _DEFINITIONS})
OPERATOR_ALIASES = MappingProxyType({alias: item.token for item in _DEFINITIONS for alias in item.aliases})
SUPPORTED_OPERATOR_TOKENS = frozenset(item.token for item in _DEFINITIONS if item.status == "supported")
BINARY_OPERATOR_TOKENS = frozenset(
	item.token for item in _DEFINITIONS if item.status == "supported" and item.arity == 2
)
UNARY_OPERATOR_TOKENS = frozenset(
	item.token for item in _DEFINITIONS if item.status == "supported" and item.arity == 1
)
UNSUPPORTED_OPERATOR_DIAGNOSTICS = MappingProxyType(
	{item.token: item.diagnostic or "is not supported" for item in _DEFINITIONS if item.status != "supported"}
)
GROUP_OPERATOR_TOKENS = frozenset({"and", "or"})
COLLECTION_OPERATION_TOKENS = frozenset({"any", "all", "none"})
OPERATOR_LABELS: dict[str, str] = {
	item.token: str(item.label) for item in _DEFINITIONS if item.label is not None
}

# Canonical UI options by Frappe fieldtype. Deprecated SQL-like tokens are
# intentionally not offered for new selections; text predicates use contains
# / not_contains, whose semantics are implemented by the condition compiler.
FIELD_TYPE_OPERATORS: dict[str, list[str]] = {
	"Data": ["==", "!=", "in", "not in", "contains", "not_contains", "is_set", "is_not_set"],
	"Text": ["==", "!=", "contains", "not_contains", "is_set", "is_not_set"],
	"Small Text": ["==", "!=", "contains", "not_contains", "is_set", "is_not_set"],
	"Long Text": ["==", "!=", "contains", "not_contains", "is_set", "is_not_set"],
	"Text Editor": ["==", "!=", "contains", "not_contains", "is_set", "is_not_set"],
	"Code": ["==", "!=", "contains", "not_contains", "is_set", "is_not_set"],
	"Password": ["is_set", "is_not_set"],
	"Select": ["==", "!=", "in", "not in", "is_set", "is_not_set"],
	"Link": ["==", "!=", "in", "not in", "is_set", "is_not_set"],
	"Dynamic Link": ["==", "!=", "in", "not in", "is_set", "is_not_set"],
	"Int": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Float": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Currency": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Percent": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Rating": ["==", "!=", ">", "<", ">=", "<="],
	"Check": ["==", "!="],
	"Date": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Datetime": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Time": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Duration": ["==", "!=", ">", "<", ">=", "<=", "is_set", "is_not_set"],
	"Attach": ["is_set", "is_not_set"],
	"Attach Image": ["is_set", "is_not_set"],
	"Signature": ["is_set", "is_not_set"],
	"Color": ["==", "!=", "is_set", "is_not_set"],
	"Geolocation": ["is_set", "is_not_set"],
	"JSON": ["is_set", "is_not_set"],
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
	"_default": ["==", "!=", "is_set", "is_not_set", "is_empty", "is_not_empty"],
}


def normalize_operator(value: str) -> str:
	"""Normalize case and documented aliases without guessing semantics."""
	token = value.strip().lower()
	return OPERATOR_ALIASES.get(token, token)


_VALUE_COMPARATORS = {
	"==": operator.eq,
	"!=": operator.ne,
	">": operator.gt,
	"<": operator.lt,
	">=": operator.ge,
	"<=": operator.le,
	"is": operator.is_,
	"is not": operator.is_not,
	"in": lambda left, right: left in right,
	"not in": lambda left, right: left not in right,
}
_LENGTH_COMPARATORS = {
	"length_eq": operator.eq,
	"length_gt": operator.gt,
	"length_gte": operator.ge,
	"length_lt": operator.lt,
	"length_lte": operator.le,
}
def _condition_is_empty(value: Any) -> bool:
	"""Apply the established FlexiRule empty-value contract without generic truthiness."""
	if value is None:
		return True
	if isinstance(value, str):
		return value.strip() == ""
	if isinstance(value, list | tuple | dict | set):
		return len(value) == 0
	return False


def _condition_length(value: Any) -> int:
	"""Match the RuleEngine's length helper for existing condition expressions."""
	if value is None:
		return 0
	if isinstance(value, str):
		return len(value.strip())
	if isinstance(value, list | tuple | dict | set):
		return len(value)
	try:
		return len(value)
	except Exception:
		return 0


def compare_values(left: Any, operator_token: str, right: Any = None) -> bool:
	"""Compare already-resolved values using the canonical primitive semantics.

	Values are not coerced: explicit None remains distinct from an empty string,
	and zero/False are not treated as empty by generic truthiness checks. A
	membership operation requires a valid container; a wrong-type RHS raises so
	callers can log the evaluation error instead of disguising it as a match.
	Metadata-dependent operators (has_field/is_submittable) belong to the runtime
	context and are intentionally handled outside this pure value comparator.
	"""
	token = normalize_operator(operator_token)
	if token not in SUPPORTED_OPERATOR_TOKENS:
		diagnostic = UNSUPPORTED_OPERATOR_DIAGNOSTICS.get(token)
		if diagnostic:
			raise ValueError(f"Unsupported condition operator {token!r}: {diagnostic}")
		raise ValueError(f"Unknown condition operator: {operator_token!r}")

	if token in _VALUE_COMPARATORS:
		return bool(_VALUE_COMPARATORS[token](left, right))

	if token == "is_set":
		return left is not None and left != ""
	if token == "is_not_set":
		return left is None or left == ""
	if token == "is_empty":
		return _condition_is_empty(left)
	if token == "is_not_empty":
		return not _condition_is_empty(left)

	if token == "contains":
		if left is None or left == "":
			return False
		return right in str(left)
	if token == "not_contains":
		if left is None or left == "":
			return True
		return right not in str(left)

	if token in _LENGTH_COMPARATORS:
		return bool(_LENGTH_COMPARATORS[token](_condition_length(left), right))

	if token in {"has_field", "is_submittable"}:
		raise ValueError(f"Condition operator {token!r} requires DocType metadata context")

	# These are listed as supported metadata tokens, but any other supported
	# token needs an explicit implementation here before it may compare values.
	raise ValueError(f"Condition operator {token!r} has no primitive comparator")
