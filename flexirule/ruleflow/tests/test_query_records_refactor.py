from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity


class TestQueryRecordsRefactor(FrappeTestCase):
	def setUp(self):
		self.handler = QueryRecordsHandler()
		# Use a non-existent name to avoid module import issues if possible,
		# or just use a custom doctype
		self.virtual_dt = "Virtual Single DT " + random_string(5)
		if not frappe.db.exists("DocType", self.virtual_dt):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": self.virtual_dt,
					"module": "Ruleflow",
					"custom": 1,
					"issingle": 1,
					"is_virtual": 1,
					"fields": [{"fieldname": "test", "fieldtype": "Data"}],
				}
			).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_query_doc_get_latest_strategy(self):
		# Create some test records with unique emails
		email1 = f"test_{random_string(5)}@example.com"
		email2 = f"test_{random_string(5)}@example.com"
		frappe.get_doc({"doctype": "User", "email": email1, "first_name": "Test Refactor 1"}).insert(
			ignore_permissions=True
		)
		frappe.get_doc({"doctype": "User", "email": email2, "first_name": "Test Refactor 2"}).insert(
			ignore_permissions=True
		)

		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "User",
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get latest Doc",
						"doctype_name": "User",
						"filters": [["User", "first_name", "like", "Test Refactor %"]],
					}
				),
			}
		)

		result, next_step = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)
		# Latest should be the second one created
		self.assertEqual(result.get("first_name"), "Test Refactor 2")

	def test_query_doc_get_single_strategy(self):
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "System Settings",
				"config": frappe.as_json(
					{"fetch_strategy": "Get Single DocType", "doctype_name": "System Settings"}
				),
			}
		)

		result, next_step = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("doctype"), "System Settings")

	def test_query_doc_strategies_mocked(self):
		# Create a test doc
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": f"Test Doc {random_string(5)}",
			}
		).insert(ignore_permissions=True)
		doc_name = todo.name

		# Strategy: Get doc
		action_get_doc = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{"fetch_strategy": "Get doc", "doctype_name": "ToDo", "docname": doc_name}
				),
			}
		)

		with patch("frappe.get_doc", wraps=frappe.get_doc) as mock_get_doc:
			self.handler.execute(action_get_doc, {}, None)
			# We check if it was called with the right arguments at least once
			mock_get_doc.assert_any_call("ToDo", doc_name)

		# Strategy: Get Doc from Cache
		action_get_cached = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{"fetch_strategy": "Get Doc from Cache", "doctype_name": "ToDo", "docname": doc_name}
				),
			}
		)

		with patch("frappe.get_cached_doc", wraps=frappe.get_cached_doc) as mock_get_cached:
			self.handler.execute(action_get_cached, {}, None)
			mock_get_cached.assert_called_with("ToDo", doc_name)

	def test_query_doc_dynamic_docname(self):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Dynamic Docname Test",
			}
		).insert(ignore_permissions=True)

		context = {"vars": {"target_id": todo.name}}
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{"fetch_strategy": "Get doc", "doctype_name": "ToDo", "docname": "{vars.target_id}"}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("name"), todo.name)

	def test_query_doc_latest_with_context_filters(self):
		user_email = f"test_{random_string(5)}@example.com"
		frappe.get_doc({"doctype": "User", "email": user_email, "first_name": "Context Filter Test"}).insert(
			ignore_permissions=True
		)

		context = {"vars": {"current_email": user_email}}
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "User",
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get latest Doc",
						"doctype_name": "User",
						"filters": [["User", "email", "=", "{vars.current_email}"]],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("email"), user_email)

	def test_query_doc_dynamic_doctype(self):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Dynamic Doctype Test",
			}
		).insert(ignore_permissions=True)

		context = {"vars": {"runtime_doctype": "ToDo", "todo_name": todo.name}}
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "User",  # reference_doctype should be ignored if doctype_name is provided
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get doc",
						"doctype_name": "{vars.runtime_doctype}",
						"docname": "{vars.todo_name}",
					}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("doctype"), "ToDo")
		self.assertEqual(result.get("name"), todo.name)

	def test_query_doc_single_strategy_fail_on_non_single(self):
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "User",
				"config": frappe.as_json({"fetch_strategy": "Get Single DocType", "doctype_name": "User"}),
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "is not a Single DocType"):
			self.handler.execute(action, {}, None)

	def test_activation_validation_virtual_single(self):
		rule_doc = frappe._dict(
			{
				"is_active": 1,
				"actions": [
					frappe._dict(
						{
							"action_id": "root",
							"action_type": "Query Records",
							"operation": "Query Doc",
							"action_label": "Test Query",
							"config": frappe.as_json({"doctype_name": self.virtual_dt}),
						}
					)
				],
			}
		)

		with self.assertRaisesRegex(
			frappe.ValidationError, "Cannot execute Query Doc on a single, virtual DocType"
		):
			validate_graph_integrity(rule_doc)
