# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.document_action import (
	DocumentActionHandler,
	_async_create_doc,
)


class TestDocumentActionPhase1(FrappeTestCase):
	"""Test Phase 1 Document Action contracts, validation, and execution semantics."""

	def setUp(self):
		self.handler = DocumentActionHandler()

	def test_get_action_contract_and_operation_policies(self):
		"""Verify operation policies for all five operations in ActionContract."""
		contract = self.handler.get_action_contract()
		policies = contract.operation_policies

		self.assertEqual(
			contract.operation_options,
			["Create New", "Update Existing", "Delete Record", "Create ToDo", "Add Comment"],
		)

		# Create New
		self.assertIn("Create New", policies)
		self.assertTrue(policies["Create New"]["require_return_type"])

		# Update Existing
		self.assertIn("Update Existing", policies)
		self.assertTrue(policies["Update Existing"]["require_return_type"])

		# Delete Record
		self.assertIn("Delete Record", policies)
		self.assertFalse(policies["Delete Record"]["supports_return_schema"])
		self.assertEqual(policies["Delete Record"]["default_return_type"], "Yes / No")

		# Create ToDo
		self.assertIn("Create ToDo", policies)
		self.assertEqual(policies["Create ToDo"]["required_config_keys"], ["assigned_to", "description"])

		# Add Comment
		self.assertIn("Add Comment", policies)
		self.assertEqual(policies["Add Comment"]["required_config_keys"], ["comment_text"])

	def test_get_operation_contracts_overrides(self):
		"""Verify operation contracts do not mandate reference_docname for Add Comment."""
		op_contracts = self.handler.get_operation_contracts()

		# Add Comment operation contract must not require reference_docname
		add_comment_overrides = op_contracts["Add Comment"].action_overrides
		comment_ref_docname = next(
			(row for row in add_comment_overrides if row.get("fieldname") == "reference_docname"), None
		)
		self.assertIsNone(comment_ref_docname)

		comment_ref_doctype = next(
			(row for row in add_comment_overrides if row.get("fieldname") == "reference_doctype"), None
		)
		self.assertIsNotNone(comment_ref_doctype)
		assert comment_ref_doctype is not None
		self.assertEqual(comment_ref_doctype.get("default"), "Comment")

		# Create ToDo operation contract
		todo_ref_doctype = next(
			(
				row
				for row in op_contracts["Create ToDo"].action_overrides
				if row.get("fieldname") == "reference_doctype"
			),
			None,
		)
		self.assertIsNotNone(todo_ref_doctype)
		assert todo_ref_doctype is not None
		self.assertEqual(todo_ref_doctype.get("default"), "ToDo")

	def test_validate_add_comment_and_todo(self):
		"""Validate Add Comment and Create ToDo config validation."""
		action_comment = frappe._dict(
			{
				"operation": "Add Comment",
				"reference_doctype": "Comment",
				"config": json.dumps({"comment_text": "Test Comment"}),
			}
		)
		errors = self.handler.validate(action_comment, {})
		self.assertEqual(errors, [])

		# Missing comment_text
		action_comment_invalid = frappe._dict(
			{
				"operation": "Add Comment",
				"reference_doctype": "Comment",
				"config": json.dumps({}),
			}
		)
		errors = self.handler.validate(action_comment_invalid, {})
		self.assertTrue(any("comment_text" in err for err in errors))

		# Create ToDo valid
		action_todo = frappe._dict(
			{
				"operation": "Create ToDo",
				"reference_doctype": "ToDo",
				"config": json.dumps({"assigned_to": "Administrator", "description": "Task"}),
			}
		)
		errors = self.handler.validate(action_todo, {})
		self.assertEqual(errors, [])

	def test_update_and_delete_target_docname_resolution_precedence(self):
		"""Test target record docname resolution precedence for Update/Delete."""
		context = {"doc": frappe._dict({"name": "DOC-123"}), "vars": {"target_id": "VAR-456"}}

		# 1. Action reference_docname takes top priority
		action1 = frappe._dict({"reference_docname": "DOC-STATIC"})
		config1 = {"docname_expression": "vars.target_id", "docname": "DOC-LITERAL"}
		resolved1 = self.handler._resolve_target_docname(action1, config1, context)
		self.assertEqual(resolved1, "DOC-STATIC")

		# 2. Config docname_expression takes second priority
		action2 = frappe._dict({"reference_docname": ""})
		config2 = {"docname_expression": "vars.target_id", "docname": "DOC-LITERAL"}
		resolved2 = self.handler._resolve_target_docname(action2, config2, context)
		self.assertEqual(resolved2, "VAR-456")

		# 3. Config docname takes third priority
		action3 = frappe._dict({"reference_docname": ""})
		config3 = {"docname": "DOC-LITERAL"}
		resolved3 = self.handler._resolve_target_docname(action3, config3, context)
		self.assertEqual(resolved3, "DOC-LITERAL")

	def test_resolve_text_template_jinja_and_expressions(self):
		"""Test _resolve_text_template handles both {expression} and {{ Jinja }} syntax."""
		context = {
			"doc": frappe._dict({"first_name": "Alice", "title": "Manager"}),
			"vars": {"score": 95},
		}

		# Expression syntax
		res1 = self.handler._resolve_text_template("User {doc.first_name} is score {vars.score}", context)
		self.assertEqual(res1, "User Alice is score 95")

		# Jinja syntax
		res2 = self.handler._resolve_text_template("Hello {{ doc.first_name }} ({{ doc.title }})", context)
		self.assertEqual(res2, "Hello Alice (Manager)")

		# Hybrid syntax
		res3 = self.handler._resolve_text_template("Task for {doc.first_name}: {{ vars.score }} pts", context)
		self.assertEqual(res3, "Task for Alice: 95 pts")

	def test_add_comment_execution(self):
		"""Test Add Comment executes and attaches to current context doc."""
		test_doc = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test ToDo for Comment",
				"allocated_to": "Administrator",
			}
		).insert(ignore_permissions=True)
		self.addCleanup(test_doc.delete, ignore_permissions=True)

		context = {"doc": test_doc, "vars": {"user_note": "Great progress"}}
		config = {"comment_text": "Note: {vars.user_note} on {{ doc.name }}"}

		result = self.handler._add_comment("Comment", config, context, ignore_permissions=True)
		self.assertEqual(result.get("doctype"), "Comment")
		self.assertEqual(result.get("reference_doctype"), "ToDo")
		self.assertEqual(result.get("reference_name"), test_doc.name)
		self.assertEqual(result.get("content"), f"Note: Great progress on {test_doc.name}")

	def test_async_create_new_child_table_mappings(self):
		"""Test async Create New passes table_mappings to _async_create_doc."""
		config = {
			"field_mappings": [],
			"static_values": {"description": "Async ToDo"},
			"table_mappings": [
				{
					"target_table": "items",
					"source": "vars.item_list",
					"assignments": [{"target": "item_code", "source": "item.code"}],
				}
			],
		}
		context = {"doc": None, "vars": {"item_list": [{"code": "ITEM-1"}]}}
		action = frappe._dict({"is_async": 1})

		with patch("frappe.enqueue") as mock_enqueue:
			res = self.handler._create_new(
				"ToDo", config, context, action, ignore_permissions=True, is_async=True
			)
			self.assertTrue(res.get("enqueued"))
			mock_enqueue.assert_called_once()
			_, kwargs = mock_enqueue.call_args
			self.assertEqual(kwargs.get("table_mappings"), config["table_mappings"])
			self.assertEqual(kwargs.get("context"), context)

		# Verify _async_create_doc function
		with patch(
			"flexirule.ruleflow.core.action_handlers.document_action.DocumentActionHandler._apply_table_mappings"
		) as mock_apply:
			with patch("frappe.get_doc") as mock_get_doc:
				mock_doc = frappe._dict({"insert": lambda ignore_permissions: None, "as_dict": lambda: {}})
				mock_get_doc.return_value = mock_doc
				table_maps: list = list(config["table_mappings"])
				_async_create_doc(
					{"doctype": "ToDo"},
					table_mappings=table_maps,
					context=context,
					ignore_permissions=True,
				)
				mock_apply.assert_called_once_with(mock_doc, table_maps, context)
