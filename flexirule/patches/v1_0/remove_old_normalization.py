import json

import frappe


def execute():
	"""
	Migrate legacy 'Normalization' Process actions to 'Assignment' actions with 'NormalizationResolver'.
	This preserves rule flow integrity and visual graph data.
	"""
	# 1. Migrate Rule Actions
	rule_actions = frappe.get_all(
		"Rule Action", filters={"process_name": "Normalization", "action_type": "Process"}, fields=["*"]
	)

	rules_to_update = set()

	for action in rule_actions:
		try:
			new_config = migrate_normalization_to_assignment(action)
			if not new_config:
				continue

			# Update the action record
			frappe.db.set_value(
				"Rule Action",
				action.name,
				{
					"action_type": "Assignment",
					"process_name": None,
					"operation": None,
					"config": json.dumps(new_config),
					"mutation_mode": None,
					"return_variable": None,
					"return_type": None,
					"target_field": None,
				},
				update_modified=False,
			)

			rules_to_update.add(action.parent)
		except Exception as e:
			frappe.log_error(f"Failed to migrate normalization action {action.name}: {e!s}")

	# 2. Update Visual Data in parent Rules
	for rule_name in rules_to_update:
		rule = frappe.get_doc("Rule", rule_name)
		if not rule.visual_data:
			continue

		try:
			visual_data = json.loads(rule.visual_data)
			updated = False

			# visual_data is a list of nodes and edges
			for node in visual_data:
				if not isinstance(node, dict) or node.get("type") != "process":
					continue

				node_data = node.get("data", {})
				if node_data.get("process_name") == "Normalization":
					# This is a match. Update it.
					# Note: frontend uses 'set-value' as node type for Assignment
					node["type"] = "set-value"
					node_data["action_type"] = "Assignment"
					node_data["action_label"] = node_data.get("action_label") or "Normalized Value"
					node_data["process_name"] = None
					node_data["operation"] = None

					# Find the corresponding migrated action to get the new config
					migrated_action = frappe.db.get_value(
						"Rule Action",
						{"parent": rule_name, "action_id": node_data.get("action_id")},
						["config"],
						as_dict=True,
					)

					if migrated_action:
						node_data["config"] = json.loads(migrated_action.config)

					node_data["mutation_mode"] = None
					node_data["return_variable"] = None
					node_data["target_field"] = None
					updated = True

			if updated:
				frappe.db.set_value(
					"Rule", rule.name, "visual_data", json.dumps(visual_data), update_modified=False
				)
		except Exception as e:
			frappe.log_error(f"Failed to update visual data for rule {rule_name}: {e!s}")

	# 3. Finally, delete the old 'Normalization' Process document
	if frappe.db.exists("Process", "Normalization"):
		frappe.delete_doc("Process", "Normalization", ignore_permissions=True, force=True)

	frappe.clear_cache()


def migrate_normalization_to_assignment(action):
	config = {}
	if action.config:
		try:
			config = json.loads(action.config)
		except Exception:
			return None

	op = action.operation
	assignments = []

	if op == "transform_value":
		target = get_assignment_target(action, config)
		if not target:
			return None

		assignments.append(
			{
				"target": target,
				"operator": "set",
				"value": {
					"mode": "resolver",
					"config": {
						"kind": "normalization",
						"norm_field": get_norm_field(config),
						"norm_pipeline": config.get("transformations"),
						"norm_profile": config.get("profile"),
					},
				},
			}
		)

	elif op == "mask_value":
		target = get_assignment_target(action, config)
		if not target:
			return None

		mask_type = config.get("mask_type")
		mask_op = f"mask_{mask_type}" if mask_type else "mask_partial"

		assignments.append(
			{
				"target": target,
				"operator": "set",
				"value": {
					"mode": "resolver",
					"config": {
						"kind": "normalization",
						"norm_field": get_norm_field(config),
						"norm_pipeline": [mask_op],
					},
				},
			}
		)

	elif op == "transform_multi_fields":
		source_fields = config.get("source_fields") or []
		if isinstance(source_fields, str):
			source_fields = [f.strip() for f in source_fields.split(",")]

		transformations = config.get("transformations")

		for field in source_fields:
			# For multi-field, we assume it updates the document fields directly
			assignments.append(
				{
					"target": f"doc.{field}",
					"operator": "set",
					"value": {
						"mode": "resolver",
						"config": {
							"kind": "normalization",
							"norm_field": f"doc.{field}",
							"norm_pipeline": transformations,
						},
					},
				}
			)

	return assignments


def get_assignment_target(action, config):
	mode = action.mutation_mode
	if mode in ["Set Doc Field", "Update Doc Field"]:
		field = config.get("target_field") or action.target_field
		return f"doc.{field}" if field else None

	# Default to vars
	var = action.return_variable or config.get("return_variable") or f"{action.action_id}_result"
	return f"vars.{var}"


def get_norm_field(config):
	field = config.get("source_field")
	if field:
		return f"doc.{field}"

	# If it's a value/expression, we might have a problem as NormalizationResolver expects a field path.
	# But for most cases it's a field.
	val = config.get("source_value")
	if val:
		# Try to strip {{ }} if present
		if val.startswith("{{") and val.endswith("}}"):
			val = val[2:-2].strip()
		return val

	return "doc.name"  # Fallback
