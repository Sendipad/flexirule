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

	def test_variable_strictly_rejects_extra_value_property(self):
		# Finding 1: Backend strict validator rejects variable payloads containing "value"
		payload_with_value = {
			"mode": "variable",
			"path": {"scope": "doc", "segments": ["customer"]},
			"value": "doc.customer",
		}
		with self.assertRaises(ConditionValidationError) as cm:
			ValueResolver.compile_flex_value(payload_with_value)
		self.assertEqual(cm.exception.code, "unknown_key")

	def test_template_mode_compilation_and_resolution(self):
		# Finding 3: Canonical template mode with text and value segments
		payload = {
			"mode": "template",
			"segments": [
				{"type": "text", "value": "Order for: "},
				{
					"type": "value",
					"value": {
						"mode": "variable",
						"path": {"scope": "doc", "segments": ["customer_name"]},
					},
				},
				{"type": "text", "value": " is ready."},
			],
		}
		compiled = ValueResolver.compile_flex_value(payload)
		ctx = {"doc": {"customer_name": "Acme Inc"}}
		self.assertEqual(compiled.resolve(ctx), "Order for: Acme Inc is ready.")

	def test_builtin_resolvers_strict_validation(self):
		# Finding 4 & 5: Built-in resolvers reject unknown configuration keys
		payload_invalid_cfg = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "current",
			"config": {"invalid_extra_key": 123},
		}
		with self.assertRaises(ConditionValidationError) as cm:
			ValueResolver.compile_flex_value(payload_invalid_cfg)
		self.assertEqual(cm.exception.code, "unknown_key")

		# Unknown mode fails closed without silent legacy fallback
		payload_unknown_mode = {
			"mode": "unsupported_mode",
			"value": "xyz",
		}
		with self.assertRaises(ConditionValidationError) as cm:
			ValueResolver.compile_flex_value(payload_unknown_mode)
		self.assertEqual(cm.exception.code, "unknown_flex_value_mode")

	def test_frappe_fieldtype_catalogue_parity(self):
		# Finding 6: All 44 standard DocField options recognized, structural fieldtypes separated
		from flexirule.ruleflow.core.flexvalue_contract import (
			ALL_FRAPPE_FIELD_TYPES,
			FRAPPE_STRUCTURAL_FIELD_TYPES,
			FRAPPE_VALUE_TYPES,
		)

		self.assertEqual(len(ALL_FRAPPE_FIELD_TYPES), 44)
		self.assertIn("Section Break", FRAPPE_STRUCTURAL_FIELD_TYPES)
		self.assertIn("Column Break", FRAPPE_STRUCTURAL_FIELD_TYPES)
		self.assertIn("Tab Break", FRAPPE_STRUCTURAL_FIELD_TYPES)
		self.assertIn("Button", FRAPPE_STRUCTURAL_FIELD_TYPES)
		self.assertNotIn("Section Break", FRAPPE_VALUE_TYPES)
		self.assertIn("Data", FRAPPE_VALUE_TYPES)
		self.assertIn("Int", FRAPPE_VALUE_TYPES)
		self.assertIn("Float", FRAPPE_VALUE_TYPES)
		self.assertIn("Table", FRAPPE_VALUE_TYPES)

	def test_duration_representation_as_integer_seconds(self):
		# Duration represents integer seconds, excluding booleans and strings
		compiled = ValueResolver.compile_flex_value(
			{"mode": "static", "value_type": "Duration", "value": 3600}
		)
		self.assertIsInstance(compiled, StaticResolver)
		self.assertEqual(compiled.resolve({}), 3600)

		# Reject boolean
		with self.assertRaises(ConditionValidationError):
			ValueResolver.compile_flex_value(
				{"mode": "static", "value_type": "Duration", "value": True}
			)

		# Reject string ISO time
		with self.assertRaises(ConditionValidationError):
			ValueResolver.compile_flex_value(
				{"mode": "static", "value_type": "Duration", "value": "01:00:00"}
			)

	def test_check_field_strictly_accepts_integer_zero_or_one(self):
		# Integer 0 and 1 are accepted
		compiled_0 = ValueResolver.compile_flex_value(
			{"mode": "static", "value_type": "Check", "value": 0}
		)
		self.assertEqual(compiled_0.resolve({}), 0)
		compiled_1 = ValueResolver.compile_flex_value(
			{"mode": "static", "value_type": "Check", "value": 1}
		)
		self.assertEqual(compiled_1.resolve({}), 1)

		# Booleans True and False must be rejected
		with self.assertRaises(ConditionValidationError):
			ValueResolver.compile_flex_value(
				{"mode": "static", "value_type": "Check", "value": True}
			)
		with self.assertRaises(ConditionValidationError):
			ValueResolver.compile_flex_value(
				{"mode": "static", "value_type": "Check", "value": False}
			)

	def test_date_time_dynamic_resolvers_in_conditions(self):
		import frappe
		from flexirule.ruleflow.core.condition_evaluator import evaluate_condition

		# 1. date_time.current with date token
		cond_date = {
			"type": "comparison",
			"operator": "eq",
			"left": {
				"mode": "resolver",
				"family": "date_time",
				"operation": "current",
				"config": {"token": "date"},
			},
			"right": {"mode": "static", "value_type": "Date", "value": frappe.utils.nowdate()},
		}
		self.assertTrue(evaluate_condition(cond_date, {}))

		# 2. date_time.current with time token
		cond_time = {
			"type": "comparison",
			"operator": "ne",
			"left": {
				"mode": "resolver",
				"family": "date_time",
				"operation": "current",
				"config": {"token": "time"},
			},
			"right": {"mode": "static", "value_type": "Time", "value": "00:00:00"},
		}
		self.assertTrue(evaluate_condition(cond_time, {}))

		# 3. system_context.get with role_check returns boolean
		cond_role = {
			"type": "comparison",
			"operator": "eq",
			"left": {
				"mode": "resolver",
				"family": "system_context",
				"operation": "get",
				"config": {"sys_token": "role_check", "sys_role": "NonExistentRoleXYZ"},
			},
			"right": {"mode": "static", "value_type": "boolean", "value": False},
		}
		self.assertTrue(evaluate_condition(cond_role, {}))

	def test_collection_resolver_last_and_fail_closed_condition(self):
		from flexirule.ruleflow.core.value_resolver import CollectionResolver

		items = [
			{"item_code": "A", "qty": 1},
			{"item_code": "B", "qty": 2},
			{"item_code": "C", "qty": 3},
		]
		col_last = CollectionResolver(source="doc.items", operation="last")
		res = col_last.resolve({"doc": {"items": items}})
		self.assertEqual(res, {"item_code": "C", "qty": 3})

		# Strictly reject non-canonical conditions
		with self.assertRaises(ConditionValidationError):
			CollectionResolver(source="doc.items", operation="any", condition="items.qty > 0")

		with self.assertRaises(ConditionValidationError):
			CollectionResolver(
				source="doc.items",
				operation="any",
				condition={"fieldname": "qty", "operator": ">", "value": 0},
			)

	def test_resolver_registration_invariants_and_unification(self):
		import flexirule.ruleflow.core.flexvalue_contract as fvc

		# Duplicate registration rejection without allow_override
		with self.assertRaises(ValueError):
			ValueResolver.register_resolver(
				"date_time",
				"current",
				label="Duplicate Date Current",
				output_type="Date",
				config_schema={},
				permission_policy="no_data_access",
				validate_config=lambda *a: None,
				factory=lambda *a: None,
			)

		# Insecure condition operand permission policy rejection
		with self.assertRaises(ValueError):
			ValueResolver.register_resolver(
				"test_insecure",
				"read_db",
				label="Insecure",
				output_type="Data",
				config_schema={},
				permission_policy="authorized_read",
				validate_config=lambda *a: None,
				factory=lambda *a: None,
				condition_operand_allowed=True,
			)

		# Fingerprints unified
		self.assertEqual(
			ValueResolver.registry_fingerprint(),
			fvc.resolver_registry_fingerprint(),
		)
