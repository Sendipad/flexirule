import frappe
import json

def execute():
	"""
	Safe migration patch to relocate Rule.trigger_condition to Entry Action config.
	Strictly idempotent and conservative.
	"""
	rules = frappe.get_all("Rule", fields=["name", "trigger_condition"])

	for r in rules:
		try:
			doc = frappe.get_doc("Rule", r.name)

			# 1. Identify Entry Action
			entry_actions = [
				a for a in doc.actions
				if (a.get("action_type") == "Entry Action" or a.get("action_id") == "root")
			]

			if not entry_actions:
				# Case C: No entry action - should be handled by ensure_start_node but let's be safe
				doc.ensure_start_node()
				entry_action = doc.get_entry_action()
			elif len(entry_actions) > 1:
				# Case C: Multiple entry actions
				frappe.log_error(
					f"Rule {doc.name} has multiple entry actions. Skipping migration.",
					"FlexiRule Trigger Condition Migration"
				)
				continue
			else:
				entry_action = entry_actions[0]

			if not entry_action:
				continue

			# 2. Parse conditions for comparison
			legacy_cond = _parse_json(doc.trigger_condition)
			action_cond = _parse_json(entry_action.config)

			# Case D: Malformed JSON check (if they were strings and failed to parse)
			if doc.trigger_condition and legacy_cond is None:
				frappe.log_error(
					f"Rule {doc.name} has malformed legacy trigger_condition. Skipping migration.",
					"FlexiRule Trigger Condition Migration"
				)
				continue

			if entry_action.config and action_cond is None:
				frappe.log_error(
					f"Rule {doc.name} has malformed Entry Action config. Skipping migration.",
					"FlexiRule Trigger Condition Migration"
				)
				continue

			# 3. Decision Logic
			if not legacy_cond or _is_effectively_empty(legacy_cond):
				# Nothing to migrate
				continue

			if not action_cond or _is_effectively_empty(action_cond):
				# Case A: Clean Move
				_update_action_config(entry_action, doc.trigger_condition)
				doc.compile_conditions()
				frappe.db.set_value("Rule", doc.name, "compiled_expression", doc.compiled_expression, update_modified=False)
			else:
				# Both have data - check for ambiguity
				if _is_equal(legacy_cond, action_cond):
					# Already migrated (Idempotent)
					continue
				else:
					# Case B: Ambiguous Data
					frappe.log_error(
						f"Rule {doc.name} has differing conditions in Rule.trigger_condition and EntryAction.config. Skipping migration.",
						"FlexiRule Trigger Condition Migration"
					)
					continue

		except Exception as e:
			import traceback
			frappe.log_error(
				f"Migration failed for Rule {r.name}: {str(e)}\n\n{traceback.format_exc()}",
				"FlexiRule Trigger Condition Migration"
			)

def _parse_json(value):
	if not value:
		return {}
	if isinstance(value, dict | list):
		return value
	try:
		return json.loads(value)
	except (ValueError, TypeError):
		return None

def _is_effectively_empty(cond):
	if not cond:
		return True
	if isinstance(cond, list) and not cond:
		return True
	if isinstance(cond, dict):
		if not cond.get("conditions") and not cond.get("collection"):
			return True
	return False

def _is_equal(cond1, cond2):
	# Simple stable comparison
	return json.dumps(cond1, sort_keys=True) == json.dumps(cond2, sort_keys=True)

def _update_action_config(action_doc, config_value):
	# Update via frappe.db.set_value to bypass hooks as requested
	if isinstance(config_value, dict | list):
		config_value = json.dumps(config_value)

	frappe.db.set_value(
		"Rule Action",
		action_doc.name,
		"config",
		config_value,
		update_modified=False
	)
	# Update in-memory for compile_conditions
	action_doc.config = config_value
