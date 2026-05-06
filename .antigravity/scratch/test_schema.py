import json

import frappe

from flexirule.ruleflow.api import test_action_query


def test():
	# Find ANY rule to satisfy the rule_name requirement
	rule_name = frappe.db.get_value("Rule", {"is_active": 1}, "name")
	if not rule_name:
		rule_name = frappe.db.get_value("Rule", {}, "name")

	if not rule_name:
		print("No rules found")
		return

	# Get any action_id from this rule to satisfy action_id requirement
	rule_doc = frappe.get_doc("Rule", rule_name)
	if not rule_doc.actions:
		print(f"Rule {rule_name} has no actions")
		return

	action_id = rule_doc.actions[0].action_id

	node_data = {
		"action_id": action_id,
		"action_type": "Query Records",
		"action_label": "Query Records",
		"operation": "Query List",
		"config": {
			"filters": [
				{
					"doctype": "Sales Invoice",
					"field": "name",
					"operator": "like",
					"value": "%{%{doc.name}%}%",
					"value_type": "Variable",
				}
			],
			"fields": ["name", "owner", "customer", "grand_total"],
		},
		"reference_doctype": "Sales Invoice",
		"return_type": "List of Records",
	}

	try:
		print(f"Testing with rule: {rule_name}, action: {action_id}")
		res = test_action_query(rule_name=rule_name, action_id=action_id, overrides=node_data)
		print(json.dumps(res, indent=2))

		# Verify schema is present even if it might say success: False (due to execution failure)
		if res.get("schema"):
			print("\n✅ Schema detected successfully!")
			for item in res["schema"]:
				print(f"  - {item['fieldname']}: {item['label']} ({item['fieldtype']})")
		else:
			print("\n❌ Schema detection failed")

	except Exception as e:
		print(f"Test crashed: {e}")
		import traceback

		traceback.print_exc()


test()
