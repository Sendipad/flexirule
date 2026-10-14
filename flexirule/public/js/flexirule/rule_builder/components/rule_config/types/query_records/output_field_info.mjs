/**
 * Resolve field metadata for a field name or dotted Link/child-table path.
 * Missing metadata is a valid editing state and must never break the grid render.
 */
export function resolveFieldInfo(metaByDoctype, doctype, fieldname) {
	const parts = String(fieldname || "")
		.split(".")
		.map((part) => part.trim())
		.filter(Boolean);
	if (!parts.length) return {};

	let currentDoctype = doctype;
	let resolvedField = null;
	for (let index = 0; index < parts.length; index += 1) {
		const fields = metaByDoctype?.[currentDoctype];
		if (!Array.isArray(fields)) return resolvedField || {};
		resolvedField = fields.find((field) => field.fieldname === parts[index]) || null;
		if (!resolvedField) return {};

		if (index < parts.length - 1) {
			if (
				["Link", "Table", "Table MultiSelect"].includes(resolvedField.fieldtype) &&
				resolvedField.options
			) {
				currentDoctype = resolvedField.options;
			} else {
				return resolvedField;
			}
		}
	}
	return resolvedField || {};
}
