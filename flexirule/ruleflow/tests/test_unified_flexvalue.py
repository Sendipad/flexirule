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

		# Frappe Duration is represented as integer seconds, not datetime.time.
		compiled = ValueResolver.compile_flex_value(
			{"mode": "static", "value_type": "Duration", "value": 3600}
		)
		self.assertEqual(compiled.resolve({}), 3600)

		# Invalid Check (e.g. string "yes") should raise
		with self.assertRaises(ConditionValidationError):
			ValueResolver.compile_flex_value({"mode": "static", "value_type": "Check", "value": "yes"})

	def test_configuration_derived_resolver_output_types(self):
		current_datetime = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "current",
			"config": {"token": "datetime"},
		}
		current_time = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "current",
			"config": {"token": "time"},
		}
		role_check = {
			"mode": "resolver",
			"family": "system_context",
			"operation": "get",
			"config": {"sys_token": "role_check", "sys_role": "System Manager"},
		}
		self.assertEqual(ValueResolver.validate_flex_value(current_datetime), "Datetime")
		self.assertEqual(ValueResolver.validate_flex_value(current_time), "Time")
		self.assertEqual(ValueResolver.validate_flex_value(role_check), "boolean")

		mismatched = {**current_datetime, "value_type": "Date"}
		with self.assertRaises(ConditionValidationError) as raised:
			ValueResolver.validate_flex_value(mismatched)
		self.assertEqual(raised.exception.code, "resolver_output_type_mismatch")

		dynamic_source = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "calculate",
			"config": {
				"source": {"mode": "variable", "path": {"scope": "doc", "segments": ["due_at"]}},
			},
		}
		self.assertIsNone(ValueResolver.validate_flex_value(dynamic_source))

		date_plus_hours = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "calculate",
			"config": {
				"source": {"mode": "static", "value_type": "Date", "value": "2026-11-23"},
				"offset_value": 2,
				"offset_unit": "hours",
			},
		}
		self.assertEqual(ValueResolver.validate_flex_value(date_plus_hours), "Datetime")

		date_plus_zero_hours = {
			**date_plus_hours,
			"config": {**date_plus_hours["config"], "offset_value": 0},
		}
		self.assertEqual(ValueResolver.validate_flex_value(date_plus_zero_hours), "Date")

		date_plus_dynamic_hours = {
			**date_plus_hours,
			"config": {
				**date_plus_hours["config"],
				"offset_value": {
					"mode": "variable",
					"path": {"scope": "doc", "segments": ["offset"]},
				},
			},
		}
		self.assertIsNone(ValueResolver.validate_flex_value(date_plus_dynamic_hours))

		boundary_datetime = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "boundary",
			"config": {
				"source": {"mode": "static", "value_type": "Datetime", "value": "2026-11-23T10:30:00"},
			},
		}
		self.assertEqual(ValueResolver.validate_flex_value(boundary_datetime), "Datetime")

		boundary_unknown_text = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "boundary",
			"config": {
				"source": {"mode": "static", "value_type": "Data", "value": "2026-11-23"},
			},
		}
		self.assertIsNone(ValueResolver.validate_flex_value(boundary_unknown_text))

		empty_boundary = {
			"mode": "resolver",
			"family": "date_time",
			"operation": "boundary",
			"config": {},
		}
		self.assertEqual(ValueResolver.validate_flex_value(empty_boundary), "null")

		empty_system_context = {
			"mode": "resolver",
			"family": "system_context",
			"operation": "get",
			"config": {"sys_token": None},
		}
		self.assertEqual(ValueResolver.validate_flex_value(empty_system_context), "null")

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
			validate_config=lambda cfg, path, scopes, rdepth, fdepth, consumer: None,
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

	def test_condition_consumer_is_preserved_through_nested_resolver_configs(self):
		from flexirule.ruleflow.core.condition_contract import validate_condition_node

		lookup = {
			"mode": "resolver",
			"family": "lookup",
			"operation": "fetch",
			"config": {
				"doctype_mode": "static",
				"target_doctype": "User",
				"record_field": "doc.owner",
				"fetch_field": "email",
			},
		}

		def comparison(operand):
			return {
				"type": "comparison",
				"operator": "eq",
				"left": operand,
				"right": {"mode": "static", "value_type": "Data", "value": "allowed"},
			}

		# Each outer resolver is condition-approved, but nested lookup.fetch must
		# retain the condition consumer and remain denied.
		nested_values = [
			{
				"mode": "resolver",
				"family": "date_time",
				"operation": "extract",
				"config": {"source": lookup, "component": "year"},
			},
			{
				"mode": "resolver",
				"family": "date_time",
				"operation": "extract",
				"config": {
					"source": {
						"mode": "resolver",
						"family": "date_time",
						"operation": "calculate",
						"config": {"source": lookup, "offset_unit": "days"},
					},
					"component": "year",
				},
			},
			{
				"mode": "resolver",
				"family": "date_time",
				"operation": "diff",
				"config": {"start_source": lookup, "diff_unit": "days"},
			},
			{
				"mode": "resolver",
				"family": "date_time",
				"operation": "boundary",
				"config": {"source": lookup, "boundary_type": "start_of_day"},
			},
		]
		for operand in nested_values:
			with self.subTest(operand=operand), self.assertRaises(ConditionValidationError) as raised:
				validate_condition_node(comparison(operand))
			self.assertEqual(raised.exception.code, "resolver_not_allowed")

		# Templates and collection resolver predicates must apply the same policy.
		template_operand = {
			"mode": "template",
			"segments": [{"type": "value", "value": nested_values[0]}],
		}
		with self.assertRaises(ConditionValidationError) as raised:
			validate_condition_node(comparison(template_operand))
		self.assertEqual(raised.exception.code, "resolver_not_allowed")

		collection_operand = {
			"mode": "resolver",
			"family": "collection",
			"operation": "any",
			"config": {
				"source": "doc.items",
				"condition": comparison(lookup),
			},
		}
		with self.assertRaises(ConditionValidationError) as raised:
			validate_condition_node(comparison(collection_operand))
		self.assertEqual(raised.exception.code, "resolver_not_allowed")

		# Other consumers retain their own allow-list: lookup.fetch is valid when
		# nested beneath an approved resolver for the Assignment consumer.
		self.assertEqual(
			ValueResolver.validate_flex_value(nested_values[0], consumer="assignment"),
			"Int",
		)

	def test_unified_registration_invalidates_condition_registry_fingerprint(self):
		from flexirule.ruleflow.core.flexvalue_contract import resolver_registry_fingerprint

		before = resolver_registry_fingerprint()
		ValueResolver.register_resolver(
			family="test_registry_fingerprint",
			operation="resolver_added",
			label="Fingerprint test resolver",
			output_type="Data",
			config_schema={"type": "object"},
			permission_policy="no_data_access",
			validate_config=lambda cfg, path, scopes, rdepth, fdepth, consumer: None,
			factory=lambda cfg, meta: StaticResolver("fingerprint"),
			condition_operand_allowed=True,
		)
		self.assertNotEqual(resolver_registry_fingerprint(), before)

	def test_compiled_resolver_cache_is_scoped_to_consumer(self):
		from types import SimpleNamespace

		from flexirule.ruleflow.core.value_resolver import get_compiled_resolver

		action = SimpleNamespace(name="consumer_cache_test")
		lookup = {
			"mode": "resolver",
			"family": "lookup",
			"operation": "fetch",
			"config": {
				"doctype_mode": "static",
				"target_doctype": "User",
				"record_field": "doc.owner",
				"fetch_field": "email",
			},
		}

		query_resolver = get_compiled_resolver(action, "shared_operand", lookup, consumer="query_records")
		assignment_resolver = get_compiled_resolver(action, "shared_operand", lookup, consumer="assignment")
		self.assertIsNot(query_resolver, assignment_resolver)

		# A generic caller without an explicit consumer is fail-closed as well.
		with self.assertRaises(ConditionValidationError) as raised:
			ValueResolver.compile_flex_value(lookup)
		self.assertEqual(raised.exception.code, "resolver_consumer_unsupported")

		# A cached Query Records resolver must not be returned to a condition
		# consumer, which explicitly disallows lookup.fetch.
		with self.assertRaises(ConditionValidationError) as raised:
			get_compiled_resolver(action, "shared_operand", lookup, consumer="condition")
		self.assertEqual(raised.exception.code, "resolver_not_allowed")

	def test_flexvalue_validation_rejects_empty_consumer(self):
		with self.assertRaises(ConditionValidationError) as raised:
			ValueResolver.validate_flex_value(
				{"mode": "static", "value_type": "Int", "value": 1}, consumer=""
			)
		self.assertEqual(raised.exception.code, "invalid_consumer")

	def test_resolver_registration_rejects_empty_consumer_allowlist(self):
		with self.assertRaisesRegex(ValueError, "non-empty set"):
			ValueResolver.register_resolver(
				family="test_empty_consumer_allowlist",
				operation="never_allowed",
				label="Empty consumer allow-list",
				output_type="Data",
				config_schema={"type": "object"},
				permission_policy="no_data_access",
				validate_config=lambda cfg, path, scopes, rdepth, fdepth, consumer: None,
				factory=lambda cfg, meta: StaticResolver("unexpected"),
				supported_consumers=set(),
			)

	def test_condition_enabled_resolver_requires_no_data_access_policy(self):
		with self.assertRaisesRegex(ValueError, "no_data_access"):
			ValueResolver.register_resolver(
				family="test_insecure_condition",
				operation="fetch",
				label="Insecure condition resolver",
				output_type="Data",
				config_schema={"type": "object"},
				permission_policy="authorized_read",
				validate_config=lambda cfg, path, scopes, rdepth, fdepth, consumer: None,
				factory=lambda cfg, meta: StaticResolver("unexpected"),
				condition_operand_allowed=True,
			)

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
