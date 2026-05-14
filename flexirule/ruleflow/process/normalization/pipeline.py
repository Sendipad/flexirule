# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
NormalizationPipeline - Text normalization and cleaning
Applies transformation pipelines to standardize data
"""

import json
import re
from typing import Any, ClassVar

import frappe


class NormalizationPipeline:
	"""
	Executes a series of text transformations
	Used for data cleaning and standardization before comparison
	"""

	# Built-in transformations
	TRANSFORMATIONS: ClassVar[dict[str, Any]] = {
		"trim": lambda x: x.strip() if isinstance(x, str) else x,
		"lowercase": lambda x: x.lower() if isinstance(x, str) else x,
		"uppercase": lambda x: x.upper() if isinstance(x, str) else x,
		"remove_spaces": lambda x: x.replace(" ", "") if isinstance(x, str) else x,
		"remove_punctuation": lambda x: (re.sub(r"[^\w\s]", "", x) if isinstance(x, str) else x),
		"remove_extra_spaces": lambda x: (re.sub(r"\s+", " ", x).strip() if isinstance(x, str) else x),
		"remove_numbers": lambda x: re.sub(r"\d+", "", x) if isinstance(x, str) else x,
		"remove_special_chars": lambda x: (re.sub(r"[^a-zA-Z0-9\s]", "", x) if isinstance(x, str) else x),
		"slug": lambda x: (
			re.sub(r"[^\w\s-]", "", x).strip().lower().replace(" ", "-") if isinstance(x, str) else x
		),
	}

	def __init__(self, profile_name: str | None = None):
		"""
		Initialize with a normalization profile

		Args:
		        profile_name: Name of Normalization Profile document
		"""
		self.profile = None
		if profile_name:
			self.profile = frappe.get_doc("Normalization Profile", profile_name)

	def normalize_document(self, doc):
		"""
		Apply normalization to all configured fields in a document

		Args:
		        doc: Frappe document to normalize
		"""
		if not self.profile or not self.profile.normalize_fields_json:
			return

		field_configs = json.loads(self.profile.normalize_fields_json)

		for config in field_configs:
			fieldname = config.get("fieldname")
			transformations = config.get("transformations", [])

			if not fieldname or not transformations:
				continue

			# Get current value
			value = doc.get(fieldname)
			if value is None:
				continue

			# Apply transformations
			normalized = self.apply_transformations(value, transformations)

			# Set normalized value
			doc.set(fieldname, normalized)

	def apply_transformations(self, value: Any, transformations: list[str]) -> Any:
		"""
		Apply a list of transformations to a value

		Args:
		        value: Value to transform
		        transformations: List of transformation names

		Returns:
		        Transformed value
		"""
		result = value

		for transform_name in transformations:
			transform_func = self.TRANSFORMATIONS.get(transform_name)
			if transform_func:
				try:
					result = transform_func(result)
				except Exception as e:
					frappe.log_error(
						title=f"Normalization Error: {transform_name}",
						message=f"Value: {value}\\nError: {e!s}",
					)

		return result

	@staticmethod
	def normalize_text(text: str, operations: list[str] | None = None) -> str:
		"""
		Standalone normalization function

		Args:
		        text: Text to normalize
		        operations: List of operations to apply

		Returns:
		        Normalized text
		"""
		if not operations:
			operations = ["trim", "lowercase", "remove_extra_spaces"]

		pipeline = NormalizationPipeline()
		return pipeline.apply_transformations(text, operations)

	@staticmethod
	def add_custom_transformation(name: str, func):
		"""
		Register a custom transformation function

		Args:
		        name: Transformation name
		        func: Function that takes a value and returns transformed value
		"""
		NormalizationPipeline.TRANSFORMATIONS[name] = func


# Whitelisted API for testing
@frappe.whitelist()
def test_normalization(text: str, transformations: str | list):
	"""
	Test normalization transformations

	Args:
	        text: Text to normalize
	        transformations: JSON array of transformation names

	Returns:
	        Normalized text
	"""
	from flexirule.ruleflow.core.permissions import require_builder_access

	require_builder_access()

	pipeline = NormalizationPipeline()
	# Ensure transformations is a list[str] for mypy
	if isinstance(transformations, str):
		transform_list = json.loads(transformations)
	else:
		transform_list = transformations

	if not isinstance(transform_list, list):
		transform_list = [str(transform_list)]

	return pipeline.apply_transformations(text, [str(t) for t in transform_list])
