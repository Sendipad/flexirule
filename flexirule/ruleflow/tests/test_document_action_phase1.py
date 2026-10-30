# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.action_handlers.document_action import (
	DocumentActionHandler,
	_async_create_doc,
)
from flexirule.ruleflow.core.engine import RuleEngine


class TestDocumentActionPhase1(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.handler = DocumentActionHandler()

	def tearDown(self):
		super().tearDown()
		frappe.db.rollback()

	def _uid(self):
		return frappe.generate_hash(length=8)

	def test_operation_contracts_structure(self):
		"""Verify operation contracts and overrides for all five operations."""
		op_contracts = DocumentActionHandler.get_operation_contracts()
		self.assertIn("Create New", op_contracts)
		self.assertIn("Update Existing", op_contracts)
		self.assertIn("Delete Record", op_contracts)
		self.assertIn("Create ToDo", op_contracts)
		self.assertIn("Add Comment", op_contracts)

		# Add Comment must NOT require reference_docname in action_overrides
		comment_overrides = op_contracts["Add Comment"].action_overrides
		reqd_docname_comment = [
			f for f in comment_overrides
			if f.get("fieldname") == "reference_docname" and f.get("reqd") == 1
		]
		self.assertEqual(len(reqd_docname_comment), 0, "Add Comment should not mark reference_docname as required")

		# Check action contract policies
		action_contract = DocumentActionHandler.get_action_contract()
		policies = getattr(action_contract, "operation_policies", {})
		self.assertEqual(policies["Create ToDo"].get("required_config_keys"), ["assigned_to", "description"])
		self.assertEqual(policies["Add Comment"].get("required_config_keys"), ["comment_text"])

	def test_target_identity_precedence_update(self):
		"""Test target record identity resolution precedence for Update Existing."""
		context = {"doc": frappe._dict({"name": "CTX123", "doctype": "Contact", "first_name": "John"}), "vars": {}}

		# 1. Action reference_docname takes top precedence
		action = frappe._dict({
			"operation": "Update Existing",
			"reference_doctype": "Contact",
			"reference_docname": "DOC_DIRECT",
		})
		config = {"docname": "DOC_CONFIG", "docname_expression": "'DOC_EXPR'"}
		resolved = self.handler._resolve_target_docname(action, config, context)
		self.assertEqual(resolved, "DOC_DIRECT")

		# 2. docname_expression takes second precedence
		action = frappe._dict({
			"operation": "Update Existing",
			"reference_doctype": "Contact",
			"reference_docname": "",
		})
		resolved = self.handler._resolve_target_docname(action, config, context)
		self.assertEqual(resolved, "DOC_EXPR")

		# 3. docname takes third precedence
		config_static = {"docname": "DOC_CONFIG"}
		resolved = self.handler._resolve_target_docname(action, config_static, context)
		self.assertEqual(resolved, "DOC_CONFIG")

	def test_add_comment_jinja_rendering(self):
		"""Test Add Comment renders Jinja text templates using context document."""
		contact = frappe.get_doc({
			"doctype": "Contact",
			"first_name": f"Tester_{self._uid()}",
		}).insert(ignore_permissions=True)

		context = {"doc": contact, "vars": {}}
		config = {
			"comment_text": "Processed contact {{ doc.first_name }}",
			"comment_type": "Comment",
		}

		res = self.handler._add_comment("Comment", config, context, ignore_permissions=True)
		self.assertIsInstance(res, dict)
		self.assertEqual(res.get("reference_doctype"), "Contact")
		self.assertEqual(res.get("reference_name"), contact.name)
		self.assertIn(contact.first_name, res.get("content"))

	def test_create_todo_execution(self):
		"""Test Create ToDo attaches to context document."""
		contact = frappe.get_doc({
			"doctype": "Contact",
			"first_name": f"Tester_{self._uid()}",
		}).insert(ignore_permissions=True)

		context = {"doc": contact, "vars": {}}
		config = {
			"assigned_to": "Administrator",
			"description": "Follow up with {{ doc.first_name }}",
			"priority": "High",
		}

		res = self.handler._create_todo("ToDo", config, context, ignore_permissions=True)
		self.assertEqual(res.get("doctype"), "ToDo")
		self.assertEqual(res.get("allocated_to"), "Administrator")
		self.assertEqual(res.get("reference_type"), "Contact")
		self.assertEqual(res.get("reference_name"), contact.name)
		self.assertIn(contact.first_name, res.get("description"))

	def test_async_create_doc_worker(self):
		"""Test _async_create_doc background worker inserts document payload."""
		payload = {
			"doctype": "Contact",
			"first_name": f"Async_{self._uid()}",
		}
		res = _async_create_doc(payload, ignore_permissions=True)
		self.assertIsInstance(res, dict)
		self.assertTrue(frappe.db.exists("Contact", res.get("name")))

	def test_validation_rules(self):
		"""Test DocumentActionHandler.validate() for edge cases."""
		# Missing operation/doctype
		action_empty = frappe._dict({"operation": "", "reference_doctype": ""})
		errs = self.handler.validate(action_empty, {})
		self.assertTrue(any("Operation/Mode is required" in e for e in errs))

		# Update without target identity
		action_update = frappe._dict({"operation": "Update Existing", "reference_doctype": "Contact", "reference_docname": ""})
		action_update.config = "{}"
		errs = self.handler.validate(action_update, {})
		self.assertTrue(any("requires a target record" in e for e in errs))

		# Create ToDo with missing assigned_to
		action_todo = frappe._dict({"operation": "Create ToDo", "reference_doctype": "ToDo"})
		action_todo.config = json.dumps({"description": "Task"})
		errs = self.handler.validate(action_todo, {})
		self.assertTrue(any("assigned_to" in e for e in errs))

		# Add Comment with invalid doctype
		action_comment = frappe._dict({"operation": "Add Comment", "reference_doctype": "Contact"})
		action_comment.config = json.dumps({"comment_text": "Hello"})
		errs = self.handler.validate(action_comment, {})
		self.assertTrue(any("Reference DocType = Comment" in e for e in errs))
