# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import re
import unicodedata
from typing import Any

import frappe

# =============================================================================
# TRANSLATION TABLES
# =============================================================================

ARABIC_INDIC_DIGITS = {chr(0x660 + i): str(i) for i in range(10)}
PERSIAN_DIGITS = {chr(0x6F0 + i): str(i) for i in range(10)}

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
		**ARABIC_INDIC_DIGITS,
		**PERSIAN_DIGITS,
	}
)

# =============================================================================
# HELPERS
# =============================================================================


def remove_diacritics(text: Any) -> Any:
	"""Strip accents/diacritics from Latin characters."""
	if not isinstance(text, str):
		return text
	# Decompose characters into base + combining marks
	normalized = unicodedata.normalize("NFD", text)
	# Filter out combining marks (category 'Mn')
	return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def phone_normalize(text: Any) -> Any:
	"""Clean phone numbers: strip non-digits except leading +, handle Indic digits."""
	if not isinstance(text, str):
		return text

	# Apply translation for non-Western digits
	text = text.translate(TRANSLATION_TABLE)

	# Preserve leading + for international format
	prefix = "+" if text.strip().startswith("+") else ""

	# Extract only digits
	digits = "".join(re.findall(r"\d", text))

	return f"{prefix}{digits}"


def email_normalize(x: Any) -> Any:
	"""Normalize email addresses by cleaning common aliases and dots (provider specific)."""
	if isinstance(x, str) and "@" in x:
		parts = x.split("@")
		user = parts[0].split("+")[0].replace(".", "").lower()
		domain = parts[1].lower()
		return f"{user}@{domain}"
	return x


def mask_email(x: Any) -> Any:
	if not isinstance(x, str) or "@" not in x:
		return "***"
	parts = x.split("@")
	return f"{parts[0][0]}***@{parts[1]}"


def mask_phone(x: Any) -> Any:
	if not isinstance(x, str) or len(x) <= 4:
		return "***"
	return f"***-***-{x[-4:]}"


def mask_credit_card(x: Any) -> Any:
	if not isinstance(x, str) or len(x) <= 4:
		return "****"
	return f"****-****-****-{x[-4:]}"


def mask_partial(x: Any) -> Any:
	if not isinstance(x, str) or len(x) <= 4:
		return "***"
	return f"{x[:2]}***{x[-2:]}"


# =============================================================================
# OPERATIONS
# =============================================================================

NORMALIZATION_OPERATIONS = {
	"trim": lambda x: x.strip() if isinstance(x, str) else x,
	"lowercase": lambda x: x.lower() if isinstance(x, str) else x,
	"uppercase": lambda x: x.upper() if isinstance(x, str) else x,
	"casefold": lambda x: x.casefold() if isinstance(x, str) else x,
	"title_case": lambda x: x.title() if isinstance(x, str) else x,
	"slug": lambda x: (
		re.sub(r"[^\w\s-]", "", x).strip().lower().replace(" ", "-") if isinstance(x, str) else x
	),
	"snake_case": lambda x: (
		re.sub(r"[^\w\s]", "", x).strip().lower().replace(" ", "_") if isinstance(x, str) else x
	),
	"remove_spaces": lambda x: x.replace(" ", "") if isinstance(x, str) else x,
	"remove_extra_spaces": lambda x: re.sub(r"\s+", " ", x).strip() if isinstance(x, str) else x,
	"remove_punctuation": lambda x: re.sub(r"[^\w\s]", "", x) if isinstance(x, str) else x,
	"remove_numbers": lambda x: re.sub(r"\d+", "", x) if isinstance(x, str) else x,
	"numeric_only": lambda x: re.sub(r"\D", "", x) if isinstance(x, str) else x,
	"alphanumeric_only": lambda x: re.sub(r"[^\w]", "", x) if isinstance(x, str) else x,
	"unicode_normalize": lambda x: unicodedata.normalize("NFKD", x) if isinstance(x, str) else x,
	"remove_diacritics": remove_diacritics,
	"translate_chars": lambda x: x.translate(TRANSLATION_TABLE) if isinstance(x, str) else x,
	"phone_normalize": phone_normalize,
	"email_normalize": email_normalize,
	"name_normalize": lambda x: " ".join([w.capitalize() for w in x.split()]) if isinstance(x, str) else x,
	"currency_to_number": lambda x: re.sub(r"[^\d.]", "", x) if isinstance(x, str) else x,
	"tax_id_clean": lambda x: re.sub(r"[\s-]", "", x) if isinstance(x, str) else x,
	"standard_date": lambda x: str(frappe.utils.getdate(x)) if x else x,
	"mask_email": mask_email,
	"mask_phone": mask_phone,
	"mask_credit_card": mask_credit_card,
	"mask_partial": mask_partial,
}

# =============================================================================
# PROFILES
# =============================================================================

NORMALIZATION_PROFILES = {
	"URL Safe": ["trim", "lowercase", "slug"],
	"Clean Text": ["trim", "remove_extra_spaces"],
	"Upper Case Token": ["trim", "uppercase", "remove_spaces"],
	"Arabic Normalization": ["trim", "unicode_normalize", "translate_chars", "remove_extra_spaces"],
	"Arabic Strict": [
		"trim",
		"unicode_normalize",
		"translate_chars",
		"remove_punctuation",
		"remove_extra_spaces",
	],
	"Phone Number": ["phone_normalize"],
	"Email Address": ["trim", "lowercase", "email_normalize"],
	"Person Name": ["trim", "name_normalize", "remove_extra_spaces"],
	"Mask Email": ["mask_email"],
	"Mask Phone": ["mask_phone"],
	"Mask Credit Card": ["mask_credit_card"],
	"Mask Partial": ["mask_partial"],
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
