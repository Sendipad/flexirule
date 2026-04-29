export async function get_doctype_schema(doctype) {
	if (!doctype) return [];
	if (frappe.get_meta(doctype)) {
		return frappe.get_meta(doctype).fields || [];
	}
	await frappe.model.with_doctype(doctype);
	return frappe.get_meta(doctype).fields || [];
}

export async function get_runtime_enums(doctype, fieldname) {
	const schema = await get_doctype_schema(doctype);
	const field = schema.find((f) => f.fieldname === fieldname);
	if (!field || !field.options) return [];
	return field.options.split("\n").filter((opt) => opt);
}

// Ensure the name strictly matches snake_case convention
export async function get_action_config_schema(action_type, operation = null, process_name = null) {
	// A generic resolver that could hit a backend endpoint
	// In the future, Frappe Backend should expose /api/method/...get_action_config_schema
	// For now, we fallback to dynamic lookup from contracts or meta
	try {
		// If it's a process, look up the schema from Process Operation
		if (action_type === "Process" && process_name && operation) {
			// Ideally frappe db call here if not cached in store
			const op_docs = await frappe.db.get_list("Process Operation", {
				filters: { parent: process_name, func_name: operation },
				fields: ["config_schema"],
			});
			if (op_docs && op_docs.length > 0 && op_docs[0].config_schema) {
				return typeof op_docs[0].config_schema === "string"
					? JSON.parse(op_docs[0].config_schema)
					: op_docs[0].config_schema;
			}
		}

		// Return empty schema so generic form builder can handle it cleanly
		return [];
	} catch (e) {
		console.warn("Failed to fetch schema", e);
		return [];
	}
}

/**
 * Build the Jinja path string for a document field.
 * Centralises the `doc.fieldname` vs `fieldname` decision that was
 * duplicated in InputPanel, ConditionStep, useMetaStore, ContextPicker.
 *
 * @param {{ fieldname: string }} field
 * @param {string|null} groupName  — the doctype grouping key
 * @param {string|null} primaryDoctype — the root doctype (maps to "doc")
 * @returns {string} e.g. "doc.customer_name" or "item_code"
 */
export function buildFieldJinjaPath(field, groupName, primaryDoctype) {
	if (!groupName || groupName === primaryDoctype) return `doc.${field.fieldname}`;
	return field.fieldname;
}

/**
 * Generate a short, readable node ID like "ACT-X9Y2".
 */
export function generateShortId() {
	const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
	let result = "";
	for (let i = 0; i < 4; i++) {
		result += chars.charAt(Math.floor(Math.random() * chars.length));
	}
	return "ACT-" + result;
}
