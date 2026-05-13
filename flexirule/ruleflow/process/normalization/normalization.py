# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import re
import unicodedata
from collections.abc import Callable
from typing import Any

import frappe
from frappe import _

from flexirule.ruleflow.utils.field_resolver import FieldResolver


def execute(context, func=None, config=None):
	"""
	Execute a normalization operation.
	"""
	if not func:
		frappe.throw(_("Operation function name is required"))

	if func not in _OPERATIONS:
		frappe.throw(_("Unknown operation: {0}. Available: {1}").format(func, ", ".join(_OPERATIONS.keys())))

	return _OPERATIONS[func](context, config or {})


# =============================================================================
# TRANSLATION TABLE (borrowed conceptually from UPH)
# =============================================================================

TRANSLATION_TABLE = str.maketrans(
	{
		"أ": "ا",
		"إ": "ا",
		"آ": "ا",
		"ى": "ي",
		"ة": "ه",
		"ؤ": "و",
		"ئ": "ي",
		"ـ": "",
		**{chr(0x660 + i): str(i) for i in range(10)},  # Arabic digits
	}
)

# =============================================================================
# TRANSFORMATIONS (single-arg, stateless)
# =============================================================================

TRANSFORMATIONS: dict[str, Callable] = {
	"trim": lambda x: x.strip() if isinstance(x, str) else x,
	"lowercase": lambda x: x.lower() if isinstance(x, str) else x,
	"uppercase": lambda x: x.upper() if isinstance(x, str) else x,
	"casefold": lambda x: x.casefold() if isinstance(x, str) else x,
	"unicode_normalize": lambda x: (unicodedata.normalize("NFKD", x) if isinstance(x, str) else x),
	"translate_chars": lambda x: (x.translate(TRANSLATION_TABLE) if isinstance(x, str) else x),
	"remove_spaces": lambda x: x.replace(" ", "") if isinstance(x, str) else x,
	"remove_extra_spaces": lambda x: (re.sub(r"\s+", " ", x).strip() if isinstance(x, str) else x),
	"remove_punctuation": lambda x: (re.sub(r"[^\w\s]", "", x) if isinstance(x, str) else x),
	"remove_numbers": lambda x: re.sub(r"\d+", "", x) if isinstance(x, str) else x,
	"numeric_only": lambda x: re.sub(r"\D", "", x) if isinstance(x, str) else x,
	"alphanumeric_only": lambda x: re.sub(r"[^\w]", "", x) if isinstance(x, str) else x,
	"slug": lambda x: (
		re.sub(r"[^\w\s-]", "", x).strip().lower().replace(" ", "-") if isinstance(x, str) else x
	),
	"title_case": lambda x: x.title() if isinstance(x, str) else x,
	"name_normalize": lambda x: (" ".join([w.capitalize() for w in x.split()]) if isinstance(x, str) else x),
	"email_normalize": lambda x: (
		f"{x.split('@')[0].split('+')[0].replace('.', '').lower()}@{x.split('@')[1].lower()}"
		if isinstance(x, str) and "@" in x
		else x
	),
	"currency_to_number": lambda x: (re.sub(r"[^\d.]", "", x) if isinstance(x, str) else x),
	"tax_id_clean": lambda x: re.sub(r"[\s-]", "", x) if isinstance(x, str) else x,
	"standard_date": lambda x: (str(frappe.utils.getdate(x)) if isinstance(x, str) and x else x),
}

# =============================================================================
# CORE HELPERS
# =============================================================================


def apply_transformations(value, transformations):
	"""
	Apply a list of transformation keys to a value.
	"""
	if value is None:  # Keep original None handling
		return None

	if not transformations:
		return value

	# Handle list of dicts (Table format from UI)
	# [{ "transformation": "trim" }, ...]
	if isinstance(transformations, list) and transformations and isinstance(transformations[0], dict):
		transformations = [t.get("transformation") for t in transformations if t.get("transformation")]

	# Handle Comma Separated Strings (MultiSelect Tags format)
	if isinstance(transformations, str):
		transformations = [t.strip() for t in transformations.split(",") if t.strip()]

	for (
		transform_name
	) in transformations:  # Renamed 'transform' to 'transform_name' to avoid conflict with TRANSFORMATIONS
		# Backward compat: ignore invalid types
		if not isinstance(transform_name, str):
			continue

		transform_name = transform_name.lower().strip()
		func = TRANSFORMATIONS.get(transform_name)
		if not func:
			frappe.logger().warning(f"Unknown transformation: {transform_name}")  # Keep original warning
			continue

		try:
			value = func(value)  # Apply transformation to 'value' directly
		except Exception as e:  # Keep original error logging
			frappe.log_error(
				title="FlexiRule Normalization Error",
				message=f"Step: {transform_name}\nValue: {value}\n{e}",
			)
	return value


# =============================================================================
# OPERATIONS
# =============================================================================


def transform_value(context, config):
	"""
	Apply transformations to an input string evaluated from an expression or field.
	Returns the transformed value. The engine's mutation_mode handles setting it.
	"""
	source_value_expr = config.get("source_value")
	source_field = config.get("source_field")
	transformations = config.get("transformations")

	value = None
	if source_value_expr:
		value = frappe.safe_eval(source_value_expr, None, context)
	elif source_field:
		value = FieldResolver.resolve(context.get("doc"), source_field)

	if value is None:
		return None

	if isinstance(transformations, str):
		transformations = [t.strip() for t in transformations.split("\n") if t.strip()]

	if not isinstance(transformations, list):
		transformations = [transformations] if transformations else []

	return apply_transformations(value, transformations)


# Whitelisted API for testing/preview
@frappe.whitelist()
def preview_normalization(text: str, transformations: str | list):
	"""
	Preview normalization result without saving
	"""
	from flexirule.ruleflow.core.permissions import require_builder_access

	require_builder_access()

	import json

	if isinstance(transformations, str):
		try:
			transformations_parsed = json.loads(transformations)
		except Exception:
			transformations_parsed = [t.strip() for t in transformations.split(",")]
	else:
		transformations_parsed = transformations

	if isinstance(text, list):
		return [apply_transformations(t, transformations_parsed) for t in text]

	return apply_transformations(text, transformations_parsed)


# ============================================================
# DISPATCHER
# ============================================================


def mask_value(context, config):
	"""
	Masks sensitive data (emails, phone numbers, credit cards).
	Returns a Single Value (string).
	"""
	source_value_expr = config.get("source_value")
	source_field = config.get("source_field")
	mask_type = config.get("mask_type")

	value = None
	if source_value_expr:
		value = frappe.safe_eval(source_value_expr, None, context)
	elif source_field:
		value = FieldResolver.resolve(context.get("doc"), source_field)

	if not value:
		return None

	value = str(value)
	if mask_type == "email":
		parts = value.split("@")
		if len(parts) == 2:
			return f"{parts[0][0]}***@{parts[1]}"
		return "***"
	elif mask_type == "phone":
		if len(value) > 4:
			return f"***-***-{value[-4:]}"
		return "***"
	elif mask_type == "credit_card":
		if len(value) > 4:
			return f"****-****-****-{value[-4:]}"
		return "****"
	elif mask_type == "partial":
		return f"{value[:2]}***{value[-2:]}" if len(value) > 4 else "***"

	return "***"


def transform_multi_fields(context, config):
	"""
	Applies the same transformations to multiple fields at once.
	Returns a Dictionary mapping field names to their transformed values.
	"""
	source_fields = config.get("source_fields")
	transformations = config.get("transformations")

	if isinstance(source_fields, str):
		source_fields = [f.strip() for f in source_fields.split(",")]

	if isinstance(transformations, str):
		transformations = [t.strip() for t in transformations.split("\n") if t.strip()]

	if not source_fields or not transformations:
		return {}

	results = {}
	for field in source_fields:
		value = FieldResolver.resolve(context.get("doc"), field)
		if value is not None:
			results[field] = apply_transformations(value, transformations)

	return results


_OPERATIONS = {
	"transform_value": transform_value,
	"mask_value": mask_value,
	"transform_multi_fields": transform_multi_fields,
}
