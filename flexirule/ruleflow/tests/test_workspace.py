import unittest

import frappe


class TestRuleFlowWorkspace(unittest.TestCase):
	def test_workspace_exists_and_configured(self):
		self.assertTrue(frappe.db.exists("Workspace", "RuleFlow"))
		ws = frappe.get_doc("Workspace", "RuleFlow")
		self.assertEqual(ws.module, "Ruleflow")
		self.assertEqual(ws.public, 1)

		# Verify number cards
		card_names = [nc.number_card_name for nc in ws.number_cards]
		expected_cards = [
			"Total Rules",
			"Active Rules",
			"Inactive Rules",
			"Recently Modified Rules",
			"Total Executions",
			"Successful Executions",
		]
		for card in expected_cards:
			self.assertIn(card, card_names)

		# Verify dashboard charts
		chart_names = [c.chart_name for c in ws.charts]
		expected_charts = ["Rule Distribution by Trigger Type", "Rule Execution Activity"]
		for chart in expected_charts:
			self.assertIn(chart, chart_names)

		# Verify shortcuts
		shortcut_labels = [s.label for s in ws.shortcuts]
		expected_shortcuts = ["New Rule", "Rule List", "Rule Builder", "Execution Logs"]
		for shortcut in expected_shortcuts:
			self.assertIn(shortcut, shortcut_labels)

	def test_number_cards_calculation(self):
		from frappe.desk.doctype.number_card.number_card import get_result

		card_doc = frappe.get_doc("Number Card", "Total Rules")
		res = get_result(card_doc, filters=[])
		self.assertIsInstance(res, float)
		self.assertGreaterEqual(res, 0.0)

	def test_dashboard_charts_calculation(self):
		from frappe.desk.doctype.dashboard_chart.dashboard_chart import get

		# Create a sample rule so Group By chart has data
		rule_name = f"Test_Chart_Rule_{frappe.generate_hash(length=6)}"
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": rule_name,
				"document_type": "Test Contact",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		try:
			chart_config = get(chart_name="Rule Distribution by Trigger Type")
			self.assertIsInstance(chart_config, dict)
			self.assertIn("labels", chart_config)
			self.assertIn("datasets", chart_config)

			activity_chart = get(chart_name="Rule Execution Activity")
			self.assertIsInstance(activity_chart, dict)
			self.assertIn("labels", activity_chart)
		finally:
			frappe.delete_doc("Rule", rule.name, ignore_permissions=True)
