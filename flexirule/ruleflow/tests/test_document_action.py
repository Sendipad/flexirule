# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.document_action import DocumentActionHandler
from flexirule.ruleflow.core.contract_dto import get_contract_dto
from flexirule.ruleflow.core.engine import RuleEngine


def _uid():
	return str(frappe.utils.now_datetime().timestamp()).replace(".", "")[-8:]


def _make_rule(name, **kwargs):
	trigger_type = kwargs.get("trigger_type", "DocType Event")
	doc = frappe.get_doc(
		{
			"doctype": "Rule",
			"rule_name": name,
			"trigger_type": trigger_type,
			"document_type": kwargs.get("document_type", "Contact"),
			"trigger_event": kwargs.get("trigger_event", "Before Save"),
			"is_active": kwargs.get("is_active", 1),
			"execution_mode": kwargs.get("execution_mode", "Synchronous"),
			"exposed_as_subrule": kwargs.get("exposed_as_subrule", 0),
			"priority": 0 if trigger_type == "Callable Event" else kwargs.get("priority", 10),
			"actions": kwargs.get("actions", []),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _action(action_id, action_label, action_type, **kw):
	row = {
		"doctype": "Rule Action",
		"action_id": action_id,
		"action_label": action_label,
		"action_type": action_type,
		"is_enabled": 1,
	}
	for key, val in kw.items():
		if key in ("config", "condition_json", "resolved_output_schema") and isinstance(val, dict | list):
			row[key] = json.dumps(val)
		else:
			row[key] = val
	return row


def _make_contact(first_name=None, email=None, **kw):
	uid = _uid()
	doc = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name or f"TestDocAction-{uid}",
			"email_ids": [{"email_id": email or f"testdocaction-{uid}@example.com", "is_primary": 1}],
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestDocumentActionPhase1(FrappeTestCase):
	"""Comprehensive tests for Document Action Phase 1 backend contracts, validation, and runtime."""

	def setUp(self):
		for r in frappe.get_all("Rule", filters={"rule_name": ["like", "TestDocAct_%"]}, pluck="name"):
			frappe.delete_doc("Rule", r, force=True)
		for c in frappe.get_all("Contact", filters={"first_name": ["like", "TestDocAction-%"]}, pluck="name"):
			frappe.delete_doc("Contact", c, force=True)

	def tearDown(self):
		for r in frappe.get_all("Rule", filters={"rule_name": ["like", "TestDocAct_%"]}, pluck="name"):
			frappe.delete_doc("Rule", r, force=True)
		for c in frappe.get_all("Contact", filters={"first_name": ["like", "TestDocAction-%"]}, pluck="name"):
			frappe.delete_doc("Contact", c, force=True)

	def test_contract_dto_and_operation_contracts(self):
		"""Verify operation contracts and DTO policies for all 5 Document Action operations."""
		handler = DocumentActionHandler()
		op_contracts = handler.get_operation_contracts()

		self.assertIn("Create New", op_contracts)
		self.assertIn("Update Existing", op_contracts)
		self.assertIn("Delete Record", op_contracts)
		self.assertIn("Create ToDo", op_contracts)
		self.assertIn("Add Comment", op_contracts)

		# Check Add Comment does NOT require reference_docname in action_overrides
		comment_overrides = op_contracts["Add Comment"].action_overrides
		override_fieldnames = [o.get("fieldname") for o in comment_overrides]
		self.assertNotIn("reference_docname", override_fieldnames)

		# Check Update Existing & Delete Record have reference_docname override without reqd=1
		for op in ("Update Existing", "Delete Record"):
			overrides = op_contracts[op].action_overrides
			ref_docname_def = next((o for o in overrides if o.get("fieldname") == "reference_docname"), None)
			self.assertIsNotNone(ref_docname_def)
			assert ref_docname_def is not None
			self.assertNotEqual(ref_docname_def.get("reqd"), 1)

		# Verify Contract DTO output includes fixed_doctype and required_config_keys
		dto = get_contract_dto()
		doc_contract = dto["action_type_contract"]["Document Action"]
		policies = doc_contract["operation_policies"]

		self.assertEqual(policies["Create ToDo"].get("fixed_doctype"), "ToDo")
		self.assertEqual(policies["Add Comment"].get("fixed_doctype"), "Comment")
		self.assertEqual(policies["Create ToDo"].get("required_config_keys"), ["assigned_to", "description"])
		self.assertEqual(policies["Add Comment"].get("required_config_keys"), ["comment_text"])

	def test_handler_validation(self):
		"""Verify handler.validate() rules across all modes."""
		handler = DocumentActionHandler()

		# Add Comment valid without reference_docname
		action_comment = frappe._dict(
			{
				"operation": "Add Comment",
				"reference_doctype": "Comment",
				"config": json.dumps({"comment_text": "Test comment"}),
			}
		)
		self.assertEqual(handler.validate(action_comment, {}), [])

		# Add Comment invalid if wrong reference_doctype
		action_bad_comment_dt = frappe._dict(
			{
				"operation": "Add Comment",
				"reference_doctype": "Contact",
				"config": json.dumps({"comment_text": "Test comment"}),
			}
		)
		errs = handler.validate(action_bad_comment_dt, {})
		self.assertTrue(any("requires Reference DocType = Comment" in e for e in errs))

		# Update Existing valid with config docname_expression instead of reference_docname
		action_update_fallback = frappe._dict(
			{
				"operation": "Update Existing",
				"reference_doctype": "Contact",
				"reference_docname": None,
				"config": json.dumps({"docname_expression": "doc.name"}),
			}
		)
		self.assertEqual(handler.validate(action_update_fallback, {}), [])

		# Update Existing invalid if neither reference_docname nor config docname is provided
		action_update_no_id = frappe._dict(
			{
				"operation": "Update Existing",
				"reference_doctype": "Contact",
				"reference_docname": None,
				"config": json.dumps({}),
			}
		)
		errs = handler.validate(action_update_no_id, {})
		self.assertTrue(any("requires either a Reference Document" in e for e in errs))

	def test_add_comment_execution(self):
		"""Verify Add Comment executes and attaches to context.doc without reference_docname."""
		contact = _make_contact()

		rule = _make_rule(
			f"TestDocAct_AddComment_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="comment"),
				_action(
					"comment",
					"Add Comment",
					"Document Action",
					reference_doctype="Comment",
					operation="Add Comment",
					config={
						"comment_text": "Reviewed {{ doc.first_name }} for user {vars.reviewer}",
						"comment_type": "Comment",
					},
					ignore_permissions=1,
					permission_audit_reason="Testing Add Comment",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(contact, vars={"reviewer": "Administrator"})

		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Contact",
				"reference_name": contact.name,
			},
			fields=["content"],
		)
		self.assertEqual(len(comments), 1)
		self.assertIn(f"Reviewed {contact.first_name} for user Administrator", comments[0].content)

	def test_create_todo_expression_and_template(self):
		"""Verify Create ToDo renders both Jinja templates and {vars} expressions."""
		contact = _make_contact()

		rule = _make_rule(
			f"TestDocAct_CreateToDo_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="todo"),
				_action(
					"todo",
					"Create Task",
					"Document Action",
					reference_doctype="ToDo",
					operation="Create ToDo",
					config={
						"assigned_to": "{vars.assignee}",
						"description": "Task for {{ doc.first_name }}",
						"priority": "High",
					},
					ignore_permissions=1,
					permission_audit_reason="Testing Create ToDo",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(contact, vars={"assignee": "Administrator"})

		todos = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": "Contact",
				"reference_name": contact.name,
			},
			fields=["allocated_to", "description", "priority"],
		)
		self.assertEqual(len(todos), 1)
		self.assertEqual(todos[0].allocated_to, "Administrator")
		self.assertEqual(todos[0].description, f"Task for {contact.first_name}")
		self.assertEqual(todos[0].priority, "High")

	def test_update_existing_precedence_and_fallbacks(self):
		"""Verify Update Existing target identity resolution precedence."""
		c1 = _make_contact(first_name="OriginalName")

		rule = _make_rule(
			f"TestDocAct_UpdateP_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="update_doc"),
				_action(
					"update_doc",
					"Update Contact",
					"Document Action",
					reference_doctype="Contact",
					operation="Update Existing",
					return_variable="update_res",
					return_type="Single Record",
					config={
						"docname_expression": "doc.name",
						"static_values": {"department": "UpdatedDept"},
					},
					ignore_permissions=1,
					permission_audit_reason="Testing Update Existing",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(c1)

		c1_reloaded = frappe.get_doc("Contact", c1.name)
		self.assertEqual(c1_reloaded.department, "UpdatedDept")

	def test_delete_record_fallback(self):
		"""Verify Delete Record works with docname_expression fallback."""
		c1 = _make_contact()

		rule = _make_rule(
			f"TestDocAct_Delete_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="del_doc"),
				_action(
					"del_doc",
					"Delete Contact",
					"Document Action",
					reference_doctype="Contact",
					operation="Delete Record",
					config={"docname_expression": "vars.target_name"},
					ignore_permissions=1,
					permission_audit_reason="Testing Delete Record",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(c1, vars={"target_name": c1.name})

		self.assertFalse(frappe.db.exists("Contact", c1.name))

	def test_async_create_new_with_child_tables(self):
		"""Verify async Create New mode evaluates table mappings and invokes whitelisted _async_create_doc."""
		contact = _make_contact()

		rule = _make_rule(
			f"TestDocAct_AsyncCreate_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="create_doc"),
				_action(
					"create_doc",
					"Create Async Contact",
					"Document Action",
					reference_doctype="Contact",
					operation="Create New",
					is_async=1,
					return_variable="async_res",
					return_type="Single Record",
					config={
						"static_values": {"first_name": f"AsyncContact-{_uid()}"},
						"table_mappings": [
							{
								"target_table": "email_ids",
								"source": "doc.email_ids",
								"assignments": [
									{"target": "email_id", "source_type": "expr", "source": "item.email_id"},
									{"target": "is_primary", "source_type": "literal", "literal": 1},
								],
							}
						],
					},
					ignore_permissions=1,
					permission_audit_reason="Testing Async Create",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		ctx = engine.execute(contact)

		self.assertTrue(ctx.get("vars", {}).get("async_res", {}).get("enqueued"))
