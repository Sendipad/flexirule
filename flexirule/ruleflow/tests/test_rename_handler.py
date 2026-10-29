# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.utils.rename_handler import (
	process_rename_references,
	update_action_config,
	update_condition_node,
	update_schema_json,
	update_visual_data,
)


class TestRenameHandlerUnit(FrappeTestCase):
	def test_update_condition_node_metadata_operator(self):
		node = {
			"type": "comparison",
			"operator": "is_submittable",
			"left": {"mode": "static", "value_type": "string", "value": "OldDocType"},
		}
		updated, changed = update_condition_node(node, "doctype", "OldDocType", "NewDocType")
		self.assertTrue(changed)
		self.assertEqual(updated["left"]["value"], "NewDocType")

	def test_update_condition_node_docname_static(self):
		node = {
			"type": "comparison",
			"operator": "eq",
			"left": {
				"mode": "variable",
				"path": {"scope": "doc", "segments": ["customer"]},
			},
			"right": {"mode": "static", "value_type": "string", "value": "CUST-001"},
		}
		updated, changed = update_condition_node(
			node, "docname", "CUST-001", "CUST-999", target_doctype="Customer"
		)
		self.assertTrue(changed)
		self.assertEqual(updated["right"]["value"], "CUST-999")

	def test_update_condition_node_preserves_unrelated(self):
		node = {
			"type": "comparison",
			"operator": "eq",
			"left": {
				"mode": "variable",
				"path": {"scope": "doc", "segments": ["status"]},
			},
			"right": {"mode": "static", "value_type": "string", "value": "Open"},
		}
		updated, changed = update_condition_node(
			node, "docname", "CUST-001", "CUST-999", target_doctype="Customer"
		)
		self.assertFalse(changed)
		self.assertEqual(updated["right"]["value"], "Open")

	def test_update_action_config_doctype(self):
		config = {
			"reference_doctype": "OldDocType",
			"filters": [["OldDocType", "status", "=", "Open"]],
		}
		updated, changed = update_action_config(config, "doctype", "OldDocType", "NewDocType")
		self.assertTrue(changed)
		self.assertEqual(updated["reference_doctype"], "NewDocType")
		self.assertEqual(updated["filters"][0][0], "NewDocType")

	def test_update_action_config_docname(self):
		config = {
			"reference_doctype": "Customer",
			"reference_docname": "CUST-001",
		}
		updated, changed = update_action_config(
			config, "docname", "CUST-001", "CUST-999", target_doctype="Customer"
		)
		self.assertTrue(changed)
		self.assertEqual(updated["reference_docname"], "CUST-999")

	def test_update_visual_data(self):
		visual = {
			"nodes": [
				{
					"id": "node_1",
					"data": {
						"reference_doctype": "OldDocType",
						"reference_docname": "CUST-001",
					},
				}
			]
		}
		updated, changed = update_visual_data(visual, "doctype", "OldDocType", "NewDocType")
		self.assertTrue(changed)
		self.assertEqual(updated["nodes"][0]["data"]["reference_doctype"], "NewDocType")

	def test_update_schema_json(self):
		schema = [
			{
				"fieldname": "cust",
				"fieldtype": "Link",
				"options": "OldDocType",
				"source": {"doctype": "OldDocType"},
			}
		]
		updated, changed = update_schema_json(schema, "doctype", "OldDocType", "NewDocType")
		self.assertTrue(changed)
		self.assertEqual(updated[0]["options"], "NewDocType")
		self.assertEqual(updated[0]["source"]["doctype"], "NewDocType")


class TestRenameHandlerIntegration(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.rule_name = "Test-Rename-Rule-Integration"
		if frappe.db.exists("Rule", self.rule_name):
			frappe.delete_doc("Rule", self.rule_name, force=True)

		# Create a Rule with embedded JSON references
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"trigger_type": "DocType Event",
				"document_type": "ToDo",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 5,
				"trigger_condition": json.dumps(
					{
						"type": "comparison",
						"operator": "eq",
						"left": {
							"mode": "variable",
							"path": {"scope": "doc", "segments": ["description"]},
						},
						"right": {
							"mode": "static",
							"value_type": "string",
							"value": "DOC-OLD-ID",
						},
					}
				),
				"actions": [
					{
						"action_id": "act_1",
						"action_label": "Test Action",
						"action_type": "Document Action",
						"operation": "Update Document",
						"reference_doctype": "ToDo",
						"config": json.dumps(
							{
								"reference_doctype": "ToDo",
								"reference_docname": "DOC-OLD-ID",
								"target_doctype": "ToDo",
							}
						),
					}
				],
			}
		)
		rule.insert(ignore_permissions=True)

	def tearDown(self):
		if frappe.db.exists("Rule", self.rule_name):
			frappe.delete_doc("Rule", self.rule_name, force=True)
		super().tearDown()

	def test_docname_rename_updates_rule_references(self):
		updated_rules = process_rename_references("ToDo", "DOC-OLD-ID", "DOC-NEW-ID")
		self.assertIn(self.rule_name, updated_rules)

		# Verify updated Rule content
		doc = frappe.get_doc("Rule", self.rule_name)
		cond = json.loads(doc.trigger_condition)
		self.assertEqual(cond["right"]["value"], "DOC-NEW-ID")

		act = next(a for a in doc.actions if a.action_id == "act_1")
		act_config = json.loads(act.config)
		self.assertEqual(act_config["reference_docname"], "DOC-NEW-ID")

	def test_idempotency_repeating_rename_does_not_corrupt(self):
		process_rename_references("ToDo", "DOC-OLD-ID", "DOC-NEW-ID")
		# Re-run for unrelated old name
		updated = process_rename_references("ToDo", "DOC-OLD-ID", "DOC-NEW-ID")
		self.assertEqual(updated, [])

		doc = frappe.get_doc("Rule", self.rule_name)
		cond = json.loads(doc.trigger_condition)
		self.assertEqual(cond["right"]["value"], "DOC-NEW-ID")

	def test_doctype_rename_updates_schemas_and_conditions(self):
		doc = frappe.get_doc("Rule", self.rule_name)
		doc.is_active = 0
		doc.status = "Draft"
		doc.trigger_condition = json.dumps(
			{
				"type": "comparison",
				"operator": "is_submittable",
				"left": {
					"mode": "static",
					"value_type": "string",
					"value": "OldCustomDocType",
				},
			}
		)
		doc.input_schema = json.dumps(
			[{"fieldname": "target", "fieldtype": "Link", "options": "OldCustomDocType"}]
		)
		doc.save(ignore_permissions=True)

		updated = process_rename_references("DocType", "OldCustomDocType", "NewCustomDocType")
		self.assertIn(self.rule_name, updated)

		updated_doc = frappe.get_doc("Rule", self.rule_name)
		cond = json.loads(updated_doc.trigger_condition)
		self.assertEqual(cond["left"]["value"], "NewCustomDocType")

		schema = json.loads(updated_doc.input_schema)
		self.assertEqual(schema[0]["options"], "NewCustomDocType")
