# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
FieldResolver - Smart field value resolution
Handles dot notation, child tables, and aggregate functions
"""

import json
from typing import Any

import frappe


class FieldResolver:
	"""
	Resolves field values from documents with support for:
	- Simple fields
	- Child table fields (dot notation)
	- Aggregate functions (SUM, AVG, COUNT, MAX, MIN)
	- Parent/grandparent references
	"""

	@staticmethod
	def resolve(doc, field_path: str) -> Any:
		"""
		Resolve a field value from a document

		Args:
		        doc: Frappe document
		        field_path: Field path (supports dot notation and aggregates)

		Returns:
		        Resolved value
		"""
		if doc is None or not field_path:
			return None

		# Check for aggregate functions
		if ":" in field_path:
			return FieldResolver._resolve_aggregate(doc, field_path)

		# Check for dot notation (child table or parent reference)
		if "." in field_path:
			return FieldResolver._resolve_nested(doc, field_path)

		# Simple field
		return doc.get(field_path)

	@staticmethod
	def resolve_picker(doc, picker_val: Any, context: dict | None = None) -> Any:
		"""
		Resolve value from a FieldSelector structured value:
		[source, doctype_or_key, fieldname, fieldtype, options]
		"""
		if not picker_val:
			return None

		if isinstance(picker_val, str):
			# Transparently handle old-style string fieldnames
			return FieldResolver.resolve(doc, picker_val)

		if isinstance(picker_val, list) and len(picker_val) >= 3:
			source, source_id, fieldname = picker_val[0:3]

			if source == "doctype":
				# Resolve typically from the current doc or related
				# For now we assume doctype refers to the current doc structure
				# (Or we could check if source_id matches doc.doctype)
				return FieldResolver.resolve(doc, fieldname)

			elif source == "context":
				# Resolve from context variables
				if context and "vars" in context:
					# FieldSelector uses context key as source_id
					# If the context var is a dict (DocField selection), resolve subfield
					var_val = context["vars"].get(source_id)
					if isinstance(var_val, dict) and fieldname:
						return var_val.get(fieldname)
					return var_val

		return None

	@staticmethod
	def _resolve_nested(doc, field_path: str) -> Any:
		"""
		Resolve nested field (child table or parent)

		Examples:
		        - 'items.item_code' → ['ITEM-001', 'ITEM-002']
		        - 'parent.customer_name' → 'Acme Corp'
		"""
		parts = field_path.split(".")

		# Check if first part is 'parent'
		if parts[0] == "parent" and doc.get("parent"):
			parent_doc = frappe.get_doc(doc.get("parenttype"), doc.get("parent"))
			if len(parts) == 2:
				return parent_doc.get(parts[1])
			else:
				# Multiple levels (rare but supported)
				return FieldResolver.resolve(parent_doc, ".".join(parts[1:]))

		# Child table field
		child_table_fieldname = parts[0]
		child_field = parts[1] if len(parts) > 1 else None

		# Get child table rows
		child_rows = doc.get(child_table_fieldname)
		if not child_rows:
			return []

		# If no child field specified, return all rows
		if not child_field:
			return child_rows

		# Extract values from child field
		values = [row.get(child_field) for row in child_rows if row.get(child_field) is not None]
		return values

	@staticmethod
	def _resolve_aggregate(doc, field_path: str) -> Any:
		"""
		Resolve aggregate function

		Format: 'child_table.field:function'

		Supported functions:
		        - sum: Sum of all values
		        - avg: Average of all values
		        - count: Count of non-null values
		        - max: Maximum value
		        - min: Minimum value
		        - first: First value
		        - last: Last value
		"""
		# Split path and function
		path, func = field_path.split(":")

		# Get values
		values = FieldResolver._resolve_nested(doc, path)
		if not values:
			return 0 if func in ["sum", "count"] else None

		# Filter numeric values for numeric functions
		if func in ["sum", "avg", "max", "min"]:
			values = [v for v in values if isinstance(v, int | float)]

		# Apply function
		if func == "sum":
			return sum(values)
		elif func == "avg":
			return sum(values) / len(values) if values else 0
		elif func == "count":
			return len(values)
		elif func == "max":
			return max(values) if values else None
		elif func == "min":
			return min(values) if values else None
		elif func == "first":
			return values[0] if values else None
		elif func == "last":
			return values[-1] if values else None
		else:
			frappe.log_error(f"Unknown aggregate function: {func}", "FieldResolver")
			return None

	@staticmethod
	def get_child_table_fields(doctype: str) -> list[str]:
		"""
		Get all child table fieldnames for a DocType

		Args:
		        doctype: DocType name

		Returns:
		        List of child table fieldnames
		"""
		meta = frappe.get_meta(doctype)
		return [f.fieldname for f in meta.fields if f.fieldtype == "Table"]

	@staticmethod
	def get_field_type(doctype: str, fieldname: str) -> str | None:
		"""
		Get field type for a field
		"""
		meta = frappe.get_meta(doctype)
		field = meta.get_field(fieldname)
		return str(field.fieldtype) if field else None

	@staticmethod
	def get_all_fields(doctype: str, include_child_tables: bool = False) -> list[dict]:
		"""
		Get all fields for a DocType with metadata

		Args:
		        doctype: DocType name
		        include_child_tables: Include child table fields with dot notation

		Returns:
		        List of field dictionaries
		"""
		meta = frappe.get_meta(doctype)
		fields = []

		for field in meta.fields:
			if field.fieldtype not in [
				"Section Break",
				"Column Break",
				"HTML",
				"Tab Break",
			]:
				fields.append(
					{
						"fieldname": field.fieldname,
						"label": field.label,
						"fieldtype": field.fieldtype,
						"options": field.options,
					}
				)

				# Add child table fields
				if include_child_tables and field.fieldtype == "Table" and field.options:
					child_meta = frappe.get_meta(field.options)
					for child_field in child_meta.fields:
						if child_field.fieldtype not in [
							"Section Break",
							"Column Break",
						]:
							fields.append(
								{
									"fieldname": f"{field.fieldname}.{child_field.fieldname}",
									"label": f"{field.label} → {child_field.label}",
									"fieldtype": child_field.fieldtype,
									"options": child_field.options,
									"is_child": True,
									"parent_field": field.fieldname,
								}
							)

		return fields


# Whitelisted API for UI
@frappe.whitelist()
def get_doctype_fields(doctype: str, include_child_tables: bool = False):
	"""
	Get all fields for a DocType (API endpoint)

	Args:
	        doctype: DocType name
	        include_child_tables: Include child table fields

	Returns:
	        List of field dictionaries
	"""
	from flexirule.ruleflow.core.permissions import require_builder_access

	require_builder_access()
	return FieldResolver.get_all_fields(doctype, include_child_tables)


# ============================================================
# CONFIGURATION PARSING UTILS
# ============================================================


def parse_field_list(fields) -> list[str]:
	"""Parse fields from multiple formats (list, newline, comma, JSON)"""
	if not fields:
		return []
	if isinstance(fields, list):
		return [f.strip() if isinstance(f, str) else f for f in fields]
	if isinstance(fields, str):
		fields = fields.strip()
		if fields.startswith("["):
			try:
				import json

				return json.loads(fields)
			except json.JSONDecodeError:
				pass
		if "\n" in fields:
			return [f.strip() for f in fields.split("\n") if f.strip()]
		if "," in fields:
			return [f.strip() for f in fields.split(",") if f.strip()]
		return [fields]
	return []


def parse_pattern_type(pattern_type, custom_pattern=None):
	"""Return regex pattern based on type"""
	patterns = {
		"Email": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
		"Phone": r"^\+?1?\d{9,15}$",
		"URL": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
		"Alphanumeric": r"^[a-zA-Z0-9 ]*$",
		"Numeric": r"^-?\d*\.?\d*$",
	}
	if pattern_type == "Custom Regex":
		return custom_pattern
	return patterns.get(pattern_type, custom_pattern)


def parse_field_mapping(mapping) -> dict:
	"""Parse field mapping from list of dicts (table) or JSON string"""
	if not mapping:
		return {}

	if isinstance(mapping, str):
		try:
			import json

			mapping = json.loads(mapping)
		except json.JSONDecodeError:
			return {}

	if isinstance(mapping, list):
		# Convert list of dicts to a single dict
		result = {}
		for item in mapping:
			if isinstance(item, dict):
				source = item.get("source_field")
				target = item.get("target_field")
				if source and target:
					result[source] = target
		return result

	if isinstance(mapping, dict):
		return mapping

	return {}
