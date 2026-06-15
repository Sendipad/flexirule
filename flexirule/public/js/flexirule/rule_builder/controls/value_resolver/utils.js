import { toDocExpression } from "../../../core/builder_utils";

export const __ = window.__ || ((s) => s);

export { toDocExpression };

/**
 * Validates if a field exists in the given doctype metadata
 * @param {string} fieldname
 * @param {string} doctype
 * @param {Object} store - Pinia store
 * @returns {boolean}
 */
export function validateField(fieldname, doctype, store) {
	if (!fieldname || !doctype) return true;
	if (fieldname.startsWith("vars.") || fieldname.startsWith("doc.")) return true;

	const fields = store.doc_meta[doctype];
	if (!fields) return true;

	return fields.some((f) => f.fieldname === fieldname);
}
