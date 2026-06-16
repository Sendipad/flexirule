# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import re
import unicodedata
from typing import Any

import frappe

# =============================================================================
# TRANSLATION TABLE
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
# OPERATIONS
# =============================================================================

NORMALIZATION_OPERATIONS = {
	"trim": lambda x: x.strip() if isinstance(x, str) else x,
	"lowercase": lambda x: x.lower() if isinstance(x, str) else x,
	"uppercase": lambda x: x.upper() if isinstance(x, str) else x,
	"title_case": lambda x: x.title() if isinstance(x, str) else x,
	"slug": lambda x: (
		re.sub(r"[^\w\s-]", "", x).strip().lower().replace(" ", "-") if isinstance(x, str) else x
	),
	"snake_case": lambda x: (
		re.sub(r"[^\w\s]", "", x).strip().lower().replace(" ", "_") if isinstance(x, str) else x
	),
	"remove_spaces": lambda x: x.replace(" ", "") if isinstance(x, str) else x,
	"remove_extra_spaces": lambda x: (re.sub(r"\s+", " ", x).strip() if isinstance(x, str) else x),
	"remove_punctuation": lambda x: (re.sub(r"[^\w\s]", "", x) if isinstance(x, str) else x),
	"remove_numbers": lambda x: re.sub(r"\d+", "", x) if isinstance(x, str) else x,
	"numeric_only": lambda x: re.sub(r"\D", "", x) if isinstance(x, str) else x,
	"alphanumeric_only": lambda x: re.sub(r"[^\w]", "", x) if isinstance(x, str) else x,
	"unicode_normalize": lambda x: (unicodedata.normalize("NFKD", x) if isinstance(x, str) else x),
	"translate_chars": lambda x: (x.translate(TRANSLATION_TABLE) if isinstance(x, str) else x),
}

# =============================================================================
# PROFILES
# =============================================================================

NORMALIZATION_PROFILES = {
	"URL Safe": ["trim", "lowercase", "slug"],
	"Clean Text": ["trim", "remove_extra_spaces"],
	"Upper Case Token": ["trim", "uppercase", "remove_spaces"],
}


def execute_normalization_pipeline(
	value: Any, pipeline: list[str] | None = None, profile: str | None = None, include_breakdown: bool = False
) -> dict[str, Any]:
	"""
	Execute a normalization pipeline on a value.
	Returns a dict with 'normalized_value' and optionally 'breakdown'.
	"""
	if profile and profile in NORMALIZATION_PROFILES:
		pipeline = NORMALIZATION_PROFILES[profile]

	if not pipeline:
		return {"normalized_value": value, "breakdown": []}

	current_value = value
	breakdown = []

	if include_breakdown:
		breakdown.append({"operation": "Initial", "value": current_value})

	for op_name in pipeline:
		op_func = NORMALIZATION_OPERATIONS.get(op_name)
		if op_func:
			try:
				current_value = op_func(current_value)
				if include_breakdown:
					breakdown.append({"operation": op_name, "value": current_value})
			except Exception as e:
				frappe.log_error(
					title=f"Normalization Pipeline Error: {op_name}",
					message=f"Value: {current_value}\nError: {e!s}",
				)

	return {"normalized_value": current_value, "breakdown": breakdown}
