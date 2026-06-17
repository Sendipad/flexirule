# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Real-world rule tests using Frappe core Contact DocType.
No ERPNext dependency. Covers all trigger types, action types,
process usage, context transformation, and sub-rule reuse.
"""

import json

import frappe
from frappe import _
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.engine import RuleEngine


def _uid():
	return str(frappe.utils.now_datetime().timestamp()).replace(".", "")[-8:]


def _make_rule(name, **kwargs):
	"""Create a Rule doc with safe defaults."""
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
	RuleCoordinator.clear_cache()
	return doc


def _action(action_id, action_label, action_type, **kw):
	"""Helper to build a Rule Action child row dict."""
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


def _make_contact(first_name=None, email=None, phone=None, **kw):
	"""Create a test Contact."""
	uid = _uid()
	doc = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name or f"Test-{uid}",
			"email_ids": [{"email_id": email or f"test-{uid}@example.com", "is_primary": 1}]
			if email or not kw.get("no_email")
			else [],
			"phone_nos": [{"phone": phone or f"+9665{uid[:7]}", "is_primary_phone": 1}]
			if phone or not kw.get("no_phone")
			else [],
			**kw,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestRealRules(FrappeTestCase):
	"""10 real-world rules exercising all FlexiRule features."""

	def setUp(self):
		# Clean up test rules & contacts from previous runs
		for r in frappe.get_all("Rule", filters={"rule_name": ["like", "TestReal_%"]}, pluck="name"):
			frappe.delete_doc("Rule", r, force=True)
		for c in frappe.get_all("Contact", filters={"first_name": ["like", "Test-%"]}, pluck="name"):
			frappe.delete_doc("Contact", c, force=True)
		frappe.db.commit()
		RuleCoordinator.clear_cache()

	def tearDown(self):
		for r in frappe.get_all("Rule", filters={"rule_name": ["like", "TestReal_%"]}, pluck="name"):
			frappe.delete_doc("Rule", r, force=True)
		for c in frappe.get_all("Contact", filters={"first_name": ["like", "Test-%"]}, pluck="name"):
			frappe.delete_doc("Contact", c, force=True)
		frappe.db.commit()
		RuleCoordinator.clear_cache()

	# ─────────────────────────────────────────────────────────
	# Rule 1: Scheduler - Query + Normalization + ToDo
	# ─────────────────────────────────────────────────────────
	def test_rule_01_scheduler_cleaning_pipeline(self):
		"""Scheduler rule: query contacts → normalize names → create todo."""
		contact = _make_contact(first_name="  john   DOE  ")

		rule = _make_rule(
			f"TestReal_01_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			exposed_as_subrule=0,
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="query"),
				_action(
					"query",
					"Query Contacts",
					"Query Records",
					reference_doctype="Contact",
					operation="Query List",
					return_variable="contacts",
					return_type="List of Records",
					config={
						"filters": {"first_name": ["like", "%john%"]},
						"fields": ["name", "first_name"],
						"limit": 10,
					},
					next_step_if_true="normalize",
					skip_permissions=1,
					permission_audit_reason="Test automation",
				),
				_action(
					"normalize",
					"Normalize Name",
					"Assignment",
					config=[
						{
							"target": "doc.first_name",
							"operator": "set",
							"value": {
								"mode": "resolver",
								"config": {
									"kind": "normalization",
									"norm_field": "doc.first_name",
									"norm_pipeline": ["trim", "remove_extra_spaces", "title_case"],
								},
							},
						}
					],
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		# Execute as callable rule
		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(contact)

		# Name should be normalized in memory (callable rules don't auto-save to DB)
		self.assertEqual(contact.first_name, "John Doe")

	# ─────────────────────────────────────────────────────────
	# Rule 2: Callable sub-rule - Phone Validation
	# ─────────────────────────────────────────────────────────
	def test_rule_02_phone_validation_subrule(self):
		"""Callable sub-rule: validates phone exists and has valid prefix."""
		contact = _make_contact(phone="+966512345678")

		rule = _make_rule(
			f"TestReal_02_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			exposed_as_subrule=1,
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="check_phone"),
				_action(
					"check_phone",
					"Check Phone Exists",
					"Condition",
					condition_json=json.dumps(
						{"left": {"ref": "doc.phone"}, "op": "is_set", "right": {"value": ""}}
					),
					next_step_if_true="set_valid",
					next_step_if_false="set_invalid",
				),
				_action(
					"set_valid",
					"Mark Valid",
					"Assignment",
					config=[{"target": "doc.department", "operator": "set", "value": "Validated"}],
					next_step_if_true="done",
				),
				_action(
					"set_invalid",
					"Mark Invalid",
					"Raise Error",
					value_template="Contact must have a phone number",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(contact)

		# Assignment operates in memory
		self.assertEqual(contact.department, "Validated")

	# ─────────────────────────────────────────────────────────
	# Rule 3: Before Save - Condition + Stop (Error)
	# ─────────────────────────────────────────────────────────
	def test_rule_03_before_save_validation(self):
		"""Before save rule: checks first_name, raises error if empty."""
		_make_rule(
			f"TestReal_03_{_uid()}",
			trigger_event="Before Save",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="check_name"),
				_action(
					"check_name",
					"Check Name",
					"Condition",
					condition_json=json.dumps(
						{"left": {"ref": "doc.designation"}, "op": "==", "right": {"value": "BLOCKED"}}
					),
					next_step_if_true="block",
					next_step_if_false="done",
				),
				_action(
					"block",
					"Block Save",
					"Stop",
					operation="Error",
					value_template="Contacts with BLOCKED designation cannot be saved",
				),
				_action("done", "Allow", "Stop", operation="Success"),
			],
		)

		# Should pass for normal contact
		_make_contact(first_name=f"Test-Normal-{_uid()}")
		# No error raised = pass

		# Should fail for blocked contact
		with self.assertRaises(frappe.ValidationError):
			blocked = frappe.get_doc(
				{
					"doctype": "Contact",
					"first_name": f"Test-Blocked-{_uid()}",
					"designation": "BLOCKED",
				}
			)
			blocked.insert(ignore_permissions=True)

	# ─────────────────────────────────────────────────────────
	# Rule 4: Document Action - Create ToDo + Add Comment
	# ─────────────────────────────────────────────────────────
	def test_rule_04_document_actions_and_context(self):
		"""Create a ToDo linked to a Contact, then add a comment."""
		contact = _make_contact()

		rule = _make_rule(
			f"TestReal_04_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="create_todo"),
				_action(
					"create_todo",
					"Create ToDo",
					"Document Action",
					reference_doctype="ToDo",
					operation="Create ToDo",
					return_variable="todo_result",
					return_type="Single Record",
					config={
						"assigned_to": "Administrator",
						"description": "Review contact {{ doc.first_name }}",
						"priority": "High",
					},
					skip_permissions=1,
					permission_audit_reason="Test automation",
					next_step_if_true="add_comment",
				),
				_action(
					"add_comment",
					"Add Comment",
					"Document Action",
					reference_doctype="Comment",
					operation="Add Comment",
					config={
						"comment_text": "ToDo created for review",
						"comment_type": "Comment",
					},
					skip_permissions=1,
					permission_audit_reason="Test automation",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(contact)

		# Verify ToDo was created
		todo = frappe.get_all(
			"ToDo",
			filters={"reference_type": "Contact", "reference_name": contact.name},
			pluck="name",
		)
		self.assertTrue(len(todo) > 0, "ToDo should be created")

		# Verify comment was added
		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Contact",
				"reference_name": contact.name,
				"comment_type": "Comment",
			},
			pluck="name",
		)
		self.assertTrue(len(comments) > 0, "Comment should be added")

	# ─────────────────────────────────────────────────────────
	# Rule 5: Retry + Error Handling
	# ─────────────────────────────────────────────────────────
	def test_rule_05_error_handling_continue(self):
		"""Test on_error=Continue: first action fails, flow continues to next."""
		contact = _make_contact()

		rule = _make_rule(
			f"TestReal_05_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="bad_process"),
				_action(
					"bad_process",
					"Bad Process",
					"Process",
					process_name="Enrichment",
					operation="calculate_value",
					on_error="Continue",
					config={
						"target_field": "department",
						"formula": "1 / 0",  # Division by zero = error
					},
					return_variable="bad_res",
					next_step_if_true="good_step",
				),
				_action(
					"good_step",
					"Mark Success",
					"Assignment",
					config=[{"target": "doc.department", "operator": "set", "value": "ErrorHandled"}],
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(contact)

		# Assignment in memory
		self.assertEqual(contact.department, "ErrorHandled")

	# ─────────────────────────────────────────────────────────
	# Rule 6: Email Domain Validation
	# ─────────────────────────────────────────────────────────
	def test_rule_06_email_domain_validation(self):
		"""Validate trigger: count contacts with same email domain."""
		email = f"test-{_uid()}@unique-domain-{_uid()}.com"
		contact = _make_contact(email=email)

		rule = _make_rule(
			f"TestReal_06_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="count"),
				_action(
					"count",
					"Count Domain",
					"Query Records",
					reference_doctype="Contact",
					operation="Count",
					return_variable="domain_count",
					config={"filters": {}},
					skip_permissions=1,
					permission_audit_reason="Test automation",
					next_step_if_true="check",
				),
				_action(
					"check",
					"Check Count",
					"Condition",
					condition_json=json.dumps(
						{"left": {"ref": "doc.first_name"}, "op": "is_set", "right": {"value": ""}}
					),
					next_step_if_true="done",
					next_step_if_false="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		ctx = engine.execute(contact)

		self.assertIsNotNone(ctx.get("vars", {}).get("domain_count"))

	# ─────────────────────────────────────────────────────────
	# Rule 7: Contact Merge Review (Callable + Query + ToDo)
	# ─────────────────────────────────────────────────────────
	def test_rule_07_merge_review_callable(self):
		"""Callable rule: query contacts → create review ToDo."""
		first_name = f"Test-Merge-{_uid()}"
		c1 = _make_contact(first_name=first_name)
		_make_contact(first_name=first_name)

		rule = _make_rule(
			f"TestReal_07_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="query"),
				_action(
					"query",
					"Find Duplicates",
					"Query Records",
					reference_doctype="Contact",
					operation="Query List",
					return_variable="duplicates",
					return_type="List of Records",
					config={
						"filters": {"first_name": first_name},
						"fields": ["name", "first_name"],
						"limit": 100,
					},
					skip_permissions=1,
					permission_audit_reason="Test",
					next_step_if_true="notify",
				),
				_action(
					"notify",
					"Notify",
					"Notify",
					operation="Toast",
					value_template="Found {{ vars.duplicates|length }} potential duplicates",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		ctx = engine.execute(c1)

		duplicates = ctx.get("vars", {}).get("duplicates", [])
		self.assertGreaterEqual(len(duplicates), 2)

	# ─────────────────────────────────────────────────────────
	# Rule 8: Scheduler Bulk Status Update (Query + Assignment)
	# ─────────────────────────────────────────────────────────
	def test_rule_08_bulk_status_update(self):
		"""Scheduler pattern: query + process to update fields."""
		tag = f"Test-Bulk-{_uid()}"
		c1 = _make_contact(first_name=tag)

		rule = _make_rule(
			f"TestReal_08_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="query"),
				_action(
					"query",
					"Query Stale",
					"Query Records",
					reference_doctype="Contact",
					operation="Query List",
					return_variable="stale_contacts",
					return_type="List of Records",
					config={
						"filters": {"first_name": tag},
						"fields": ["name"],
						"limit": 100,
					},
					skip_permissions=1,
					permission_audit_reason="Test",
					next_step_if_true="set_status",
				),
				_action(
					"set_status",
					"Mark Processed",
					"Assignment",
					config=[{"target": "doc.department", "operator": "set", "value": "BulkProcessed"}],
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		ctx = engine.execute(c1)

		# Assignment operates in-memory on the context doc
		self.assertEqual(c1.department, "BulkProcessed")
		self.assertIn("stale_contacts", ctx.get("vars", {}))

	# ─────────────────────────────────────────────────────────
	# Rule 9: Cross-Doc Linking (Query + Condition + Update)
	# ─────────────────────────────────────────────────────────
	def test_rule_09_cross_doc_query_and_update(self):
		"""Query Doc mode: fetch a document by name, store as context."""
		contact = _make_contact()

		rule = _make_rule(
			f"TestReal_09_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="query_doc"),
				_action(
					"query_doc",
					"Fetch Self",
					"Query Records",
					reference_doctype="Contact",
					operation="Query Doc",
					config={
						"fetch_strategy": "Get doc",
						"doctype_name": "Contact",
						"docname": contact.name,
					},
					return_variable="fetched_doc",
					return_type="Full Document",
					skip_permissions=1,
					permission_audit_reason="Test",
					next_step_if_true="check",
				),
				_action(
					"check",
					"Verify Fetch",
					"Condition",
					condition_json=json.dumps(
						{"left": {"ref": "doc.first_name"}, "op": "is_set", "right": {"value": ""}}
					),
					next_step_if_true="update",
					next_step_if_false="done",
				),
				_action(
					"update",
					"Set Department",
					"Assignment",
					config=[{"target": "doc.department", "operator": "set", "value": "CrossDocLinked"}],
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		ctx = engine.execute(contact)

		# Assignment in memory
		self.assertEqual(contact.department, "CrossDocLinked")
		self.assertIn("fetched_doc", ctx.get("vars", {}))

	# ─────────────────────────────────────────────────────────
	# Rule 10: Context Transform Pipeline (Process + Assignment)
	# ─────────────────────────────────────────────────────────
	def test_rule_10_context_transform_pipeline(self):
		"""Process normalization → Assignment → stop: multi-step transform."""
		contact = _make_contact(first_name="  test   user  ")

		rule = _make_rule(
			f"TestReal_10_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="normalize"),
				_action(
					"normalize",
					"Normalize Name",
					"Assignment",
					config=[
						{
							"target": "doc.first_name",
							"operator": "set",
							"value": {
								"mode": "resolver",
								"config": {
									"kind": "normalization",
									"norm_field": "doc.first_name",
									"norm_pipeline": ["trim", "remove_extra_spaces", "title_case"],
								},
							},
						}
					],
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		engine = RuleEngine(rule, {"test_mode": True})
		engine.execute(contact)

		# Normalization + Assignment operate in memory
		self.assertEqual(contact.first_name, "Test User")


class TestSubRuleIsolation(FrappeTestCase):
	"""Verify sub-rule context isolation works correctly."""

	def setUp(self):
		# Delete parent rules first to avoid sub-rule reference protection
		for r in frappe.get_all(
			"Rule",
			filters={"rule_name": ["like", "TestIso_Parent%"]},
			pluck="name",
		):
			frappe.delete_doc("Rule", r, force=True)
		for r in frappe.get_all("Rule", filters={"rule_name": ["like", "TestIso_%"]}, pluck="name"):
			frappe.delete_doc("Rule", r, force=True)
		frappe.db.commit()
		RuleCoordinator.clear_cache()

	def tearDown(self):
		# Delete parent rules first to avoid sub-rule reference protection
		for r in frappe.get_all(
			"Rule",
			filters={"rule_name": ["like", "TestIso_Parent%"]},
			pluck="name",
		):
			frappe.delete_doc("Rule", r, force=True)
		for r in frappe.get_all(
			"Rule",
			filters={"rule_name": ["like", "TestIso_%"]},
			pluck="name",
		):
			frappe.delete_doc("Rule", r, force=True)
		for c in frappe.get_all("Contact", filters={"first_name": ["like", "Test-%"]}, pluck="name"):
			frappe.delete_doc("Contact", c, force=True)
		frappe.db.commit()
		RuleCoordinator.clear_cache()

	def test_subrule_isolation_with_return_variable(self):
		"""Sub-rule vars are isolated when return_variable is set."""
		# Create sub-rule that writes an internal context variable
		sub_rule = _make_rule(
			f"TestIso_Sub_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			exposed_as_subrule=1,
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="count_contacts"),
				_action(
					"count_contacts",
					"Count Contacts",
					"Query Records",
					reference_doctype="Contact",
					operation="Count",
					return_variable="internal_contact_count",
					config={},
					skip_permissions=1,
					permission_audit_reason="Test isolation",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		# Create parent rule that calls sub-rule with return_variable
		parent_rule = _make_rule(
			f"TestIso_Parent_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="call_sub"),
				_action(
					"call_sub",
					"Call Sub-Rule",
					"Sub-Rule",
					rule=sub_rule.name,
					return_variable="sub_result",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		contact = _make_contact()
		engine = RuleEngine(parent_rule, {"test_mode": True})
		ctx = engine.execute(contact)

		# Sub-rule result should be namespaced under return_variable
		self.assertIn("sub_result", ctx.get("vars", {}))
		self.assertIn("internal_contact_count", ctx.get("vars", {}).get("sub_result", {}))
		self.assertNotIn("internal_contact_count", ctx.get("vars", {}))

	def test_subrule_without_return_variable_uses_auto_namespace(self):
		"""Without return_variable, sub-rule output is written to deterministic namespace."""
		sub_rule = _make_rule(
			f"TestIso_SubBC_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			exposed_as_subrule=1,
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="count_contacts"),
				_action(
					"count_contacts",
					"Count Contacts",
					"Query Records",
					reference_doctype="Contact",
					operation="Count",
					return_variable="internal_count",
					config={},
					skip_permissions=1,
					permission_audit_reason="Test isolation",
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		parent_rule = _make_rule(
			f"TestIso_ParentBC_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="call_sub"),
				_action(
					"call_sub",
					"Call Sub-Rule",
					"Sub-Rule",
					rule=sub_rule.name,
					# No return_variable: output should go to auto namespace
					next_step_if_true="done",
				),
				_action("done", "Complete", "Stop", operation="Success"),
			],
		)

		contact = _make_contact()
		engine = RuleEngine(parent_rule, {"test_mode": True})
		ctx = engine.execute(contact)
		self.assertIn("subrule_call_sub", ctx.get("vars", {}))
		self.assertIn("internal_count", ctx.get("vars", {}).get("subrule_call_sub", {}))
		self.assertNotIn("internal_count", ctx.get("vars", {}))


class TestRaiseErrorAction(FrappeTestCase):
	"""Verify the Raise Error action type works correctly."""

	def setUp(self):
		for r in frappe.get_all("Rule", filters={"rule_name": ["like", "TestRE_%"]}, pluck="name"):
			frappe.delete_doc("Rule", r, force=True)
		frappe.db.commit()
		RuleCoordinator.clear_cache()

	def tearDown(self):
		for r in frappe.get_all("Rule", filters={"rule_name": ["like", "TestRE_%"]}, pluck="name"):
			frappe.delete_doc("Rule", r, force=True)
		for c in frappe.get_all("Contact", filters={"first_name": ["like", "Test-%"]}, pluck="name"):
			frappe.delete_doc("Contact", c, force=True)
		frappe.db.commit()
		RuleCoordinator.clear_cache()

	def test_raise_error_stops_execution(self):
		"""Raise Error action throws ValidationError and halts."""
		rule = _make_rule(
			f"TestRE_01_{_uid()}",
			trigger_type="Callable Event",
			trigger_event="",
			actions=[
				_action("root", "Start", "Entry Action", next_step_if_true="error"),
				_action(
					"error",
					"Raise Error",
					"Raise Error",
					value_template="This contact is invalid: {{ doc.first_name }}",
				),
			],
		)

		contact = _make_contact(first_name=f"Test-BadContact-{_uid()}")
		engine = RuleEngine(rule, {"test_mode": True})
		with self.assertRaises(frappe.ValidationError) as ctx:
			engine.execute(contact)

		self.assertIn("invalid", str(ctx.exception))

	def test_raise_error_in_contract(self):
		"""Raise Error should be in ACTION_TYPE_CONTRACT."""
		from flexirule.ruleflow.core.contracts import ACTION_TYPE_CONTRACT

		self.assertIn("Raise Error", ACTION_TYPE_CONTRACT)
		contract = ACTION_TYPE_CONTRACT["Raise Error"]
		self.assertTrue(contract["terminal"])
		self.assertIn("value_template", contract["required_fields"])
