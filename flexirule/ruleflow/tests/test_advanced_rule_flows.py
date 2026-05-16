import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator


def _j(value):
	return json.dumps(value)


class TestAdvancedRuleFlows(FrappeTestCase):
	RULE_PREFIX = "FX Advanced Rule"
	FIRST_NAME = "FX Advanced Subject"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

	@classmethod
	def tearDownClass(cls):
		RuleCoordinator.clear_cache()
		frappe.db.rollback()
		super().tearDownClass()

	def tearDown(self):
		RuleCoordinator.clear_cache()
		frappe.db.rollback()
		super().tearDown()

	def _trigger_filter(self):
		return _j(
			[
				{
					"left": {"ref": "doc.first_name"},
					"op": "==",
					"right": {"value": self.FIRST_NAME},
				}
			]
		)

	def _create_rule(
		self,
		rule_name,
		actions,
		trigger_type="DocType Event",
		trigger_event="Validate",
		is_active=1,
		exposed_as_subrule=0,
		priority="10",
	):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": rule_name,
				"document_type": "Contact",
				"trigger_type": trigger_type,
				"trigger_event": trigger_event,
				"trigger_condition": self._trigger_filter() if trigger_type == "DocType Event" else None,
				"is_active": is_active,
				"priority": priority,
				"exposed_as_subrule": exposed_as_subrule,
				"max_execution_time": 10,
				"actions": actions,
			}
		)
		rule.insert(ignore_permissions=True)
		rule.compile_conditions()
		if rule.compiled_expression:
			frappe.db.set_value("Rule", rule.name, "compiled_expression", rule.compiled_expression)
		RuleCoordinator.clear_cache()
		return rule

	def _create_existing_contact(self, phone, email):
		return frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "FX Advanced Existing",
				"last_name": "Match",
				"status": "Passive",
				"email_ids": [{"email_id": email, "is_primary": 1}],
				"phone_nos": [{"phone": phone, "is_primary_phone": 1}],
			}
		).insert(ignore_permissions=True)

	def _create_subject_contact(self, phone, email):
		return frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": self.FIRST_NAME,
				"last_name": "Flow",
				"status": "Passive",
				"email_ids": [{"email_id": email, "is_primary": 1}],
				"phone_nos": [{"phone": phone, "is_primary_phone": 1}],
			}
		)

	def _latest_log(self, rule_name, docname=None):
		filters = {"rule": rule_name}
		if docname:
			filters["reference_docname"] = docname

		name = frappe.get_all(
			"Rule Execution Log",
			filters=filters,
			order_by="creation desc",
			limit=1,
			pluck="name",
		)
		return frappe.get_doc("Rule Execution Log", name[0]) if name else None

	def _create_nested_callable_rule(self):
		return self._create_rule(
			f"{self.RULE_PREFIX} Nested Callable",
			actions=[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Nested Start",
					"next_step_if_true": "nested_comment",
				},
				{
					"action_id": "nested_comment",
					"action_type": "Document Action",
					"action_label": "Nested Comment",
					"reference_doctype": "Comment",
					"operation": "Add Comment",
					"config": _j({"comment_text": "Nested callable executed for {{ doc.name }}"}),
					"skip_permissions": 1,
					"permission_audit_reason": "Automated Test",
					"return_variable": "nested_comment_result",
					"next_step_if_true": "nested_stop",
				},
				{
					"action_id": "nested_stop",
					"action_type": "Stop",
					"operation": "Success",
					"action_label": "Nested Stop",
				},
			],
			trigger_type="Callable Event",
			trigger_event=None,
			exposed_as_subrule=1,
			priority="0",
		)

	def _create_callable_followup_rule(self, nested_rule_name):
		return self._create_rule(
			f"{self.RULE_PREFIX} Callable Followup",
			actions=[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Callable Start",
					"next_step_if_true": "create_todo",
				},
				{
					"action_id": "create_todo",
					"action_type": "Document Action",
					"action_label": "Create Followup ToDo",
					"reference_doctype": "ToDo",
					"operation": "Create ToDo",
					"config": _j(
						{
							"assigned_to": "Administrator",
							"description": "Review advanced flow contact {{ doc.name }}",
							"priority": "High",
						}
					),
					"skip_permissions": 1,
					"permission_audit_reason": "Automated Test",
					"return_variable": "followup_todo",
					"next_step_if_true": "call_nested",
				},
				{
					"action_id": "call_nested",
					"action_type": "Sub-Rule",
					"action_label": "Call Nested Callable",
					"rule": nested_rule_name,
					"skip_conditions": 1,
					"skip_permissions": 1,
					"permission_audit_reason": "Automated Test",
					"next_step_if_true": "callable_stop",
				},
				{
					"action_id": "callable_stop",
					"action_type": "Stop",
					"operation": "Success",
					"action_label": "Callable Stop",
				},
			],
			trigger_type="Callable Event",
			trigger_event=None,
			exposed_as_subrule=1,
			priority="0",
		)

	def _create_before_save_rule(self):
		return self._create_rule(
			f"{self.RULE_PREFIX} Before Save",
			actions=[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Before Save Start",
					"next_step_if_true": "detect_change",
				},
				{
					"action_id": "detect_change",
					"action_type": "Process",
					"action_label": "Detect Contact Changes",
					"process_name": "Validation",
					"operation": "on_field_change",
					"config": _j(
						{
							"watched_fields": ["email_id", "phone", "mobile_no"],
							"match_mode": "Any",
							"store_result": "changed_fields",
						}
					),
					"return_variable": "contact_changed",
					"return_type": "Yes / No",
					"next_step_if_true": "dedupe_phone",
				},
				{
					"action_id": "dedupe_phone",
					"action_type": "Process",
					"action_label": "Find Phone Duplicates",
					"process_name": "Deduplication",
					"operation": "find_duplicates_in_child_table",
					"config": _j(
						{
							"child_table_field": "phone_nos",
							"child_search_field": "phone",
						}
					),
					"return_variable": "phone_matches",
					"next_step_if_true": "has_match",
				},
				{
					"action_id": "has_match",
					"action_type": "Condition",
					"action_label": "Has Duplicate Match",
					"condition_json": _j(
						[
							{
								"left": {"ref": "doc.email_id"},
								"op": "!=",
								"right": {"value": ""},
							}
						]
					),
					"next_step_if_true": "set_status",
					"next_step_if_false": "before_save_stop",
				},
				{
					"action_id": "set_status",
					"action_type": "Assignment",
					"config": json.dumps([{"target": "doc.status", "operator": "set", "value_template": "Open"}]),
					"action_label": "Set Status Open",
					"next_step_if_true": "before_save_stop",
				},
				{
					"action_id": "before_save_stop",
					"action_type": "Stop",
					"operation": "Success",
					"action_label": "Before Save Stop",
				},
			],
			trigger_event="Validate",
		)

	def _create_after_insert_rule(self, callable_rule_name):
		return self._create_rule(
			f"{self.RULE_PREFIX} After Insert",
			actions=[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "After Insert Start",
					"next_step_if_true": "notify_owner",
				},
				{
					"action_id": "notify_owner",
					"action_type": "Notify",
					"action_label": "Notify Owner",
					"operation": "System Notification",
					"value_template": "Contact {{ doc.name }} entered the advanced flow.",
					"config": _j(
						{
							"subject": "Advanced flow for {{ doc.name }}",
							"for_user": "Administrator",
						}
					),
					"next_step_if_true": "after_insert_comment",
				},
				{
					"action_id": "after_insert_comment",
					"action_type": "Document Action",
					"action_label": "Create Timeline Comment",
					"reference_doctype": "Comment",
					"operation": "Add Comment",
					"config": _j(
						{
							"comment_text": "After insert flow executed for {{ doc.name }}",
						}
					),
					"skip_permissions": 1,
					"permission_audit_reason": "Automated Test",
					"return_variable": "after_insert_comment_result",
					"next_step_if_true": "wait_step",
				},
				{
					"action_id": "wait_step",
					"action_type": "Wait",
					"action_label": "Small Wait",
					"config": _j({"duration": 0.01}),
					"next_step_if_true": "call_followup",
				},
				{
					"action_id": "call_followup",
					"action_type": "Sub-Rule",
					"action_label": "Call Followup Callable",
					"rule": callable_rule_name,
					"skip_conditions": 1,
					"skip_permissions": 1,
					"permission_audit_reason": "Automated Test",
					"next_step_if_true": "after_insert_stop",
				},
				{
					"action_id": "after_insert_stop",
					"action_type": "Stop",
					"operation": "Success",
					"action_label": "After Insert Stop",
				},
			],
			trigger_event="After Insert",
		)

	def _create_scheduler_rule(self, callable_rule_name):
		return self._create_rule(
			f"{self.RULE_PREFIX} Scheduler",
			actions=[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Scheduler Start",
					"next_step_if_true": "query_current_contact",
				},
				{
					"action_id": "query_current_contact",
					"action_type": "Query Records",
					"action_label": "Fetch Contact Snapshot",
					"reference_doctype": "Contact",
					"operation": "Query Doc",
					"config": _j({"docname_expression": "doc.name"}),
					"mutation_mode": "Set Context Variable",
					"return_variable": "contact_snapshot",
					"return_type": "Full Document",
					"next_step_if_true": "count_followups",
				},
				{
					"action_id": "count_followups",
					"action_type": "Query Records",
					"action_label": "Count Followup ToDos",
					"reference_doctype": "ToDo",
					"operation": "Count",
					"config": _j(
						{
							"filters": [
								{"field": "reference_type", "operator": "=", "value": "{doc.doctype}"},
								{"field": "reference_name", "operator": "=", "value": "{doc.name}"},
							]
						}
					),
					"mutation_mode": "Set Context Variable",
					"return_variable": "todo_count",
					"next_step_if_true": "call_scheduler_followup",
				},
				{
					"action_id": "call_scheduler_followup",
					"action_type": "Sub-Rule",
					"action_label": "Call Followup From Scheduler",
					"rule": callable_rule_name,
					"skip_conditions": 1,
					"skip_permissions": 1,
					"permission_audit_reason": "Automated Test",
					"next_step_if_true": "scheduler_stop",
				},
				{
					"action_id": "scheduler_stop",
					"action_type": "Stop",
					"operation": "Success",
					"action_label": "Scheduler Stop",
				},
			],
			trigger_type="Scheduler Event",
			trigger_event=None,
		)

	def _create_raise_error_rule(self):
		return self._create_rule(
			f"{self.RULE_PREFIX} Raise Error",
			actions=[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Failure Start",
					"next_step_if_true": "raise_error",
				},
				{
					"action_id": "raise_error",
					"action_type": "Raise Error",
					"action_label": "Raise Blocking Error",
					"value_template": "Advanced flow blocked for {{ doc.name }}",
				},
			],
			trigger_type="Callable Event",
			trigger_event=None,
			priority="0",
		)

	def _create_loop_rule(self):
		return self._create_rule(
			f"{self.RULE_PREFIX} Loop",
			actions=[
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Loop Start",
					"next_step_if_true": "loop_phones",
				},
				{
					"action_id": "loop_phones",
					"action_type": "Loop",
					"action_label": "Iterate Phones",
					"config": _j({"iterator": "doc.phone_nos", "alias": "phone_row"}),
					"return_variable": "phone_row",
					"next_step_if_true": "set_loop_var",
					"next_step_if_false": "loop_stop",
				},
				{
					"action_id": "set_loop_var",
					"action_type": "Assignment",
					"config": json.dumps(
						[
							{
								"target": "vars.last_phone",
								"operator": "set",
								"value_template": "{{ vars.phone_row.phone }}",
							}
						]
					),
					"action_label": "Set Loop Context",
					"next_step_if_true": "loop_phones",
				},
				{
					"action_id": "loop_stop",
					"action_type": "Stop",
					"operation": "Success",
					"action_label": "Loop Complete",
				},
			],
			trigger_type="Callable Event",
			trigger_event=None,
			priority="0",
		)

	def _create_scheduler(self, rule_name, contact_name):
		return frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": rule_name,
				"frequency": "All",
				"filter_doctype": "Contact",
				"filter_json": _j({"name": contact_name}),
				"batch_size": 10,
				"on_error": "Stop",
			}
		).insert(ignore_permissions=True)

	def _build_scenarios(self):
		nested_rule = self._create_nested_callable_rule()
		callable_rule = self._create_callable_followup_rule(nested_rule.name)
		before_save_rule = self._create_before_save_rule()
		after_insert_rule = self._create_after_insert_rule(callable_rule.name)
		scheduler_rule = self._create_scheduler_rule(callable_rule.name)
		raise_error_rule = self._create_raise_error_rule()
		loop_rule = self._create_loop_rule()
		return {
			"nested": nested_rule,
			"callable": callable_rule,
			"before_save": before_save_rule,
			"after_insert": after_insert_rule,
			"scheduler": scheduler_rule,
			"raise_error": raise_error_rule,
			"loop": loop_rule,
		}

	def test_suite_fixtures_cover_all_current_action_types(self):
		scenarios = self._build_scenarios()
		used_action_types: set[str] = set()
		for rule in scenarios.values():
			used_action_types.update(action.action_type for action in rule.actions)

		available_action_types = {
			value.strip()
			for value in frappe.get_meta("Rule Action").get_field("action_type").options.splitlines()
			if value.strip()
		}

		missing = available_action_types - used_action_types
		extra = used_action_types - available_action_types
		msg = f"\nMissing coverage for: {missing}\nExtra coverage for: {extra}"
		self.assertSetEqual(used_action_types, available_action_types, msg)

	def test_contact_insert_runs_multi_rule_chain_with_nested_subrules(self):
		phone = "9715550100"
		email = "fx.advanced.insert@example.com"
		self._create_existing_contact(phone, email)
		scenarios = self._build_scenarios()

		contact = self._create_subject_contact(phone, email).insert(ignore_permissions=True)
		contact.reload()

		self.assertEqual(contact.status, "Open")

		comments = frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Contact", "reference_name": contact.name},
			fields=["name", "content"],
		)
		self.assertGreaterEqual(len(comments), 2)
		self.assertTrue(any("After insert flow executed" in row.content for row in comments))
		self.assertTrue(any("Nested callable executed" in row.content for row in comments))

		todos = frappe.get_all(
			"ToDo",
			filters={"reference_type": "Contact", "reference_name": contact.name},
			fields=["name", "description", "allocated_to", "priority"],
		)
		self.assertGreaterEqual(len(todos), 1)
		self.assertTrue(
			any(todo.allocated_to == "Administrator" and todo.priority == "High" for todo in todos)
		)

		notifications = frappe.get_all(
			"Notification Log",
			filters={"document_type": "Contact", "document_name": contact.name},
			fields=["name", "subject", "email_content"],
		)
		self.assertGreaterEqual(len(notifications), 1)
		self.assertTrue(any("Advanced flow for" in row.subject for row in notifications))

		before_save_log = self._latest_log(scenarios["before_save"].name, contact.name)
		self.assertIsNotNone(before_save_log)
		self.assertEqual(before_save_log.status, "Success")
		context_snapshot = json.loads(before_save_log.context_snapshot or "{}")
		self.assertEqual(context_snapshot.get("phone_matches", {}).get("match_count"), 1)
		self.assertEqual(context_snapshot.get("contact_changed"), True)
		self.assertEqual(context_snapshot.get("doc", {}).get("status"), "Open")

		after_insert_log = self._latest_log(scenarios["after_insert"].name, contact.name)
		self.assertIsNotNone(after_insert_log)
		path = json.loads(after_insert_log.execution_path or "[]")
		self.assertTrue(any(step.get("action") == "Call Followup Callable" for step in path))

		callable_log = self._latest_log(scenarios["callable"].name, contact.name)
		self.assertIsNotNone(callable_log)
		nested_log = self._latest_log(scenarios["nested"].name, contact.name)
		self.assertIsNotNone(nested_log)

	def test_contact_update_re_evaluates_deduplication_and_aggregations(self):
		existing_phone = "9715550200"
		existing_email = "fx.advanced.update@example.com"
		self._create_existing_contact(existing_phone, existing_email)
		scenarios = self._build_scenarios()

		contact = self._create_subject_contact("9715550299", "fx.advanced.unique@example.com").insert(
			ignore_permissions=True
		)
		contact.reload()
		self.assertEqual(contact.status, "Open")

		contact.status = "Passive"
		contact.load_doc_before_save()
		contact.set("phone_nos", [{"phone": existing_phone, "is_primary_phone": 1}])
		contact.set("email_ids", [{"email_id": existing_email, "is_primary": 1}])
		contact.validate()
		RuleCoordinator.execute_rules_from_event(contact, "Validate")

		self.assertEqual(contact.status, "Open")

		before_save_log = self._latest_log(scenarios["before_save"].name, contact.name)
		self.assertIsNotNone(before_save_log)
		context_snapshot = json.loads(before_save_log.context_snapshot or "{}")
		self.assertEqual(context_snapshot.get("phone_matches", {}).get("match_count"), 1)
		self.assertTrue(context_snapshot.get("phone_matches", {}).get("has_match"))
		path = json.loads(before_save_log.execution_path or "[]")
		self.assertTrue(any(step.get("action") == "Find Phone Duplicates" for step in path))

	def test_scheduler_rule_executes_callable_dependencies_with_batch_metadata(self):
		phone = "9715550300"
		email = "fx.advanced.scheduler@example.com"
		self._create_existing_contact(phone, email)
		scenarios = self._build_scenarios()

		contact = self._create_subject_contact(phone, email).insert(ignore_permissions=True)
		scheduler = self._create_scheduler(scenarios["scheduler"].name, contact.name)

		initial_todo_count = frappe.db.count(
			"ToDo", {"reference_type": "Contact", "reference_name": contact.name}
		)

		scheduler.execute()

		self.assertEqual(
			frappe.db.count("ToDo", {"reference_type": "Contact", "reference_name": contact.name}),
			initial_todo_count + 1,
		)

		scheduler_log = self._latest_log(scenarios["scheduler"].name, contact.name)
		self.assertIsNotNone(scheduler_log)
		self.assertEqual(scheduler_log.scheduler, scheduler.name)
		self.assertTrue(bool(scheduler_log.batch_id))
		self.assertEqual(scheduler_log.status, "Success")

		context_snapshot = json.loads(scheduler_log.context_snapshot or "{}")
		self.assertEqual(context_snapshot.get("todo_count"), initial_todo_count)
		self.assertEqual(context_snapshot.get("contact_snapshot", {}).get("name"), contact.name)

		callable_log = self._latest_log(scenarios["callable"].name, contact.name)
		self.assertIsNotNone(callable_log)
		nested_log = self._latest_log(scenarios["nested"].name, contact.name)
		self.assertIsNotNone(nested_log)

	def test_callable_raise_error_rule_fails_and_persists_log(self):
		contact = self._create_subject_contact("9715550400", "fx.advanced.error@example.com").insert(
			ignore_permissions=True
		)
		scenarios = self._build_scenarios()

		with self.assertRaises(frappe.ValidationError):
			RuleCoordinator.execute_rule(scenarios["raise_error"].name, {"doc": contact})

		error_log = self._latest_log(scenarios["raise_error"].name, contact.name)
		self.assertIsNotNone(error_log)
		self.assertEqual(error_log.status, "Failed")
		self.assertIn("Advanced flow blocked", error_log.message or "")
