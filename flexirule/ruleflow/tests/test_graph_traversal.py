# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.core.exceptions import CycleDetectedError


class TestGraphTraversal(FrappeTestCase):
	def test_loop_detection(self):
		"""Verify that infinite loops are detected and aborted"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Infinite Loop Rule",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"is_enabled": 1,
						"next_step_if_true": "loop_node",
					},
					{
						"action_id": "loop_node",
						"action_type": "Condition",
						"action_label": "Loop Back",
						"is_enabled": 1,
						"compiled_expression": "True",
						"next_step_if_true": "loop_node",  # Cycles back
						"next_step_if_false": "node_end",
					},
					{
						"action_id": "node_end",
						"action_type": "Stop",
						"action_label": "End",
						"operation": "Success",
						"is_enabled": 1,
					},
				],
			}
		)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaisesRegex(CycleDetectedError, "Infinite loop detected"):
			engine.execute(doc)

	def test_orphan_node_behavior(self):
		"""Verify that nodes not reachable from root are ignored and flow terminates at leaf"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Orphan Node Rule",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"is_enabled": 1,
						"next_step_if_true": "node_end",
					},
					{
						"action_id": "node_end",
						"action_type": "Stop",
						"action_label": "End",
						"operation": "Success",
						"is_enabled": 1,
					},
					{
						"action_id": "orphan",
						"action_type": "Raise Error",
						"action_label": "Should never run",
						"value_template": "Orphan ran!",
						"is_enabled": 1,
					},
				],
			}
		)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)
		# Path trace should only contain root and node_end
		labels = [step["action"] for step in engine.path_trace]
		self.assertIn("Start", labels)
		self.assertIn("End", labels)
		self.assertNotIn("Should never run", labels)

	def test_complex_vueflow_payload_simulation(self):
		"""Simulate a complex payload structure as sent by the VueFlow builder"""
		# VueFlow sends visual_data as a JSON string of nodes and edges
		visual_data = [
			{"id": "root", "type": "start", "data": {"action_id": "root"}},
			{"id": "node_1", "type": "process", "data": {"action_id": "node_1"}},
			{"id": "node_end", "type": "stop", "data": {"action_id": "node_end"}},
			{"id": "edge_1", "source": "root", "target": "node_1"},
			{"id": "edge_2", "source": "node_1", "target": "node_end"},
		]

		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "VueFlow Simulated Rule",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"visual_data": json.dumps(visual_data),
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"is_enabled": 1,
						"next_step_if_true": "node_1",
					},
					{
						"action_id": "node_1",
						"action_type": "Assignment",
						"action_label": "Set Status",
						"is_enabled": 1,
						"config": '[{"target": "vars.status", "operator": "set", "value": "VueFlow OK"}]',
						"next_step_if_true": "node_end",
					},
					{
						"action_id": "node_end",
						"action_type": "Stop",
						"action_label": "End",
						"operation": "Success",
						"is_enabled": 1,
					},
				],
			}
		)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		res = engine.execute(doc)
		self.assertEqual(res["vars"]["status"], "VueFlow OK")
		self.assertEqual(len(engine.path_trace), 3)
