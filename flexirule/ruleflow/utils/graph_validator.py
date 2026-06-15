# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from flexirule.ruleflow.core.contracts import get_contract, is_release_disabled_action


def validate_graph_integrity(rule_doc):
	"""
	Validate connectivity and termination of the Rule Flow graph
	"""
	if not rule_doc.actions:
		return

	actions = {a.action_id: a for a in rule_doc.actions}
	missing_references = []

	def get_neighbors(action):
		contract = get_contract(action.get("action_type"))
		neighbors = []
		if action.get("next_step_if_true"):
			neighbors.append(action.get("next_step_if_true"))
		if contract.get("has_next_false") and action.get("next_step_if_false"):
			neighbors.append(action.get("next_step_if_false"))
		return neighbors

	for action in rule_doc.actions:
		if is_release_disabled_action(action.action_type):
			frappe.throw(
				_(
					"{0} actions are not available in this release. Remove '{1}' to activate this rule."
				).format(action.action_type, action.action_label)
			)

		if action.action_type == "Query Records" and action.operation == "Query Doc":
			config = frappe.parse_json(action.config or "{}")
			doctype_name = config.get("doctype_name")
			target_dt = None
			if isinstance(doctype_name, str):
				if not (doctype_name.startswith("{") and doctype_name.endswith("}")):
					target_dt = doctype_name
			elif isinstance(doctype_name, dict) and doctype_name.get("mode") == "static":
				target_dt = doctype_name.get("value")

			if target_dt and frappe.db.exists("DocType", target_dt):
				meta = frappe.get_meta(target_dt)
				if meta.issingle and meta.is_virtual:
					frappe.throw(
						_(
							"Action '{0}': Cannot execute Query Doc on a single, virtual DocType ({1}) as it lacks database persistence."
						).format(action.action_label or action.action_id, target_dt)
					)

		for next_step in [action.get("next_step_if_true"), action.get("next_step_if_false")]:
			if next_step and next_step not in actions:
				missing_references.append(
					_("Action '{0}' points to missing action '{1}'").format(action.action_label, next_step)
				)

	# 1. Check for Cycles (DFS with Recursion Stack)
	visited = set()
	recursion_stack = set()

	def detect_cycle(current_id):
		visited.add(current_id)
		recursion_stack.add(current_id)

		current_action = actions.get(current_id)
		neighbors = []
		if current_action:
			# Get neighbors (next steps)
			neighbors = get_neighbors(current_action)

			for neighbor in neighbors:
				if neighbor not in visited:
					if detect_cycle(neighbor):
						return True
				elif neighbor in recursion_stack:
					# Allow back-edges if the target (neighbor) is a Loop action
					neighbor_action = actions.get(neighbor)
					neighbor_type = neighbor_action.get("action_type") if neighbor_action else None
					if neighbor_type == "Loop":
						continue

					if current_action.get("action_type") != "Loop":
						return True

		recursion_stack.remove(current_id)
		return False

	# Run cycle detection from all nodes (to catch disconnected cycles too)
	for action_id in actions:
		if action_id not in visited:
			if detect_cycle(action_id):
				frappe.throw(
					_(
						"Cycle detected in Rule Graph (involving action {0}). Use 'Loop' type for iterations."
					).format(action_id)
				)

	# 2. Check for Orphan Nodes (Reachability BFS)
	# Identify Start Node(s)
	start_nodes = []

	# Priority 1: 'root' node or 'Entry Action'
	for a in rule_doc.actions:
		if a.action_id == "root" or a.action_type == "Entry Action":
			start_nodes.append(a.action_id)

	# Priority 2: Legacy 'is_entry_action'
	if not start_nodes:
		start_nodes = [a.action_id for a in rule_doc.actions if a.get("is_entry_action")]

	# Priority 3: Fallback to first action
	if not start_nodes and rule_doc.actions:
		start_nodes = [rule_doc.actions[0].action_id]

	reachable = set()
	queue = list(start_nodes)

	while queue:
		node_id = queue.pop(0)
		if node_id in reachable:
			continue
		reachable.add(node_id)

		action = actions.get(node_id)
		if action:
			queue.extend(get_neighbors(action))

	# Check for non-reachable nodes
	orphans = [qid for qid in actions if qid not in reachable]
	if orphans:
		orphan_labels = [actions[o].action_label or actions[o].action_id or str(o) for o in orphans]
		message = _("Unreachable (Orphan) Actions found: {0}").format(", ".join(orphan_labels))
		if missing_references:
			message = "{0}. {1}".format(message, missing_references[0])

		# ONLY throw if rule is active. For Drafts, we allow orphans to enable incremental building.
		if getattr(rule_doc, "is_active", 0):
			frappe.throw(message)
		else:
			# Just log as a warning for now (or let the UI handle it)
			# frappe.msgprint(message, alert=True)
			pass

	if missing_references:
		frappe.throw(missing_references[0])

	# 3. Check for Dead Ends (Paths not ending in Stop)
	for action in rule_doc.actions:
		contract = get_contract(action.action_type)
		if contract.get("terminal"):
			if action.next_step_if_true or action.next_step_if_false:
				frappe.throw(
					_("Action '{0}' is terminal and must not have outgoing paths").format(action.action_label)
				)
			continue

		if contract.get("has_next_false") and not action.next_step_if_false:
			# We do not strictly enforce next_step_if_false.
			# If it's missing, the engine safely terminates the execution path.
			pass
