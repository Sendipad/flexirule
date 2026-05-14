# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _


def validate_config(config_json, schema_json, mapped_fields=None):
	"""
	Validate configuration against a schema

	Args:
	    config_json (str|dict): Configuration data
	    schema_json (str): JSON Schema definition
	    mapped_fields (list): Optional list of fields provided via mapping (skip required check)
	"""
	if not schema_json:
		return

	try:
		from jsonschema import ValidationError, validate, validators
	except ImportError:
		frappe.throw(_("jsonschema library not found. Please pip install jsonschema"))

	# Parse inputs if they are strings
	config = _parse_json(config_json)
	schema = _parse_json(schema_json)

	if not schema:
		return

	# Convert Frappe fields list to standard JSON Schema if needed
	schema = frappe_fields_to_json_schema(schema)

	# Deep copy schema so we don't mutate the cached version
	import copy

	schema = copy.deepcopy(schema)

	# If fields are provided via mapping, they shouldn't trigger "Required" errors in static config
	if mapped_fields and "required" in schema:
		schema["required"] = [f for f in schema["required"] if f not in mapped_fields]
		if not schema["required"]:
			del schema["required"]

	try:
		# Validate using the custom validator
		Validator = get_custom_validator(schema)
		Validator(schema).validate(config)

	except ValidationError as e:
		frappe.throw(_("Configuration Error: {0}").format(e.message))


def get_custom_validator(schema):
	"""
	Returns a jsonschema validator class customized for FlexiRule
	(e.g., handles 0/1 for booleans)
	"""
	from jsonschema import validators

	DefaultValidator = validators.validator_for(schema)

	# Redefine the boolean type checker to allow 0 and 1 (Frappe convention)
	type_checker = DefaultValidator.TYPE_CHECKER.redefine(
		"boolean",
		lambda checker, instance: isinstance(instance, bool | int) and instance in (True, False, 0, 1),
	)

	return validators.extend(DefaultValidator, type_checker=type_checker)


def _parse_json(data):
	if isinstance(data, str):
		try:
			return json.loads(data)
		except json.JSONDecodeError:
			return {}
	return data or {}


def frappe_fields_to_json_schema(frappe_schema: dict):
	"""
	Convert Frappe-style 'fields' schema to JSON Schema
	"""
	if "type" in frappe_schema and "properties" in frappe_schema:
		return frappe_schema  # Already JSON Schema

	fields = frappe_schema.get("fields", [])
	properties = {}
	required = []

	for field in fields:
		fieldname = field.get("fieldname")
		if not fieldname:
			continue

		ftype = field.get("fieldtype")
		js_type: str | list[str] = "string"

		if ftype in ["Int", "Check"]:
			js_type = "integer"
		elif ftype in ["Float", "Percent", "Currency"]:
			js_type = "number"
		elif ftype in ["Table"]:
			js_type = "array"
		elif ftype in ["Code"]:
			js_type = ["object", "array", "string"]  # Flexible
		elif ftype in ["MultiSelect"]:
			js_type = "array"
			options = field.get("options")
			if isinstance(options, str):
				# Split newline or comma separated options
				options = [opt.strip() for opt in options.replace("\n", ",").split(",")]
			properties[fieldname] = {"type": "array", "items": {"type": "string", "enum": options}}
			if field.get("reqd"):
				required.append(fieldname)
			continue  # Skip default string mapping

		# Default mapping for other types
		properties[fieldname] = {"type": js_type}

		if field.get("reqd"):
			required.append(fieldname)

	schema = {"type": "object", "properties": properties}
	if required:
		schema["required"] = required

	return schema
