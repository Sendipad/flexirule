import frappe


def ensure_action_type_exists(name, category=None, is_multi_mode=0, description=None):
	"""
	Creates an Action Type record if it doesn't exist.
	Never updates existing records for production safety.
	"""
	if not frappe.db.exists("Action Type", name):
		doc = frappe.get_doc(
			{
				"doctype": "Action Type",
				"name": name,
				"category": category or "Flow Control",
				"is_multi_mode": is_multi_mode,
				"description": description or "Auto-generated",
			}
		)
		doc.insert(ignore_permissions=True)
		return True
	return False


def seed_default_action_types():
	"""
	Seeds the default action types required for FlexiRule.
	"""
	default_types = [
		{"name": "Entry Action", "category": "Flow Control", "is_multi_mode": 0, "description": "Start node"},
		{
			"name": "Condition",
			"category": "Flow Control",
			"is_multi_mode": 0,
			"description": "Branching logic",
		},
		{
			"name": "Process",
			"category": "Process",
			"is_multi_mode": 1,
			"description": "Executes configurable operations",
		},
		{"name": "Stop", "category": "Flow Control", "is_multi_mode": 0, "description": "Terminal node"},
		{
			"name": "Raise Error",
			"category": "Flow Control",
			"is_multi_mode": 0,
			"description": "Terminal failure",
		},
		{"name": "Wait", "category": "Flow Control", "is_multi_mode": 0, "description": "Delay/sleep"},
		{
			"name": "Sub-Rule",
			"category": "Flow Control",
			"is_multi_mode": 0,
			"description": "Delegated execution",
		},
		{
			"name": "Assignment",
			"category": "Data",
			"is_multi_mode": 1,
			"description": "Batch variable/document updates",
		},
		{
			"name": "Notify",
			"category": "Communication",
			"is_multi_mode": 1,
			"description": "Multi-channel notification types",
		},
		{
			"name": "Query Records",
			"category": "Data",
			"is_multi_mode": 1,
			"description": "Data retrieval operations",
		},
		{
			"name": "Document Action",
			"category": "Data",
			"is_multi_mode": 1,
			"description": "CRUD-style operations",
		},
		{
			"name": "Loop",
			"category": "Flow Control",
			"is_multi_mode": 0,
			"description": "Iteration over datasets",
		},
		{
			"name": "Switch",
			"category": "Flow Control",
			"is_multi_mode": 0,
			"description": "Multi-branch routing",
		},
	]

	for action_type in default_types:
		ensure_action_type_exists(**action_type)
