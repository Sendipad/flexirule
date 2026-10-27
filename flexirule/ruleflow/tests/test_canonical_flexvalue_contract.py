# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

from flexirule.ruleflow.core.flexvalue_contract import (
	FlexValueError,
	validate_flexvalue,
)


class TestCanonicalFlexValueContract(unittest.TestCase):
	def test_valid_static_flexvalues(self):
		valid_cases = [
			{"mode": "static", "value_type": "string", "value": "hello"},
			{"mode": "static", "value_type": "integer", "value": 42},
			{"mode": "static", "value_type": "decimal", "value": "100.50"},
			{"mode": "static", "value_type": "boolean", "value": True},
			{"mode": "static", "value_type": "boolean", "value": False},
			{"mode": "static", "value_type": "null", "value": None},
			{"mode": "static", "value_type": "date", "value": "2026-10-26"},
			{"mode": "static", "value_type": "datetime", "value": "2026-10-26T12:00:00Z"},
			{"mode": "static", "value_type": "time", "value": "12:00:00"},
			{"mode": "static", "value_type": "list", "value": [1, 2, "a"]},
			{"mode": "static", "value_type": "object", "value": {"k": "v"}},
		]
		for case in valid_cases:
			with self.subTest(case=case):
				validate_flexvalue(case)

	def test_invalid_static_flexvalues(self):
		# Rejects boolean for integer
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue({"mode": "static", "value_type": "integer", "value": True})
		self.assertEqual(cm.exception.code, "TYPE_MISMATCH")

		# Rejects unknown key 'id'
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue({"mode": "static", "value_type": "string", "value": "x", "id": "ui-123"})
		self.assertEqual(cm.exception.code, "UNKNOWN_KEY")

		# Rejects invalid decimal string
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue({"mode": "static", "value_type": "decimal", "value": "not-a-number"})
		self.assertEqual(cm.exception.code, "INVALID_DECIMAL")

		# Rejects invalid date format
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue({"mode": "static", "value_type": "date", "value": "26-10-2026"})
		self.assertEqual(cm.exception.code, "TYPE_MISMATCH")

	def test_valid_variable_flexvalue(self):
		valid_case = {
			"mode": "variable",
			"path": {
				"scope": "doc",
				"segments": ["grand_total"],
			},
		}
		validate_flexvalue(valid_case)

	def test_invalid_variable_flexvalue(self):
		# Empty segments
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue({"mode": "variable", "path": {"scope": "doc", "segments": []}})
		self.assertEqual(cm.exception.code, "EMPTY_SEGMENTS")

		# Dunder segment
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue({"mode": "variable", "path": {"scope": "doc", "segments": ["__class__"]}})
		self.assertEqual(cm.exception.code, "FORBIDDEN_SEGMENT")

		# Segments count exceeded
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue(
				{"mode": "variable", "path": {"scope": "doc", "segments": [f"s{i}" for i in range(33)]}}
			)
		self.assertEqual(cm.exception.code, "LIMIT_EXCEEDED")

	def test_valid_resolver_flexvalue(self):
		valid_case = {
			"mode": "resolver",
			"family": "math",
			"operation": "add",
			"config": {
				"left": {"mode": "static", "value_type": "integer", "value": 10},
				"right": {"mode": "variable", "path": {"scope": "doc", "segments": ["amount"]}},
			},
		}
		validate_flexvalue(valid_case)

	def test_invalid_resolver_flexvalue(self):
		# Unknown key inside resolver
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue(
				{
					"mode": "resolver",
					"family": "math",
					"operation": "add",
					"config": {},
					"ui_id": "999",
				}
			)
		self.assertEqual(cm.exception.code, "UNKNOWN_KEY")

	def test_valid_template_flexvalue(self):
		valid_case = {
			"mode": "template",
			"segments": [
				{"type": "text", "text": "Hello "},
				{
					"type": "value",
					"value": {"mode": "variable", "path": {"scope": "doc", "segments": ["first_name"]}},
				},
			],
		}
		validate_flexvalue(valid_case)

	def test_invalid_template_flexvalue(self):
		# Unknown segment type
		with self.assertRaises(FlexValueError) as cm:
			validate_flexvalue(
				{
					"mode": "template",
					"segments": [
						{"type": "raw_python", "code": "1 + 1"},
					],
				}
			)
		self.assertEqual(cm.exception.code, "INVALID_TEMPLATE_SEGMENT")
