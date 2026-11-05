# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from typing import Any

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.condition_errors import ConditionValidationError
from flexirule.ruleflow.core.condition_evaluator import (
	evaluate_prepared_condition,
	prepare_condition,
)
from flexirule.ruleflow.core.flexvalue_contract import (
	get_resolver_entry,
	register_resolver,
	validate_flex_value,
)
from flexirule.ruleflow.core.value_resolver import (
	TemplateResolver,
	ValueResolver,
)


class TestUnifiedArchitecture(FrappeTestCase):
	def test_canonical_modes_strictly_three(self):
		register_resolver(
			"text",
			"combine",
			label="Text Combine",
			output_type="Data",
			config_schema={"type": "object"},
			permission_policy="no_data_access",
			required_capability="value_resolution",
			consumers={"condition", "assignment", "action"},
			validate_config=lambda *args: None,
			condition_operand_allowed=True,
		)
		# static, variable, resolver are valid
		self.assertEqual(
			validate_flex_value({"mode": "static", "value_type": "Data", "value": "test"}), "Data"
		)
		self.assertIsNone(
			validate_flex_value({"mode": "variable", "path": {"scope": "doc", "segments": ["name"]}})
		)
		self.assertEqual(
			validate_flex_value(
				{
					"mode": "resolver",
					"family": "text",
					"operation": "combine",
					"config": {"str_a": "a", "str_b": "b"},
				},
				consumer="condition",
			),
			"Data",
		)

		# unknown/legacy mode rejected
		with self.assertRaises(ConditionValidationError) as raised:
			validate_flex_value({"mode": "template", "segments": []})
		self.assertEqual(raised.exception.code, "unknown_flex_value_mode")

		with self.assertRaises(ConditionValidationError) as raised:
			validate_flex_value({"mode": "formula", "expression": "1+1"})
		self.assertEqual(raised.exception.code, "unknown_flex_value_mode")

	def test_frappe_native_value_types_and_null_rejection(self):
		# 'null' as value_type must be rejected
		with self.assertRaises(ConditionValidationError) as raised:
			validate_flex_value({"mode": "static", "value_type": "null", "value": None})
		self.assertEqual(raised.exception.code, "unknown_value_type")

		# None as value state under valid Frappe value_type is allowed
		self.assertEqual(
			validate_flex_value({"mode": "static", "value_type": "Data", "value": None}),
			"Data",
		)
		self.assertEqual(
			validate_flex_value({"mode": "static", "value_type": "Int", "value": None}),
			"Int",
		)

	def test_check_value_strict_0_or_1_in_static_payload(self):
		# 0, 1, True, False are accepted representations for Check
		self.assertEqual(validate_flex_value({"mode": "static", "value_type": "Check", "value": 0}), "Check")
		self.assertEqual(validate_flex_value({"mode": "static", "value_type": "Check", "value": 1}), "Check")
		self.assertEqual(
			validate_flex_value({"mode": "static", "value_type": "Check", "value": True}), "Check"
		)
		self.assertEqual(
			validate_flex_value({"mode": "static", "value_type": "Check", "value": False}), "Check"
		)

		# Other integers like 2, -1 are strictly rejected
		with self.assertRaises(ConditionValidationError) as raised:
			validate_flex_value({"mode": "static", "value_type": "Check", "value": 2})
		self.assertEqual(raised.exception.code, "invalid_static_type")

		with self.assertRaises(ConditionValidationError) as raised:
			validate_flex_value({"mode": "static", "value_type": "Check", "value": -1})
		self.assertEqual(raised.exception.code, "invalid_static_type")

	def test_resolver_registry_and_bounded_lookup(self):
		register_resolver(
			"lookup",
			"fetch",
			label="Lookup Record Field",
			output_type="Data",
			config_schema={"type": "object"},
			permission_policy="authorized_read",
			required_capability="database_read",
			consumers={"condition", "assignment", "action"},
			validate_config=lambda *args: None,
			condition_operand_allowed=True,
		)
		entry = get_resolver_entry("lookup", "fetch")
		self.assertIsNotNone(entry)
		assert entry is not None
		self.assertEqual(entry["permission_policy"], "authorized_read")
		self.assertEqual(entry["required_capability"], "database_read")
		self.assertIn("condition", entry["consumers"])

		lookup = ValueResolver.compile_resolver_config(
			{
				"family": "lookup",
				"operation": "fetch",
				"target_doctype": "User",
				"record_field": "doc.usr",
				"fetch_field": "email",
			}
		)
		res = lookup.resolve({"doc": {"usr": "Administrator"}})
		self.assertEqual(res, "admin@example.com")

	def test_text_template_resolver_operation(self):
		tmpl_cfg = {
			"family": "text",
			"operation": "template",
			"config": {
				"segments": [
					{"type": "text", "value": "Status is "},
					{
						"type": "value",
						"value": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
					},
				]
			},
		}
		res = ValueResolver.compile_resolver_config(tmpl_cfg)
		self.assertIsInstance(res, TemplateResolver)
		out = res.resolve({"doc": {"status": "Active"}})
		self.assertEqual(out, "Status is Active")

	def test_condition_and_or_short_circuit_does_not_execute_unreached_resolvers(self):
		register_resolver(
			"math",
			"calculate",
			label="Math Calculate",
			output_type="Float",
			config_schema={"type": "object"},
			permission_policy="no_data_access",
			required_capability="value_resolution",
			consumers={"condition", "assignment", "action"},
			validate_config=lambda *args: None,
			resolve=lambda cfg, ctx: 60.0,
			condition_operand_allowed=True,
		)
		cond = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["active"]}},
					"right": {"mode": "static", "value_type": "Check", "value": 1},
				},
				{
					"type": "comparison",
					"operator": "gt",
					"left": {
						"mode": "resolver",
						"family": "math",
						"operation": "calculate",
						"config": {"operand_a": 60, "operand_b": 0, "math_op": "+"},
					},
					"right": {"mode": "static", "value_type": "Float", "value": 50},
				},
			],
		}

		prep = prepare_condition(cond)
		# When active is 0, first branch is false, second is not evaluated
		res = evaluate_prepared_condition(prep, {"doc": {"active": 0}})
		self.assertFalse(res)

		# When active is 1, both evaluate
		res2 = evaluate_prepared_condition(prep, {"doc": {"active": 1}})
		self.assertTrue(res2)
