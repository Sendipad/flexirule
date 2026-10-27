# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Read-only inventory for controlled canonical-condition migration.

This module intentionally reports identifiers, structural paths and issue codes only.
It never writes Rule/Rule Action records and never includes condition operands or config
values in the report. Run from Bench with:
    bench --site SITE execute flexirule.ruleflow.core.condition_migration.inventory_condition_migration
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from typing import Any

import frappe

from flexirule.ruleflow.core.condition_contract import validate_condition_node
from flexirule.ruleflow.core.condition_errors import ConditionError, ConditionValidationError
from flexirule.ruleflow.core.condition_payload import (
	detect_canonical_condition_payload,
	get_condition_payload,
)
from flexirule.ruleflow.core.contracts import normalize_action_type

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 200
MAX_ISSUES_PER_PAGE = 2000
LEGACY_GUARD_KEYS = ("pythonExpression", "when_expression", "when")


def _decode_json(value: Any) -> Any:
	if isinstance(value, dict | list):
		return value
	if not isinstance(value, str) or not value.strip():
		return []
	return json.loads(value)


def _location_issue(
	issues: list[dict[str, str]],
	*,
	rule_name: str,
	action_id: str | None,
	location: str,
	code: str,
	path: str = "$",
	severity: str = "review",
) -> None:
	"""Append an operand-free diagnostic, bounded to avoid oversized reports."""
	issues.append(
		{
			"rule": str(rule_name),
			"action": str(action_id or ""),
			"location": location,
			"code": code,
			"path": path,
			"severity": severity,
		}
	)


def _inspect_condition(
	payload: Any,
	*,
	rule_name: str,
	action_id: str | None,
	location: str,
	doctype: str | None,
	issues: list[dict[str, str]],
	counts: Counter,
) -> None:
	if payload in (None, ""):
		counts[f"{location}.absent"] += 1
		return
	try:
		is_canonical, node = detect_canonical_condition_payload(payload)
		if not is_canonical:
			counts[f"{location}.legacy_requires_review"] += 1
			_location_issue(
				issues,
				rule_name=rule_name,
				action_id=action_id,
				location=location,
				code="legacy_condition_requires_review",
			)
			return
		validate_condition_node(node, doctype=doctype)
		counts[f"{location}.canonical_valid"] += 1
	except ConditionError as exc:
		counts[f"{location}.invalid"] += 1
		_location_issue(
			issues,
			rule_name=rule_name,
			action_id=action_id,
			location=location,
			code=exc.code,
			path=exc.path,
			severity="error",
		)
	except Exception:
		counts[f"{location}.invalid"] += 1
		_location_issue(
			issues,
			rule_name=rule_name,
			action_id=action_id,
			location=location,
			code="condition_inventory_error",
			severity="error",
		)


def _inspect_assignment_guards(
	config: Any,
	*,
	rule_name: str,
	action_id: str | None,
	doctype: str | None,
	issues: list[dict[str, str]],
	counts: Counter,
) -> None:
	try:
		rows = _decode_json(config)
	except (TypeError, ValueError, json.JSONDecodeError):
		counts["assignment_config.invalid"] += 1
		_location_issue(
			issues,
			rule_name=rule_name,
			action_id=action_id,
			location="assignment_config",
			code="invalid_assignment_config",
			severity="error",
		)
		return
	if not isinstance(rows, list):
		counts["assignment_config.invalid"] += 1
		_location_issue(
			issues,
			rule_name=rule_name,
			action_id=action_id,
			location="assignment_config",
			code="assignment_config_not_list",
			severity="error",
		)
		return

	for index, row in enumerate(rows):
		if not isinstance(row, Mapping):
			continue
		guard = row.get("when_condition")
		has_legacy = any(row.get(key) not in (None, "") for key in LEGACY_GUARD_KEYS)
		if guard in (None, ""):
			if has_legacy:
				counts["assignment_guard.legacy_requires_review"] += 1
				_location_issue(
					issues,
					rule_name=rule_name,
					action_id=action_id,
					location=f"assignment_guard[{index}]",
					code="legacy_assignment_guard_requires_review",
				)
			continue

		try:
			is_canonical, node = detect_canonical_condition_payload(guard)
			if is_canonical:
				if has_legacy:
					raise ConditionValidationError(
						"multiple_guard_formats",
						f"assignments[{index}]",
						"Canonical and legacy guard formats are mixed",
					)
				validate_condition_node(node, doctype=doctype)
				counts["assignment_guard.canonical_valid"] += 1
			else:
				counts["assignment_guard.legacy_requires_review"] += 1
				_location_issue(
					issues,
					rule_name=rule_name,
					action_id=action_id,
					location=f"assignment_guard[{index}]",
					code="legacy_assignment_guard_requires_review",
				)
		except ConditionError as exc:
			counts["assignment_guard.invalid"] += 1
			_location_issue(
				issues,
				rule_name=rule_name,
				action_id=action_id,
				location=f"assignment_guard[{index}]",
				code=exc.code,
				path=exc.path,
				severity="error",
			)
		except Exception:
			counts["assignment_guard.invalid"] += 1
			_location_issue(
				issues,
				rule_name=rule_name,
				action_id=action_id,
				location=f"assignment_guard[{index}]",
				code="assignment_guard_inventory_error",
				severity="error",
			)


def _walk_collection_resolvers(
	value: Any,
	*,
	rule_name: str,
	action_id: str | None,
	doctype: str | None,
	issues: list[dict[str, str]],
	counts: Counter,
	path: str = "config",
	depth: int = 0,
) -> None:
	"""Inspect only explicit CollectionResolver structures, not query filters."""
	if depth > 32:
		counts["collection_resolver.scan_limit"] += 1
		_location_issue(
			issues,
			rule_name=rule_name,
			action_id=action_id,
			location=path,
			code="collection_resolver_scan_depth_exceeded",
			severity="error",
		)
		return
	if isinstance(value, Mapping):
		family = value.get("family")
		kind = value.get("kind")
		if family in {"collection", "child_aggregation"} or kind in {"collection", "child_aggregation"}:
			inner = value.get("config") if isinstance(value.get("config"), Mapping) else {}
			condition: Any = inner.get("condition") if "condition" in inner else value.get("condition")
			if condition is None or condition == "":
				counts["collection_predicate.absent"] += 1
			else:
				_inspect_condition(
					condition,
					rule_name=rule_name,
					action_id=action_id,
					location=f"{path}.condition",
					doctype=doctype,
					issues=issues,
					counts=counts,
				)
		for key, child in value.items():
			_walk_collection_resolvers(
				child,
				rule_name=rule_name,
				action_id=action_id,
				doctype=doctype,
				issues=issues,
				counts=counts,
				path=f"{path}.{key}",
				depth=depth + 1,
			)
	elif isinstance(value, list):
		for index, child in enumerate(value):
			_walk_collection_resolvers(
				child,
				rule_name=rule_name,
				action_id=action_id,
				doctype=doctype,
				issues=issues,
				counts=counts,
				path=f"{path}[{index}]",
				depth=depth + 1,
			)


def inventory_condition_migration(start: int = 0, page_size: int = DEFAULT_PAGE_SIZE) -> dict[str, Any]:
	"""Scan one bounded Rule page without mutation; return the next offset for reruns."""
	start = max(0, int(start))
	page_size = min(MAX_PAGE_SIZE, max(1, int(page_size)))
	rules = frappe.get_all(
		"Rule",
		fields=["name", "trigger_condition", "compiled_expression", "document_type"],
		order_by="name asc",
		limit_start=start,
		limit_page_length=page_size,
	)
	if not rules:
		return {
			"read_only": True,
			"start": start,
			"page_size": page_size,
			"rules_scanned": 0,
			"next_start": None,
			"complete": True,
			"counts": {},
			"issues": [],
			"issues_truncated": False,
		}

	rule_names = [rule.name for rule in rules]
	action_meta = frappe.get_meta("Rule Action")
	available_fields = {field.fieldname for field in action_meta.fields}
	action_fields = [
		field
		for field in (
			"name",
			"parent",
			"parenttype",
			"idx",
			"action_id",
			"action_type",
			"config",
			"condition_json",
			"compiled_expression",
		)
		if field in available_fields or field in {"name", "parent", "parenttype", "idx"}
	]
	actions = frappe.get_all(
		"Rule Action",
		filters={"parent": ["in", rule_names], "parenttype": "Rule"},
		fields=action_fields,
		order_by="parent asc, idx asc",
		limit_page_length=max(1000, page_size * 100),
	)
	action_limit = max(1000, page_size * 100)
	actions_truncated = len(actions) >= action_limit
	actions_by_parent: dict[str, list[Any]] = {}
	for action in actions:
		actions_by_parent.setdefault(action.parent, []).append(action)

	counts: Counter = Counter()
	issues: list[dict[str, str]] = []
	for rule in rules:
		trigger_payload = rule.get("trigger_condition")
		if trigger_payload in (None, "") and rule.get("compiled_expression"):
			trigger_payload = rule.get("compiled_expression")
		_inspect_condition(
			trigger_payload,
			rule_name=rule.name,
			action_id=None,
			location="trigger_condition",
			doctype=rule.get("document_type"),
			issues=issues,
			counts=counts,
		)
		if rule.get("trigger_condition") not in (None, "") and rule.get("compiled_expression"):
			try:
				is_canonical_trigger, _ = detect_canonical_condition_payload(rule.get("trigger_condition"))
			except ConditionError:
				is_canonical_trigger = False
			if is_canonical_trigger:
				counts["trigger_condition.stale_compiled_expression"] += 1
				_location_issue(
					issues,
					rule_name=rule.name,
					action_id=None,
					location="trigger_condition",
					code="stale_compiled_expression",
				)

		for action in actions_by_parent.get(rule.name, []):
			action_id = action.get("action_id") or action.get("name")
			action_type = normalize_action_type(action.get("action_type"))
			if action_type == "Condition":
				try:
					payload = get_condition_payload(action)
				except Exception:
					counts["condition_action.invalid"] += 1
					_location_issue(
						issues,
						rule_name=rule.name,
						action_id=action_id,
						location="condition_action",
						code="condition_payload_parse_error",
						severity="error",
					)
				else:
					if payload in (None, ""):
						legacy_expression = action.get("compiled_expression")
						if legacy_expression:
							payload = legacy_expression
						else:
							counts["condition_action.invalid"] += 1
							_location_issue(
								issues,
								rule_name=rule.name,
								action_id=action_id,
								location="condition_action",
								code="condition_required",
								severity="error",
							)
							continue
					is_canonical_action = False
					if payload not in (None, ""):
						try:
							is_canonical_action, _ = detect_canonical_condition_payload(payload)
						except ConditionError:
							pass
					_inspect_condition(
						payload,
						rule_name=rule.name,
						action_id=action_id,
						location="condition_action",
						doctype=rule.get("document_type"),
						issues=issues,
						counts=counts,
					)
					if is_canonical_action and action.get("compiled_expression"):
						counts["condition_action.stale_compiled_expression"] += 1
						_location_issue(
							issues,
							rule_name=rule.name,
							action_id=action_id,
							location="condition_action",
							code="stale_compiled_expression",
						)
					if action.get("condition_json") not in (None, ""):
						counts["condition_action.legacy_condition_json_present"] += 1
						_location_issue(
							issues,
							rule_name=rule.name,
							action_id=action_id,
							location="condition_json",
							code="legacy_condition_json_present",
						)
			if action_type == "Assignment":
				_inspect_assignment_guards(
					action.get("config"),
					rule_name=rule.name,
					action_id=action_id,
					doctype=rule.get("document_type"),
					issues=issues,
					counts=counts,
				)
			if action_type != "Query Records":
				try:
					config = _decode_json(action.get("config"))
				except Exception:
					config = None
				if config is not None:
					_walk_collection_resolvers(
						config,
						rule_name=rule.name,
						action_id=action_id,
						doctype=rule.get("document_type"),
						issues=issues,
						counts=counts,
					)

	issues_truncated = len(issues) > MAX_ISSUES_PER_PAGE
	return {
		"read_only": True,
		"start": start,
		"page_size": page_size,
		"rules_scanned": len(rules),
		"next_start": start + len(rules) if len(rules) == page_size else None,
		"complete": len(rules) < page_size and not actions_truncated and not issues_truncated,
		"actions_truncated": actions_truncated,
		"counts": dict(sorted(counts.items())),
		"issues": issues[:MAX_ISSUES_PER_PAGE],
		"issues_truncated": issues_truncated,
	}
