import frappe
from frappe.tests.utils import FrappeTestCase
from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity

class TestQueryRecordsRefactor(FrappeTestCase):
    def setUp(self):
        self.handler = QueryRecordsHandler()
        # Create a virtual single DocType for validation test if it doesn't exist
        if not frappe.db.exists("DocType", "Virtual Single DT"):
            frappe.get_doc({
                "doctype": "DocType",
                "name": "Virtual Single DT",
                "module": "Ruleflow",
                "issingle": 1,
                "is_virtual": 1,
                "fields": [{"fieldname": "test", "fieldtype": "Data"}]
            }).insert()

    def tearDown(self):
        frappe.db.rollback()

    def test_query_doc_get_latest_strategy(self):
        # Create some test records
        frappe.get_doc({"doctype": "User", "email": "test1@example.com", "first_name": "Test 1"}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "User", "email": "test2@example.com", "first_name": "Test 2"}).insert(ignore_permissions=True)

        action = frappe._dict({
            "operation": "Query Doc",
            "reference_doctype": "User",
            "config": frappe.as_json({
                "fetch_strategy": "Get latest Doc",
                "doctype_name": "User",
                "filters": [["User", "first_name", "like", "Test %"]]
            })
        })

        result, next_step = self.handler.execute(action, {}, None)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("first_name"), "Test 2")

    def test_query_doc_get_single_strategy(self):
        action = frappe._dict({
            "operation": "Query Doc",
            "reference_doctype": "System Settings",
            "config": frappe.as_json({
                "fetch_strategy": "Get Single DocType",
                "doctype_name": "System Settings"
            })
        })

        result, next_step = self.handler.execute(action, {}, None)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("doctype"), "System Settings")

    def test_activation_validation_virtual_single(self):
        rule_doc = frappe._dict({
            "is_active": 1,
            "actions": [
                frappe._dict({
                    "action_id": "root",
                    "action_type": "Query Records",
                    "operation": "Query Doc",
                    "action_label": "Test Query",
                    "config": frappe.as_json({
                        "doctype_name": "Virtual Single DT"
                    })
                })
            ]
        })

        with self.assertRaisesRegex(frappe.ValidationError, "Cannot execute Query Doc on a single, virtual DocType"):
            validate_graph_integrity(rule_doc)
