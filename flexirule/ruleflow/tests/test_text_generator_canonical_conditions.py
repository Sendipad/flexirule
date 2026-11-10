# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
import unittest
from typing import Any

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.simple_actions import NotifyHandler
from flexirule.ruleflow.core.condition_errors import ConditionValidationError
from flexirule.ruleflow.doctype.rule.rule import Rule


class TestTextGeneratorCanonicalConditions(FrappeTestCase):
	"""Focused test suite for TextGenerator canonical condition segment compilation and render-time evaluation."""

	def setUp(self):
		self.rule = frappe.new_doc("Rule")
		self.rule.rule_name = "Test TextGen Canonical"
		self.rule.document_type = "ToDo"
		self.handler = NotifyHandler()

	def test_if_elif_else_branching(self):
		segments = [
			{
				"type": "conditional",
				"condition": {
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
					"right": {"mode": "static", "value_type": "Select", "value": "Open"},
				},
				"then_segments": [{"type": "text", "content": "Status is Open"}],
				"elif_branches": [
					{
						"condition": {
							"type": "comparison",
							"operator": "eq",
							"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
							"right": {"mode": "static", "value_type": "Select", "value": "Closed"},
						},
						"segments": [{"type": "text", "content": "Status is Closed"}],
					}
				],
				"else_segments": [{"type": "text", "content": "Status is Unknown"}],
			}
		]

		registry: dict[str, dict] = {}
		compiled_jinja = self.rule._compile_segments_v2(segments, "Test Action", condition_registry=registry)
		self.assertEqual(len(registry), 2)
		self.assertIn("_eval_condition(", compiled_jinja)

		# Render with Open status
		context: dict[str, Any] = {
			"doc": {"status": "Open", "doctype": "ToDo"},
			"_condition_registry": registry,
		}
		rendered = frappe.render_template(compiled_jinja, self.handler._build_template_context(context))
		self.assertEqual(rendered.strip(), "Status is Open")

		# Render with Closed status
		context_closed = {"doc": {"status": "Closed", "doctype": "ToDo"}, "_condition_registry": registry}
		rendered_closed = frappe.render_template(
			compiled_jinja, self.handler._build_template_context(context_closed)
		)
		self.assertEqual(rendered_closed.strip(), "Status is Closed")

		# Render with Other status (Else branch)
		context_other = {"doc": {"status": "Cancelled", "doctype": "ToDo"}, "_condition_registry": registry}
		rendered_other = frappe.render_template(
			compiled_jinja, self.handler._build_template_context(context_other)
		)
		self.assertEqual(rendered_other.strip(), "Status is Unknown")

	def test_conditions_inside_loops_with_iteration_values(self):
		segments = [
			{
				"type": "loop",
				"iterator": "row",
				"iterable": "vars.rows",
				"segments": [
					{
						"type": "conditional",
						"condition": {
							"type": "comparison",
							"operator": "gt",
							"left": {"mode": "variable", "path": {"scope": "row", "segments": ["qty"]}},
							"right": {"mode": "static", "value_type": "Int", "value": 15},
						},
						"then_segments": [{"type": "text", "content": "[HIGH: {{ row.qty }}]"}],
						"else_segments": [{"type": "text", "content": "[LOW: {{ row.qty }}]"}],
					}
				],
			}
		]

		rule_no_dt = frappe.new_doc("Rule")
		rule_no_dt.rule_name = "Test Generic Loop"
		registry: dict[str, dict] = {}
		compiled_jinja = rule_no_dt._compile_segments_v2(
			segments, "Test Loop Action", condition_registry=registry
		)
		self.assertIn("row=row", compiled_jinja)

		rows = [
			{"qty": 10},
			{"qty": 20},
			{"qty": 5},
			{"qty": 30},
		]
		context: dict[str, Any] = {"vars": {"rows": rows}, "_condition_registry": registry}
		rendered = frappe.render_template(compiled_jinja, self.handler._build_template_context(context))
		self.assertEqual(rendered.strip(), "[LOW: 10][HIGH: 20][LOW: 5][HIGH: 30]")

	def test_missing_condition_id_raises_explicit_error(self):
		context: dict[str, Any] = {"doc": {}, "_condition_registry": {}}
		jinja_ctx = self.handler._build_template_context(context)

		with self.assertRaises(ConditionValidationError) as raised:
			frappe.render_template('{% if _eval_condition("non_existent_id") %}YES{% endif %}', jinja_ctx)
		self.assertEqual(raised.exception.code, "missing_template_condition")

	def test_unsupported_condition_ast_rejected_at_compile_time(self):
		segments = [
			{
				"type": "conditional",
				"condition": {"invalid": "shape"},
				"then_segments": [{"type": "text", "content": "Text"}],
			}
		]
		with self.assertRaises(ConditionValidationError) as raised:
			self.rule._compile_segments_v2(segments, "Action With Bad Condition")
		self.assertEqual(raised.exception.code, "unsupported_template_condition")

	def test_nested_conditionals_and_multiple_independent_conditions(self):
		segments = [
			{
				"type": "conditional",
				"condition": {
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "vars", "segments": ["flag_a"]}},
					"right": {"mode": "static", "value_type": "Check", "value": 1},
				},
				"then_segments": [
					{"type": "text", "content": "A_TRUE "},
					{
						"type": "conditional",
						"condition": {
							"type": "comparison",
							"operator": "eq",
							"left": {"mode": "variable", "path": {"scope": "vars", "segments": ["flag_b"]}},
							"right": {"mode": "static", "value_type": "Check", "value": 1},
						},
						"then_segments": [{"type": "text", "content": "B_TRUE"}],
						"else_segments": [{"type": "text", "content": "B_FALSE"}],
					},
				],
				"else_segments": [{"type": "text", "content": "A_FALSE"}],
			}
		]

		registry: dict[str, dict] = {}
		compiled = self.rule._compile_segments_v2(segments, "Nested Action", condition_registry=registry)
		self.assertEqual(len(registry), 2)

		ctx_a_true_b_true = {"vars": {"flag_a": 1, "flag_b": 1}, "_condition_registry": registry}
		res1 = frappe.render_template(compiled, self.handler._build_template_context(ctx_a_true_b_true))
		self.assertEqual(res1.strip(), "A_TRUE B_TRUE")

		ctx_a_true_b_false = {"vars": {"flag_a": 1, "flag_b": 0}, "_condition_registry": registry}
		res2 = frappe.render_template(compiled, self.handler._build_template_context(ctx_a_true_b_false))
		self.assertEqual(res2.strip(), "A_TRUE B_FALSE")

		ctx_a_false = {"vars": {"flag_a": 0, "flag_b": 1}, "_condition_registry": registry}
		res3 = frappe.render_template(compiled, self.handler._build_template_context(ctx_a_false))
		self.assertEqual(res3.strip(), "A_FALSE")

	def test_multiple_render_isolation(self):
		registry1: dict[str, dict] = {}
		segments1 = [
			{
				"type": "conditional",
				"condition": {
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "vars", "segments": ["val"]}},
					"right": {"mode": "static", "value_type": "Data", "value": "FIRST"},
				},
				"then_segments": [{"type": "text", "content": "FIRST_MATCH"}],
			}
		]
		tmpl1 = self.rule._compile_segments_v2(segments1, "Action 1", condition_registry=registry1)

		registry2: dict[str, dict] = {}
		segments2 = [
			{
				"type": "conditional",
				"condition": {
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "vars", "segments": ["val"]}},
					"right": {"mode": "static", "value_type": "Data", "value": "SECOND"},
				},
				"then_segments": [{"type": "text", "content": "SECOND_MATCH"}],
			}
		]
		tmpl2 = self.rule._compile_segments_v2(segments2, "Action 2", condition_registry=registry2)

		# Render 1 using its registry
		ctx1 = {"vars": {"val": "FIRST"}, "_condition_registry": registry1}
		res1 = frappe.render_template(tmpl1, self.handler._build_template_context(ctx1))
		self.assertEqual(res1.strip(), "FIRST_MATCH")

		# Render 2 using its registry
		ctx2 = {"vars": {"val": "SECOND"}, "_condition_registry": registry2}
		res2 = frappe.render_template(tmpl2, self.handler._build_template_context(ctx2))
		self.assertEqual(res2.strip(), "SECOND_MATCH")

		# Render 1 fails if supplied registry 2 because cond_id is isolated
		ctx_mismatch = {"vars": {"val": "FIRST"}, "_condition_registry": registry2}
		with self.assertRaises(ConditionValidationError):
			frappe.render_template(tmpl1, self.handler._build_template_context(ctx_mismatch))

	def test_loop_with_custom_iterator_and_doctype_metadata(self):
		"""Verify loop with custom alias validates condition against child DocType metadata."""
		rule = frappe.new_doc("Rule")
		rule.name = "Test Loop Custom Alias"
		rule.document_type = "User"
		segments = [
			{
				"type": "loop",
				"iterator": "user_role",
				"iterable": "doc.roles",
				"segments": [
					{
						"type": "conditional",
						"condition": {
							"type": "comparison",
							"operator": "eq",
							"left": {
								"mode": "variable",
								"path": {"scope": "user_role", "segments": ["role"]},
							},
							"right": {"mode": "static", "value_type": "Data", "value": "System Manager"},
						},
						"then_segments": [{"type": "text", "content": "Admin"}],
					}
				],
			}
		]
		cond_reg: dict[str, Any] = {}
		compiled = rule._compile_segments_v2(segments, "Action 1", condition_registry=cond_reg)
		self.assertIn("{% for user_role in doc.roles %}", compiled)
		self.assertEqual(len(cond_reg), 1)

	def test_loop_invalid_iterator_name_rejected(self):
		"""Verify loop iterator with invalid or reserved identifier throws an error."""
		rule = frappe.new_doc("Rule")
		rule.name = "Test Loop Invalid Iter"
		rule.document_type = "User"
		segments = [
			{
				"type": "loop",
				"iterator": "doc",  # Reserved alias
				"iterable": "doc.roles",
				"segments": [{"type": "text", "content": "Hi"}],
			}
		]
		with self.assertRaises(frappe.exceptions.ValidationError):
			rule._compile_segments_v2(segments, "Action 1")
