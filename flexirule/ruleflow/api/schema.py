import frappe
from frappe import _

from flexirule.ruleflow.core.permissions import require_builder_access


@frappe.whitelist()
def get_node_schema_meta(doctype: str):
	"""
	Returns the relevant metadata for a specific DocType, specifically
	to be used by the Vue GUI for dynamic node configuration.
	"""
	require_builder_access()

	if not doctype:
		frappe.throw(_("DocType is required"))

	meta = frappe.get_meta(doctype)

	fields = []
	for df in meta.fields:
		if df.hidden:
			continue

		fields.append(
			{
				"fieldname": df.fieldname,
				"fieldtype": df.fieldtype,
				"label": df.label,
				"options": df.options,
				"reqd": df.reqd,
				"default": df.default,
				"description": df.description,
				"depends_on": df.depends_on,
				"mandatory_depends_on": df.mandatory_depends_on,
				"read_only_depends_on": df.read_only_depends_on,
				"collapsible": df.collapsible,
				"hidden": df.hidden,
			}
		)

	return {"name": meta.name, "module": meta.module, "allow_rename": meta.allow_rename, "fields": fields}
