# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Search Service — Fuzzy search for actions and operations.

Provides a unified search API that indexes:
  - Action type names + descriptions (from contracts)
  - Process operation names + labels
  - Operation descriptions

Uses Frappe's built-in string matching when rapidfuzz is not available,
with optional rapidfuzz for better fuzzy matching.
"""

from __future__ import annotations

import frappe
from frappe import _

from flexirule.ruleflow.core.contracts import (
	ACTION_TYPE_CONTRACT,
	get_contract,
	normalize_action_type,
)

# Category mapping for UI grouping
ACTION_CATEGORIES = {
	"Entry Action": "Trigger",
	"Condition": "Logic",
	"Loop": "Logic",
	"Switch": "Logic",
	"Stop": "Control",
	"Wait": "Control",
	"Set Value": "Data",
	"Query Records": "Data",
	"Document Action": "Data",
	"Process": "Process",
	"Sub-Rule": "Modularity",
	"Notify": "Integration",
	"Raise Error": "Control",
}


def search_actions(query: str, filters: dict | None = None, limit: int = 20) -> list[dict]:
	"""Fuzzy search across all available action types and operations.

	Args:
	    query: Search query string
	    filters: Optional filters:
	        - document_type: Filter document-aware operations
	        - exclude_types: List of action types to exclude
	    limit: Max results

	Returns:
	    list of dicts with action_type, operation, label, description, etc.
	"""
	filters = filters or {}
	candidates = _build_search_index(filters)

	if not query or not query.strip():
		return candidates[:limit]

	# Try rapidfuzz first, fall back to basic matching
	try:
		return _fuzzy_search(query, candidates, limit)
	except ImportError:
		return _basic_search(query, candidates, limit)


def _fuzzy_search(query: str, candidates: list[dict], limit: int) -> list[dict]:
	"""Use rapidfuzz for high-quality fuzzy matching."""
	from rapidfuzz import fuzz
	from rapidfuzz import process as rfprocess

	results = rfprocess.extract(
		query,
		{i: c["search_text"] for i, c in enumerate(candidates)},
		scorer=fuzz.WRatio,
		limit=limit,
		score_cutoff=35,
	)

	return [{**candidates[idx], "score": round(score, 1)} for __, score, idx in results]


def _basic_search(query: str, candidates: list[dict], limit: int) -> list[dict]:
	"""Fallback search using simple substring + keyword matching."""
	query_lower = query.lower()
	query_words = query_lower.split()

	scored = []
	for candidate in candidates:
		text = candidate["search_text"].lower()
		score = 0

		# Exact substring match
		if query_lower in text:
			score += 80

		# Word-level matching
		for word in query_words:
			if word in text:
				score += 30
			# Prefix match
			for token in text.split():
				if token.startswith(word):
					score += 20

		if score > 0:
			scored.append((candidate, score))

	scored.sort(key=lambda x: x[1], reverse=True)
	return [{**c, "score": s} for c, s in scored[:limit]]


def _build_search_index(filters: dict) -> list[dict]:
	"""Build searchable index from contracts + process operations."""
	exclude_types = set(filters.get("exclude_types", []))
	index = []

	# 1. Static action types from contracts
	for action_type, contract in ACTION_TYPE_CONTRACT.items():
		if action_type in exclude_types:
			continue

		# Skip internal/disabled types
		if contract.get("release_disabled"):
			continue

		# Skip Entry Action from the search (it's always present)
		if action_type == "Entry Action":
			continue

		css = contract.get("css", {})
		label = contract.get("label", action_type)
		description = contract.get("description", "")

		index.append(
			{
				"action_type": action_type,
				"operation": None,
				"process_name": None,
				"label": label,
				"description": description,
				"icon": css.get("icon", "fa fa-circle"),
				"color": css.get("color", "#6b7280"),
				"search_text": f"{action_type} {label} {description}",
				"category": ACTION_CATEGORIES.get(action_type, "Other"),
			}
		)

	# 2. Dynamic process operations
	try:
		processes = frappe.get_all(
			"Process",
			filters={"enabled": 1},
			fields=["name", "label"],
		)

		for process in processes:
			process_doc = frappe.get_cached_doc("Process", process.name)

			for op in process_doc.get("operations") or []:
				if not op.get("func_name"):
					continue

				op_label = op.get("label") or op.get("func_name", "")
				op_desc = op.get("description") or ""

				index.append(
					{
						"action_type": "Process",
						"operation": op.func_name,
						"process_name": process.name,
						"label": f"{process.label or process.name}: {op_label}",
						"description": op_desc,
						"icon": "fa fa-cog",
						"color": "#8b5cf6",
						"search_text": f"Process {process.name} {op_label} {op.func_name} {op_desc}",
						"category": "Process",
					}
				)
	except Exception:
		# If Process doctype doesn't exist or other issues, skip
		pass

	return index
