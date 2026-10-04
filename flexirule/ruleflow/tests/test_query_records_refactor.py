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

	def test_child_table_field_query(self):
		user_email = f"child_test_{random_string(5).lower()}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": user_email,
				"first_name": "Child Table Test User",
				"roles": [{"role": "System Manager"}],
			}
		).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Query List",
				"reference_doctype": "User",
				"config": frappe.as_json(
					{
						"filters": [["User", "email", "=", user_email]],
						"fields": ["name", "roles.role"],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)
		self.assertGreaterEqual(len(result), 1)
		self.assertEqual(result[0].get("name"), user.name)

	def test_link_field_traversal_query(self):
		frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Link Traversal Test " + random_string(5),
				"assigned_by": frappe.session.user,
			}
		).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Query List",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [["ToDo", "assigned_by", "=", frappe.session.user]],
						"fields": ["name", "assigned_by"],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)

	def test_query_list_nested_filter_groups(self):
		prefix = f"NestedGrp_{random_string(5)}"
		todo1 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix} A", "status": "Open"}).insert(
			ignore_permissions=True
		)
		todo2 = frappe.get_doc({"doctype": "ToDo", "description": f"{prefix} B", "status": "Closed"}).insert(
			ignore_permissions=True
		)

		action = frappe._dict(
			{
				"operation": "Query List",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": {
							"op": "or",
							"conditions": [
								{
									"doctype": "ToDo",
									"field": "description",
									"operator": "=",
									"value": f"{prefix} A",
								},
								{
									"doctype": "ToDo",
									"field": "description",
									"operator": "=",
									"value": f"{prefix} B",
								},
							],
						},
						"fields": ["name", "description", "status"],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)
		names = [r.get("name") for r in result]
		self.assertIn(todo1.name, names)
		self.assertIn(todo2.name, names)

	def test_query_list_between_operator(self):
		todo = frappe.get_doc({"doctype": "ToDo", "description": f"BetweenTest_{random_string(5)}"}).insert(
			ignore_permissions=True
		)

		action = frappe._dict(
			{
				"operation": "Query List",
				"reference_doctype": "ToDo",
				"config": frappe.as_json(
					{
						"filters": [
							["ToDo", "creation", "between", ["2020-01-01 00:00:00", "2030-12-31 23:59:59"]],
							["ToDo", "name", "=", todo.name],
						],
						"fields": ["name", "description"],
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0].get("name"), todo.name)

	def test_exist_record_and_aggregations(self):
		prefix = f"AggTest_{random_string(5)}"
		frappe.get_doc({"doctype": "ToDo", "description": prefix, "priority": "High"}).insert(
			ignore_permissions=True
		)

		# Exist Record
		action_exist = frappe._dict(
			{
				"operation": "Exist Record",
				"reference_doctype": "ToDo",
				"config": frappe.as_json({"filters": [["ToDo", "description", "=", prefix]]}),
			}
		)
		exists_res, _ = self.handler.execute(action_exist, {}, None)
		self.assertTrue(exists_res)

		# Count
		action_count = frappe._dict(
			{
				"operation": "Count",
				"reference_doctype": "ToDo",
				"config": frappe.as_json({"filters": [["ToDo", "description", "=", prefix]]}),
			}
		)
		count_res, _ = self.handler.execute(action_count, {}, None)
		self.assertGreaterEqual(count_res, 1)

	def test_query_doc_latest_with_context_filters(self):
		user_email = f"test_{random_string(5).lower()}@example.com"
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

	def test_query_doc_concrete_normal_target(self):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Concrete Normal Target Test " + random_string(5),
			}
		).insert(ignore_permissions=True)

		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "ToDo",
				"reference_docname": todo.name,
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get doc",
						"doctype_name": "ToDo",
						"docname": todo.name,
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("name"), todo.name)

	def test_query_doc_concrete_single_target_test(self):
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "System Settings",
				"reference_docname": "",
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get Single DocType",
						"doctype_name": "System Settings",
					}
				),
			}
		)

		result, _ = self.handler.execute(action, {}, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("doctype"), "System Settings")

	def test_query_doc_dynamic_target_and_docname(self):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Dynamic Both Test " + random_string(5),
			}
		).insert(ignore_permissions=True)

		context = {"vars": {"target_dt": "ToDo", "target_id": todo.name}}
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "",
				"reference_docname": "",
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get doc",
						"doctype_name": "{vars.target_dt}",
						"docname": "{vars.target_id}",
					}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("name"), todo.name)

	def test_query_doc_concrete_doctype_dynamic_docname(self):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Concrete DT Dynamic Docname Test " + random_string(5),
			}
		).insert(ignore_permissions=True)

		context = {"vars": {"target_id": todo.name}}
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "ToDo",
				"reference_docname": "",
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get doc",
						"doctype_name": "ToDo",
						"docname": "{vars.target_id}",
					}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("name"), todo.name)

	def test_query_doc_dynamic_doctype_concrete_docname(self):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Dynamic DT Concrete Docname Test " + random_string(5),
			}
		).insert(ignore_permissions=True)

		context = {"vars": {"target_dt": "ToDo"}}
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "",
				"reference_docname": todo.name,
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get doc",
						"doctype_name": "{vars.target_dt}",
						"docname": todo.name,
					}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("name"), todo.name)

	def test_query_doc_resolver_object_config(self):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Resolver Object Test " + random_string(5),
			}
		).insert(ignore_permissions=True)

		context = {"vars": {"target_id": todo.name}}
		action = frappe._dict(
			{
				"operation": "Query Doc",
				"reference_doctype": "ToDo",
				"reference_docname": "",
				"config": frappe.as_json(
					{
						"fetch_strategy": "Get doc",
						"doctype_name": "ToDo",
						"docname": {"mode": "variable", "value": "vars.target_id"},
					}
				),
			}
		)

		result, _ = self.handler.execute(action, context, None)
		self.assertIsNotNone(result)
		self.assertEqual(result.get("name"), todo.name)
