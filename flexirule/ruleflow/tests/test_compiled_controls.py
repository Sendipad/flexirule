# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_plan_cache import (
	clear_rule_action_plan_cache,
	get_rule_action_plan,
	get_rule_version_hash,
)
from flexirule.ruleflow.core.engine import RuleEngine


class TestCompiledControls(FrappeTestCase):
	def tearDown(self):
		super().tearDown()
		frappe.db.rollback()

	def _uid(self):
		return frappe.generate_hash(length=8)

	def _base_rule(self, suffix, actions, document_type="ToDo"):
		return frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": f"Test Compiled Controls {suffix}",
				"document_type": document_type,
				"trigger_type": "Callable Event",
				"trigger_event": "",
				"priority": "0",
				"is_active": 0,
				"actions": actions,
			}
		)

	def test_compile_text_generator_v2_with_condition_tree(self):
		"""Test v2 segments with condition tree objects compile to Jinja."""
		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "set_1",
				},
				{
					"action_id": "set_1",
					"action_type": "Assignment",
					"action_label": "Set Description",
					"config": json.dumps(
						[
							{
								"target": "doc.description",
								"operator": "set",
								"value": "",
								"text_generator_ui": {
									"version": 2,
									"segments": [
										{"type": "text", "content": "Hello "},
										{"type": "variable", "path": "doc.name"},
										{
											"type": "conditional",
											"condition": {
												"op": "and",
												"conditions": [
													{
														"left": {"ref": "doc.priority"},
														"op": "==",
														"right": {"value": "High"},
													}
												],
											},
											"then_segments": [{"type": "text", "content": " URGENT!"}],
											"elif_branches": [
												{
													"condition": {
														"op": "and",
														"conditions": [
															{
																"left": {"ref": "doc.priority"},
																"op": "==",
																"right": {"value": "Medium"},
															}
														],
													},
													"segments": [{"type": "text", "content": " (medium)"}],
												}
											],
											"else_segments": [{"type": "text", "content": " (low)"}],
										},
									],
								},
							}
						]
					),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
		)

		rule.insert(ignore_permissions=True)
		action = next(a for a in rule.actions if a.action_id == "set_1")
		expected = (
			"Hello {{ doc.name }}"
			"{% if doc.priority == 'High' %} URGENT!"
			"{% elif doc.priority == 'Medium' %} (medium)"
			"{% else %} (low)"
			"{% endif %}"
		)
		self.assertEqual(json.loads(action.config)[0]["value"], expected)

	def test_compile_text_generator_normalizes_shorthand_roots(self):
		"""Shorthand refs (is_pos / result.total) should normalize to doc./vars. roots."""
		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"return_variable": "result",
					"next_step_if_true": "set_1",
				},
				{
					"action_id": "set_1",
					"action_type": "Assignment",
					"action_label": "Set Remarks",
					"config": json.dumps(
						[
							{
								"target": "doc.description",
								"operator": "set",
								"value": "",
								"text_generator_ui": {
									"version": 2,
									"segments": [
										{"type": "text", "content": "Value: {{ is_pos }} / "},
										{
											"type": "conditional",
											"condition": {
												"op": "and",
												"conditions": [
													{
														"left": {"ref": "is_pos"},
														"op": "!=",
														"right": {"value": 1},
													}
												],
											},
											"then_segments": [{"type": "variable", "path": "result.total"}],
											"elif_branches": [],
											"else_segments": [],
										},
									],
								},
							}
						]
					),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
		)

		rule.validate()

		action = next(a for a in rule.actions if a.action_id == "set_1")
		config = json.loads(action.config)
		self.assertIn("{{ doc.is_pos }}", config[0]["value"])
		self.assertIn("{% if doc.is_pos != 1 %}", config[0]["value"])
		self.assertIn("{{ vars.result.total }}", config[0]["value"])

	def test_assignment_compiles_operand_and_guard_metadata(self):
		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "set_1",
				},
				{
					"action_id": "set_1",
					"action_type": "Assignment",
					"action_label": "Set Description",
					"config": json.dumps(
						[
							{
								"target": "doc.description",
								"operator": "set",
								"value_template_ui": {"mode": "static", "value": "Compiled Literal"},
								"when_condition": {
									"op": "and",
									"conditions": [
										{
											"left": {"ref": "doc.status"},
											"op": "==",
											"right": {"value": "Open"},
										}
									],
								},
							}
						]
					),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
		)

		rule.insert(ignore_permissions=True)
		action = next(a for a in rule.actions if a.action_id == "set_1")
		row = json.loads(action.config)[0]
		self.assertEqual(row.get("value_source"), "literal")
		self.assertEqual(row.get("value_literal"), "Compiled Literal")
		python_expression = row.get("pythonExpression", "")
		self.assertIn("Open", python_expression)
		self.assertIn("status", python_expression)

	def test_assignment_row_when_expression_skips_row(self):
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Initial"}).insert(ignore_permissions=True)

		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "set_1",
				},
				{
					"action_id": "set_1",
					"action_type": "Assignment",
					"action_label": "Conditional Assignment",
					"config": json.dumps(
						[
							{
								"target": "doc.description",
								"operator": "set",
								"value_template_ui": {"mode": "static", "value": "Should Not Run"},
								"when_expression": "doc.status == 'Closed'",
							},
							{
								"target": "doc.description",
								"operator": "set",
								"value_template_ui": {"mode": "static", "value": "Executed"},
							},
						]
					),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
		)
		rule.is_active = 1
		rule.insert(ignore_permissions=True)

		engine = RuleEngine(rule, execution_context={"allow_inactive_rule_test": True})
		context = engine.execute(todo)
		self.assertEqual(context.get("doc").description, "Executed")

	def test_rule_action_plan_cache_compiles_notify_and_document_action(self):
		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "notify_1",
				},
				{
					"action_id": "notify_1",
					"action_type": "Notify",
					"action_label": "Notify",
					"operation": "Toast",
					"value_template": "Hello {{ doc.name }}",
					"config": json.dumps({"subject": "Subject {{ doc.name }}"}),
					"next_step_if_true": "doc_1",
				},
				{
					"action_id": "doc_1",
					"action_type": "Document Action",
					"action_label": "Create Todo",
					"reference_doctype": "ToDo",
					"operation": "Create New",
					"return_type": "Single Record",
					"return_variable": "created_todo",
					"config": json.dumps({"static_values": {"description": "From Plan"}}),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
		)
		rule.insert(ignore_permissions=True)

		clear_rule_action_plan_cache(rule.name)
		plan = get_rule_action_plan(rule)
		compiled_actions = plan.get("actions", {})

		notify_action = next(a for a in rule.actions if a.action_id == "notify_1")
		doc_action = next(a for a in rule.actions if a.action_id == "doc_1")

		notify_plan = compiled_actions.get(notify_action.name)
		doc_plan = compiled_actions.get(doc_action.name)

		self.assertEqual(notify_plan.get("action_type"), "Notify")
		self.assertEqual(notify_plan.get("mode"), "Toast")
		self.assertEqual(notify_plan.get("message_spec", {}).get("source"), "jinja")

		self.assertEqual(doc_plan.get("action_type"), "Document Action")
		self.assertEqual(doc_plan.get("mode"), "Create New")
		self.assertEqual(doc_plan.get("reference_doctype"), "ToDo")
		self.assertEqual(doc_plan.get("config", {}).get("static_values", {}).get("description"), "From Plan")

	def test_rule_version_hash_changes_when_execution_payload_changes(self):
		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "set_1",
				},
				{
					"action_id": "set_1",
					"action_type": "Assignment",
					"action_label": "Set Description",
					"config": json.dumps(
						[
							{
								"target": "doc.description",
								"operator": "set",
								"value_template_ui": {"mode": "static", "value": "A"},
							}
						]
					),
				},
			],
		)
		rule.insert(ignore_permissions=True)
		clear_rule_action_plan_cache(rule.name)
		hash_before = get_rule_version_hash(rule)

		action = next(a for a in rule.actions if a.action_id == "set_1")
		action.config = json.dumps(
			[
				{
					"target": "doc.description",
					"operator": "set",
					"value_template_ui": {"mode": "static", "value": "B"},
				}
			]
		)
		clear_rule_action_plan_cache(rule.name)
		hash_after = get_rule_version_hash(rule)
		self.assertNotEqual(hash_before, hash_after)

	def test_compile_action_mappings_from_resource_mapper_ui(self):
		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "doc_1",
				},
				{
					"action_id": "doc_1",
					"action_type": "Document Action",
					"action_label": "Create ToDo",
					"reference_doctype": "ToDo",
					"operation": "Create New",
					"return_type": "Single Record",
					"return_variable": "created_todo",
					"config": json.dumps(
						{
							"resource_mapper_ui": {
								"version": 2,
								"mode": "field_mappings",
								"source_path": "doc",
								"copy_same_fields": True,
								"field_no_map": ["description"],
								"scalars": [
									{
										"target": "description",
										"source_type": "path",
										"path": "doc.description",
									},
									{
										"target": "priority",
										"source_type": "literal",
										"literal": "High",
									},
								],
								"tables": [],
							}
						}
					),
				},
			],
		)

		rule.insert(ignore_permissions=True)
		action = next(a for a in rule.actions if a.action_id == "doc_1")
		config = json.loads(action.config)

		self.assertEqual(config.get("static_values", {}).get("priority"), "High")
		self.assertEqual(config.get("field_mappings", [])[0]["target"], "description")
		self.assertEqual(config.get("field_mappings", [])[0]["source"], "doc.description")
		self.assertEqual(config.get("input_mapping"), {})
		self.assertEqual(config.get("table_mappings"), [])
		self.assertEqual(config.get("mapper_options", {}).get("source_path"), "doc")
		self.assertTrue(config.get("mapper_options", {}).get("copy_same_fields"))
		self.assertEqual(config.get("mapper_options", {}).get("field_no_map"), ["description"])

	def test_document_action_table_mappings_append_rows(self):
		source_phone = "+15551234567"
		source_contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Source",
				"phone_nos": [{"phone": source_phone, "is_primary_phone": 1}],
			}
		).insert(ignore_permissions=True)

		target_first_name = f"Mapped-{self._uid()}"
		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "doc_1",
				},
				{
					"action_id": "doc_1",
					"action_type": "Document Action",
					"action_label": "Create Contact",
					"reference_doctype": "Contact",
					"operation": "Create New",
					"return_type": "Single Record",
					"return_variable": "created_contact",
					"config": json.dumps(
						{
							"resource_mapper_ui": {
								"version": 2,
								"mode": "field_mappings",
								"source_path": "doc",
								"copy_same_fields": False,
								"field_no_map": [],
								"scalars": [
									{
										"target": "first_name",
										"source_type": "literal",
										"literal": target_first_name,
									}
								],
								"tables": [
									{
										"target_table": "phone_nos",
										"source_path": "doc.phone_nos",
										"item_alias": "item",
										"reset_value": True,
										"add_if_empty": False,
										"condition": "",
										"filter": "",
										"mappings": [
											{
												"target": "phone",
												"source_type": "path",
												"path": "item.phone",
											}
										],
									}
								],
							}
						}
					),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
			document_type="Contact",
		)
		rule.insert(ignore_permissions=True)
		rule.is_active = 1
		action = next(a for a in rule.actions if a.action_id == "doc_1")
		compiled_cfg = json.loads(action.config)
		self.assertTrue(compiled_cfg.get("table_mappings"))
		self.assertTrue(compiled_cfg.get("table_mappings")[0].get("assignments"))

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(source_contact, event_name="Manual Test")

		created_name = frappe.get_all(
			"Contact",
			filters={"first_name": target_first_name},
			order_by="creation desc",
			limit=1,
			pluck="name",
		)
		self.assertTrue(created_name)

		created = frappe.get_doc("Contact", created_name[0])
		self.assertTrue(created.phone_nos)
		self.assertEqual(created.phone_nos[0].phone, source_phone)

	def test_document_action_copy_same_fields_with_exclusions(self):
		source_first_name = f"Src-{self._uid()}"
		source_last_name = f"Skip-{self._uid()}"
		source_contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": source_first_name,
				"last_name": source_last_name,
			}
		).insert(ignore_permissions=True)

		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "doc_1",
				},
				{
					"action_id": "doc_1",
					"action_type": "Document Action",
					"action_label": "Clone Contact",
					"reference_doctype": "Contact",
					"operation": "Create New",
					"return_type": "Single Record",
					"return_variable": "created_contact",
					"config": json.dumps(
						{
							"resource_mapper_ui": {
								"version": 2,
								"mode": "field_mappings",
								"source_path": "doc",
								"copy_same_fields": True,
								"field_no_map": ["last_name"],
								"scalars": [],
								"tables": [],
							}
						}
					),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
			document_type="Contact",
		)
		rule.insert(ignore_permissions=True)
		rule.is_active = 1

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(source_contact, event_name="Manual Test")

		created_name = frappe.get_all(
			"Contact",
			filters={"first_name": source_first_name},
			order_by="creation desc",
			limit=1,
			pluck="name",
		)
		self.assertTrue(created_name)
		self.assertNotEqual(created_name[0], source_contact.name)

		created = frappe.get_doc("Contact", created_name[0])
		self.assertEqual(created.first_name, source_first_name)
		self.assertTrue(created.last_name in (None, ""))

	def test_jinja_format_filter_and_dict_attribute_evaluation(self):
		"""Test that uppercase/lowercase formatters and dict attribute access evaluate correctly."""
		todo = frappe.get_doc({"doctype": "ToDo", "description": "initial"}).insert(ignore_permissions=True)

		rule = self._base_rule(
			self._uid(),
			[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"next_step_if_true": "set_1",
				},
				{
					"action_id": "set_1",
					"action_type": "Assignment",
					"action_label": "Test Formatter",
					"config": json.dumps(
						[
							{
								"target": "doc.description",
								"operator": "set",
								"value": "{{ format('uppercase', {}) }}",
								"value_template": "{{ format('uppercase', {}) }}",
								"value_template_ui": {
									"mode": "template",
									"value": "{{ format('uppercase', {}) }}",
								},
							}
						]
					),
					"next_step_if_true": "stop_1",
				},
				{
					"action_id": "stop_1",
					"action_type": "Stop",
					"action_label": "Stop",
					"operation": "Success",
				},
			],
		)
		rule.is_active = 1
		rule.insert(ignore_permissions=True)

		engine = RuleEngine(rule, execution_context={"allow_inactive_rule_test": True})
		# Test with actual Document object
		context = engine.execute(todo)
		self.assertEqual(context.get("doc").description, "INITIAL")

		# Test with dictionary to verify dict dot-access wrapping
		todo_dict = {"doctype": "ToDo", "description": "lowercase text", "name": todo.name}
		context_dict = engine.execute(todo_dict)
		self.assertEqual(context_dict.get("doc").description, "LOWERCASE TEXT")
