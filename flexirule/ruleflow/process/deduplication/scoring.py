# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Shared deduplication scoring utilities.

This module owns:
- candidate blocking filter generation
- weighted similarity scoring
- structured duplicate result output
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import frappe
from rapidfuzz import fuzz

from flexirule.ruleflow.utils.field_resolver import parse_field_list

ALGORITHMS = ("Exact", "Fuzzy", "Contains", "Phonetic", "Numeric Range", "Date Distance")

DEFAULTS_BY_ALGORITHM = {
	"Exact": {"threshold": 1.0, "weight": 1.0, "tolerance": 0, "normalize": True},
	"Fuzzy": {"threshold": 0.8, "weight": 0.5, "tolerance": 0, "normalize": True},
	"Contains": {"threshold": 0.8, "weight": 0.5, "tolerance": 0, "normalize": True},
	"Phonetic": {"threshold": 0.9, "weight": 0.5, "tolerance": 0, "normalize": True},
	"Numeric Range": {"threshold": 0.5, "weight": 0.4, "tolerance": 30, "normalize": False},
	"Date Distance": {"threshold": 0.5, "weight": 0.4, "tolerance": 30, "normalize": False},
}


def normalize_fields_config(config: dict | None) -> list[dict]:
	"""Normalize process config into a canonical list of comparison rules."""
	config = config or {}
	fields_config = config.get("fields_config") or []
	normalized: list[dict] = []

	if not fields_config:
		for fieldname in parse_field_list(config.get("fields")):
			fields_config.append({"fieldname": fieldname, "algorithm": "Exact"})

	for raw in fields_config:
		fieldname = raw.get("fieldname") or raw.get("field")
		if not fieldname:
			continue

		algorithm = raw.get("algorithm") or "Fuzzy"
		if algorithm not in ALGORITHMS:
			algorithm = "Fuzzy"

		defaults = DEFAULTS_BY_ALGORITHM[algorithm]
		normalized.append(
			{
				"fieldname": fieldname,
				"algorithm": algorithm,
				"threshold": _coerce_float(raw.get("threshold"), defaults["threshold"]),
				"weight": _coerce_float(raw.get("weight"), defaults["weight"]),
				"tolerance": _coerce_float(raw.get("tolerance"), defaults["tolerance"]),
				"normalize": bool(raw.get("normalize", defaults["normalize"])),
				"included_in_filters": bool(raw.get("included_in_filters", True)),
			}
		)

	return normalized


def build_candidate_filters(doc, fields_config: list[dict], config: dict | None = None) -> dict:
	"""Build optimized blocking filters for candidate fetch."""
	config = config or {}
	filters = dict(config.get("candidate_filters") or {})

	for field_cfg in fields_config:
		if not field_cfg.get("included_in_filters", True):
			continue

		fieldname = field_cfg["fieldname"]
		value = doc.get(fieldname)
		if value in (None, ""):
			continue

		algorithm = field_cfg.get("algorithm", "Exact")
		if algorithm == "Exact":
			filters[fieldname] = value
		elif algorithm in ("Fuzzy", "Contains", "Phonetic") and isinstance(value, str):
			prefix = value.strip().lower()[: int(config.get("blocking_prefix_length", 3) or 3)]
			if prefix:
				filters[fieldname] = ["like", f"%{prefix}%"]

	exclude_current = config.get("exclude_current_document", True)
	if exclude_current and getattr(doc, "name", None):
		filters["name"] = ["!=", doc.name]

	if config.get("ignore_cancelled", True) and _doctype_has_field(doc.doctype, "docstatus"):
		filters["docstatus"] = ["!=", 2]

	return filters


def fetch_candidate_rows(doc, fields_config: list[dict], config: dict | None = None) -> list[dict]:
	"""Fetch candidate rows with only the fields required for scoring."""
	config = config or {}
	candidate_doctype = config.get("candidate_doctype") or doc.doctype
	filters = build_candidate_filters(doc, fields_config, config)
	fieldnames = set(["name"] + [field["fieldname"] for field in fields_config])
	fieldnames.update(parse_field_list(config.get("candidate_fields")))

	return frappe.get_all(
		candidate_doctype,
		filters=filters,
		fields=sorted(fieldnames),
		limit=int(config.get("candidate_limit", 1000) or 1000),
		order_by=config.get("candidate_order_by") or "modified desc",
	)


class DedupeScoringEngine:
	"""Weighted record matcher for current-doc vs candidate row scoring."""

	def __init__(self, doc, fields_config: list[dict], config: dict | None = None):
		self.doc = doc
		self.fields_config = fields_config
		self.config = config or {}
		self._phonetic_scorer: Any = None

	def find_matches(self, candidates: list[dict]) -> dict:
		"""Score candidates and return a structured dedupe result."""
		matches: list[dict] = []
		total_candidates = len(candidates)
		overall_threshold = _coerce_float(self.config.get("overall_threshold"), 0.8)
		minimum_fields_matched = int(self.config.get("minimum_fields_matched", 1) or 1)
		stop_after_first = bool(self.config.get("stop_after_first_match", False))
		total_weight = sum(max(field["weight"], 0.0) for field in self.fields_config) or 1.0

		for candidate in candidates:
			field_results: dict[str, dict] = {}
			weighted_sum = 0.0
			matched_fields = 0

			for field_cfg in self.fields_config:
				fieldname = field_cfg["fieldname"]
				score = self.get_score(
					field_cfg["algorithm"],
					self.doc.get(fieldname),
					candidate.get(fieldname),
					field_cfg,
				)
				passed = score >= field_cfg["threshold"]
				if passed:
					matched_fields += 1
				weighted_sum += score * max(field_cfg["weight"], 0.0)

				field_results[fieldname] = {
					"score": round(score * 100, 2),
					"matched": passed,
					"algorithm": field_cfg["algorithm"],
					"threshold": round(field_cfg["threshold"] * 100, 2),
					"doc_value": self.doc.get(fieldname),
					"candidate_value": candidate.get(fieldname),
				}

			final_score = weighted_sum / total_weight
			if final_score >= overall_threshold and matched_fields >= minimum_fields_matched:
				matches.append(
					{
						"name": candidate.get("name"),
						"doctype": self.config.get("candidate_doctype") or self.doc.doctype,
						"score": round(final_score * 100, 2),
						"matched_field_count": matched_fields,
						"fields": field_results,
						"candidate": dict(candidate),
					}
				)
				if stop_after_first:
					break

		matches.sort(key=lambda row: row["score"], reverse=True)
		return {
			"has_match": bool(matches),
			"match_count": len(matches),
			"candidate_count": total_candidates,
			"best_match": matches[0] if matches else None,
			"matches": matches,
			"criteria": {
				"overall_threshold": overall_threshold,
				"minimum_fields_matched": minimum_fields_matched,
				"fields_config": self.fields_config,
			},
		}

	def get_score(self, algorithm: str, val1, val2, field_config: dict | None = None) -> float:
		"""Calculate similarity score in the range 0.0 - 1.0."""
		if val1 is None or val2 is None:
			return 0.0

		field_config = field_config or {}
		do_normalize = field_config.get("normalize", True)
		s1 = self.normalize_value(val1) if do_normalize else str(val1).lower()
		s2 = self.normalize_value(val2) if do_normalize else str(val2).lower()

		if algorithm == "Exact":
			return 1.0 if s1 == s2 else 0.0
		if algorithm == "Fuzzy":
			return fuzz.ratio(s1, s2) / 100.0
		if algorithm == "Contains":
			return 1.0 if (s1 in s2 or s2 in s1) else 0.0
		if algorithm == "Phonetic":
			return self.get_phonetic_scorer()(val1, val2)
		if algorithm == "Numeric Range":
			return self._numeric_range_score(val1, val2, field_config)
		if algorithm == "Date Distance":
			return self._date_distance_score(val1, val2, field_config)
		return 0.0

	def get_phonetic_scorer(self):
		"""Lazy-load a phonetic scoring function."""
		if self._phonetic_scorer:
			return self._phonetic_scorer

		try:
			import jellyfish

			def phonetic_score(a, b):
				return 1.0 if jellyfish.metaphone(str(a)) == jellyfish.metaphone(str(b)) else 0.0

			self._phonetic_scorer = phonetic_score
		except ImportError:
			self._phonetic_scorer = lambda a, b: 1.0 if str(a).lower() == str(b).lower() else 0.0

		return self._phonetic_scorer

	@staticmethod
	def normalize_value(value) -> str:
		"""Normalize values for text comparison."""
		if value is None:
			return ""
		if not isinstance(value, str):
			return str(value)
		return re.sub(r"\s+", " ", value.lower().strip())

	@staticmethod
	def create_fingerprint(doc, fields: list[str]) -> str:
		"""Create a stable hash fingerprint for the given fields."""
		values = []
		for field in fields:
			value = doc.get(field)
			if value not in (None, ""):
				values.append(DedupeScoringEngine.normalize_value(value).replace(" ", ""))
		return hashlib.md5("|".join(sorted(values)).encode()).hexdigest()

	def _numeric_range_score(self, val1, val2, field_config: dict) -> float:
		try:
			n1 = float(val1)
			n2 = float(val2)
		except (TypeError, ValueError):
			return 0.0

		tolerance = abs(_coerce_float(field_config.get("tolerance"), 0.0))
		if tolerance > 0:
			diff = abs(n1 - n2)
			return max(0.0, 1.0 - (diff / tolerance))

		max_val = max(abs(n1), abs(n2))
		if max_val == 0:
			return 1.0
		return max(0.0, 1.0 - (abs(n1 - n2) / max_val))

	def _date_distance_score(self, val1, val2, field_config: dict) -> float:
		from frappe.utils import date_diff, getdate

		tolerance = abs(_coerce_float(field_config.get("tolerance"), 30.0)) or 1.0
		try:
			diff = abs(date_diff(getdate(val1), getdate(val2)))
		except Exception:
			return 0.0
		return max(0.0, 1.0 - (diff / tolerance))


def _coerce_float(value, default: float) -> float:
	try:
		return float(value)
	except (TypeError, ValueError):
		return float(default)


def _doctype_has_field(doctype: str, fieldname: str) -> bool:
	meta = frappe.get_meta(doctype)
	return bool(
		meta.get_field(fieldname) or fieldname in {"name", "owner", "creation", "modified", "docstatus"}
	)
