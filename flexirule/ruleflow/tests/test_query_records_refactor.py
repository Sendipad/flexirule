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
