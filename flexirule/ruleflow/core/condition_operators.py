# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Canonical metadata for the condition comparison contract.

Keep this table small and explicit: it is the source for server validation,
alias normalization, and the Condition Builder's operator metadata. It does
not yet replace the runtime comparator; that migration is tracked separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


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
OPERATOR_ALIASES = MappingProxyType(
	{alias: item.token for item in _DEFINITIONS for alias in item.aliases}
)
SUPPORTED_OPERATOR_TOKENS = frozenset(
	item.token for item in _DEFINITIONS if item.status == "supported"
)
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
OPERATOR_LABELS = {
	item.token: item.label for item in _DEFINITIONS if item.label is not None
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
	"Table": ["is_set", "is_not_set", "is_empty", "is_not_empty", "length_eq", "length_gt", "length_gte", "length_lt", "length_lte"],
	"Table MultiSelect": ["is_set", "is_not_set", "is_empty", "is_not_empty", "length_eq", "length_gt", "length_gte", "length_lt", "length_lte"],
	"_default": ["==", "!=", "is_set", "is_not_set", "is_empty", "is_not_empty"],
}


def normalize_operator(value: str) -> str:
	"""Normalize case and documented aliases without guessing semantics."""
	token = value.strip().lower()
	return OPERATOR_ALIASES.get(token, token)
