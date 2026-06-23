import frappe


def extend_bootinfo(bootinfo):
	"""
	Inject full Action Type records into bootinfo for client-side use.
	Structure: bootinfo["action_type_map"] = { "Name": { "category": "...", ... }, ... }
	"""
	action_types = frappe.get_all("Action Type", fields=["name", "category", "is_multi_mode", "description"])

	action_type_map = {}
	for at in action_types:
		action_type_map[at.name] = {
			"category": at.category,
			"is_multi_mode": at.is_multi_mode,
			"description": at.description,
		}

	bootinfo["action_type_map"] = action_type_map
