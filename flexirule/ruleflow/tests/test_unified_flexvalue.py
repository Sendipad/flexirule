# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from decimal import Decimal
from typing import Any

from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.condition_errors import ConditionValidationError
from flexirule.ruleflow.core.value_resolver import (
	CanonicalVariableResolver,
	CompiledResolver,
	StaticResolver,
	ValueResolver,
)


class TestUnifiedFlexValueArchitecture(FrappeTestCase):
	def test_frappe_native_value_types_static(self):
		# Static Int
		compiled = ValueResolver.compile_flex_value({"mode": "static", "value_type": "Int", "value": 42})
		self.assertIsInstance(compiled, StaticResolver)
		self.assertEqual(compiled.resolve({}), 42)

		# Static Float / Currency / Percent
		compiled = ValueResolver.compile_flex_value(
			{"mode": "static", "value_type": "Currency", "value": "150.75"}
		)
		self.assertEqual(compiled.resolve({}), Decimal("150.75"))

		# Static Check (0 or 1)
		compiled = ValueResolver.compile_flex_value({"mode": "static", "value_type": "Check", "value": 1})
		self.assertEqual(compiled.resolve({}), 1)

		# Invalid Check (e.g. string "yes") should raise
		with self.assertRaises(ConditionValidationError):
			ValueResolver.compile_flex_value({"mode": "static", "value_type": "Check", "value": "yes"})

		# Extended Frappe Fieldtypes
		compiled_phone = ValueResolver.compile_flex_value(
			{"mode": "static", "value_type": "Phone", "value": "+1234567890"}
		)
		self.assertEqual(compiled_phone.resolve({}), "+1234567890")

		compiled_rating = ValueResolver.compile_flex_value(
			{"mode": "static", "value_type": "Rating", "value": "0.8"}
		)
		self.assertEqual(compiled_rating.resolve({}), "0.8")

	def test_canonical_variable_resolution(self):
		payload = {
			"mode": "variable",
			"path": {"scope": "doc", "segments": ["customer", "name"]},
		}
		compiled = ValueResolver.compile_flex_value(payload)
		self.assertIsInstance(compiled, CanonicalVariableResolver)
		ctx: dict[str, Any] = {"doc": {"customer": {"name": "Acme Corp"}}}
		self.assertEqual(compiled.resolve(ctx), "Acme Corp")

	def test_unified_resolver_execution(self):
		# Math formula
		payload = {
			"mode": "resolver",
			"family": "math",
			"operation": "formula",
			"value_type": "Float",
			"config": {
				"field_a": "doc.qty",
				"math_op": "*",
				"field_b_type": "constant",
				"constant_b": 5,
				"precision": 2,
			},
		}
		compiled = ValueResolver.compile_flex_value(payload)
		ctx_math: dict[str, Any] = {"doc": {"qty": 10}}
		self.assertEqual(compiled.resolve(ctx_math), 50.0)

		# Text combine
		payload = {
			"mode": "resolver",
			"family": "text",
			"operation": "combine",
			"value_type": "Data",
			"config": {
				"str_a": "doc.first_name",
				"str_a_type": "field",
				"str_b": " Smith",
				"str_b_type": "constant",
			},
		}
		compiled = ValueResolver.compile_flex_value(payload)
		ctx_text: dict[str, Any] = {"doc": {"first_name": "John"}}
		self.assertEqual(compiled.resolve(ctx_text), "John Smith")

	def test_unknown_resolver_fails_closed(self):
		payload = {
			"mode": "resolver",
			"family": "unknown_family",
			"operation": "unknown_op",
			"config": {},
		}
		with self.assertRaises(ConditionValidationError):
			ValueResolver.compile_flex_value(payload)

	def test_builtin_resolver_exact_validation(self):
		# Invalid math operator
		bad_math = {
			"mode": "resolver",
			"family": "math",
			"operation": "formula",
			"value_type": "Float",
			"config": {
				"field_a": "doc.qty",
				"math_op": "%",  # Invalid op
			},
		}
		with self.assertRaises(ConditionValidationError) as cm:
			ValueResolver.compile_flex_value(bad_math)
		self.assertEqual(cm.exception.code, "invalid_math_op")

		# Unknown config key in math formula
		bad_keys = {
			"mode": "resolver",
			"family": "math",
			"operation": "formula",
			"value_type": "Float",
			"config": {
				"field_a": "doc.qty",
				"math_op": "+",
				"unsupported_key": 123,
			},
		}
		with self.assertRaises(ConditionValidationError) as cm:
			ValueResolver.compile_flex_value(bad_keys)
		self.assertEqual(cm.exception.code, "unknown_key")

	def test_short_circuit_and_lazy_evaluation(self):
		invocations = 0

		class CountingResolver(CompiledResolver):
			def resolve(self, ctx):
				nonlocal invocations
				invocations += 1
				return 100

		ValueResolver.register_resolver(
			family="test_short_circuit",
			operation="get_val",
			label="Test Short Circuit",
			output_type="Int",
			config_schema={"type": "object"},
			permission_policy="no_data_access",
			validate_config=lambda cfg, path, scopes, rdepth, fdepth: None,
			factory=lambda cfg, meta: CountingResolver(),
			condition_operand_allowed=True,
		)

		from flexirule.ruleflow.core.condition_evaluator import evaluate_condition

		# AND group: First branch evaluates to False, second resolver branch should be SKIPPED
		payload_and = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "static", "value_type": "Check", "value": 0},
					"right": {"mode": "static", "value_type": "Check", "value": 1},
				},
				{
					"type": "comparison",
					"operator": "gt",
					"left": {
						"mode": "resolver",
						"family": "test_short_circuit",
						"operation": "get_val",
						"value_type": "Int",
						"config": {},
					},
					"right": {"mode": "static", "value_type": "Int", "value": 50},
				},
			],
		}

		res = evaluate_condition(payload_and, {})
		self.assertFalse(res)
		self.assertEqual(invocations, 0, "Resolver in AND branch was invoked despite short-circuit!")

		# OR group: First branch evaluates to True, second resolver branch should be SKIPPED
		payload_or = {
			"type": "group",
			"operator": "or",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "static", "value_type": "Check", "value": 1},
					"right": {"mode": "static", "value_type": "Check", "value": 1},
				},
				{
					"type": "comparison",
					"operator": "gt",
					"left": {
						"mode": "resolver",
						"family": "test_short_circuit",
						"operation": "get_val",
						"value_type": "Int",
						"config": {},
					},
					"right": {"mode": "static", "value_type": "Int", "value": 50},
				},
			],
		}

		res = evaluate_condition(payload_or, {})
		self.assertTrue(res)
		self.assertEqual(invocations, 0, "Resolver in OR branch was invoked despite short-circuit!")

		# When first branch does not short-circuit, resolver IS executed
		payload_exec = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "static", "value_type": "Check", "value": 1},
					"right": {"mode": "static", "value_type": "Check", "value": 1},
				},
				{
					"type": "comparison",
					"operator": "gt",
					"left": {
						"mode": "resolver",
						"family": "test_short_circuit",
						"operation": "get_val",
						"value_type": "Int",
						"config": {},
					},
					"right": {"mode": "static", "value_type": "Int", "value": 50},
				},
			],
		}

		res = evaluate_condition(payload_exec, {})
		self.assertTrue(res)
		self.assertEqual(invocations, 1, "Resolver was not executed when condition reached it!")
