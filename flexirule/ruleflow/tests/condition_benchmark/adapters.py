# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NeutralNode:
	"""Abstract representation of a condition tree node."""

	kind: str  # 'comparison', 'group', 'collection_predicate'
	operator: str = ""  # 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in', 'contains', 'not_contains', 'is_set', 'is_not_set', 'is_null', 'is_not_null', 'is_empty', 'is_not_empty', 'length_gt', 'length_gte', 'length_eq', 'length_lt', 'length_lte', 'has_changed', 'is_submittable', 'has_field'
	left_scope: str | None = None  # 'doc', 'item', 'row', 'old_doc'
	left_segments: list[str] = field(default_factory=list)
	right_value_type: str | None = None  # 'string', 'integer', 'decimal', 'boolean', 'list', 'null'
	right_value: Any = None
	right_scope: str | None = None
	right_segments: list[str] = field(default_factory=list)
	children: list[NeutralNode] = field(default_factory=list)
	quantifier: str | None = None  # 'any', 'all', 'none'
	source_scope: str | None = None
	source_segments: list[str] = field(default_factory=list)
	alias: str | None = None
	where: NeutralNode | None = None


@dataclass
class NeutralScenario:
	"""Neutral business scenario definition independent of candidate payload formats."""

	scenario_id: str
	tier: str
	description: str
	root: NeutralNode
	matching_doc: Any
	non_matching_doc: Any
	expected_matching_result: bool = True
	expected_non_matching_result: bool = False
	leaf_count: int = 1
	nesting_depth: int = 1
	is_invalid_test: bool = False
	expected_error_code: str | None = None


# Operator translation tables
LEGACY_OP_MAP = {
	"eq": "==",
	"ne": "!=",
	"gt": ">",
	"gte": ">=",
	"lt": "<",
	"lte": "<=",
	"in": "in",
	"not_in": "not in",
	"contains": "contains",
	"not_contains": "not_contains",
	"is_set": "is_set",
	"is_not_set": "is_not_set",
	"is_empty": "is_empty",
	"is_not_empty": "is_not_empty",
	"length_eq": "length_eq",
	"length_gt": "length_gt",
	"length_gte": "length_gte",
	"length_lt": "length_lt",
	"length_lte": "length_lte",
	"has_changed": "has_changed",
	"is_submittable": "is_submittable",
	"has_field": "has_field",
}


def node_to_legacy_payload(node: NeutralNode) -> dict | None:
	"""Translate a neutral node into a legacy condition payload (Approaches A, A-Exp, B, C)."""
	if node.kind == "group":
		return {
			"op": node.operator.lower(),
			"conditions": [
				child_payload
				for child in node.children
				if (child_payload := node_to_legacy_payload(child)) is not None
			],
		}

	if node.kind == "comparison":
		left_ref = (
			f"{node.left_scope}.{'.'.join(node.left_segments)}"
			if node.left_scope and node.left_segments
			else ""
		)
		payload: dict[str, Any] = {
			"left": {"ref": left_ref},
			"op": LEGACY_OP_MAP.get(node.operator, node.operator),
		}
		if node.operator not in {
			"is_set",
			"is_not_set",
			"is_null",
			"is_not_null",
			"is_empty",
			"is_not_empty",
			"has_changed",
			"is_submittable",
		}:
			if node.right_scope and node.right_segments:
				payload["right"] = {"ref": f"{node.right_scope}.{'.'.join(node.right_segments)}"}
			else:
				# Coerce numeric strings for legacy evaluators that do not cast strings automatically
				val = node.right_value
				if node.right_value_type == "integer" and isinstance(val, str):
					val = int(val)
				elif node.right_value_type == "decimal" and isinstance(val, str):
					try:
						val = int(val) if val.isdigit() else float(val)
					except ValueError:
						val = node.right_value
				payload["right"] = {"value": val}
		return payload

	if node.kind == "collection_predicate":
		source_ref = (
			f"{node.source_scope}.{'.'.join(node.source_segments)}"
			if node.source_scope and node.source_segments
			else ""
		)
		where_payload = node_to_legacy_payload(node.where) if node.where else {"op": "and", "conditions": []}
		return {
			"collection": source_ref,
			"op": node.quantifier or "any",
			"alias": node.alias or "item",
			"where": where_payload,
		}

	return None


def node_to_canonical_payload(node: NeutralNode) -> dict | None:
	"""Translate a neutral node into a PR #469 direct-node canonical payload."""
	if node.kind == "group":
		return {
			"type": "group",
			"operator": node.operator.lower(),
			"children": [
				child_payload
				for child in node.children
				if (child_payload := node_to_canonical_payload(child)) is not None
			],
		}

	if node.kind == "comparison":
		payload = {
			"type": "comparison",
			"operator": node.operator,
			"left": {
				"mode": "variable",
				"path": {
					"scope": node.left_scope or "doc",
					"segments": list(node.left_segments),
				},
			},
		}
		if node.operator not in {
			"is_set",
			"is_not_set",
			"is_null",
			"is_not_null",
			"is_empty",
			"is_not_empty",
			"is_submittable",
		}:
			if node.right_scope and node.right_segments:
				payload["right"] = {
					"mode": "variable",
					"path": {
						"scope": node.right_scope,
						"segments": list(node.right_segments),
					},
				}
			else:
				payload["right"] = {
					"mode": "static",
					"value_type": node.right_value_type or "string",
					"value": node.right_value,
				}
		return payload

	if node.kind == "collection_predicate":
		where_payload = (
			node_to_canonical_payload(node.where)
			if node.where
			else {"type": "group", "operator": "and", "children": []}
		)
		return {
			"type": "collection_predicate",
			"quantifier": node.quantifier or "any",
			"source": {
				"scope": node.source_scope or "doc",
				"segments": list(node.source_segments),
			},
			"as": node.alias or "item_row",
			"where": where_payload,
		}

	return None
