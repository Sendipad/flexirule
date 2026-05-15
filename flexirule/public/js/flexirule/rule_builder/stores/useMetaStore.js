/**
 * useMetaStore — DocType metadata cache.
 *
 * Follows Frappe builder pattern (workflow_builder/store.js L16-53):
 *   - Uses frappe.model.with_doctype + frappe.get_meta
 *   - Caches metadata per doctype
 *   - Pre-fetches child table metadata
 */
import { defineStore } from "pinia";
import { ref, computed, reactive } from "vue";

export const useMetaStore = defineStore("rule-builder-meta", () => {
	// ── State ──
	const doc_meta = reactive({}); // { [doctype]: field[] }
	const fetch_counter = ref(0); // in-flight metadata requests
	const link_options_cache = reactive({});
	const doctype_fields_cache = reactive({});

	// ── Derived ──
	const meta_loading = computed(() => fetch_counter.value > 0);

	// ── Excluded field types for visual builder ──
	const EXCLUDED_FIELDTYPES = new Set([
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Button",
		"Image",
		"Fold",
		"Heading",
		"Spacer",
	]);

	// ── Standard fields available on all documents ──
	const STANDARD_FIELDS = [
		{ label: "Name (name)", fieldname: "name", fieldtype: "Data" },
		{ label: "Owner (owner)", fieldname: "owner", fieldtype: "Data" },
		{ label: "Creation (creation)", fieldname: "creation", fieldtype: "Datetime" },
		{ label: "Modified (modified)", fieldname: "modified", fieldtype: "Datetime" },
		{ label: "Modified By (modified_by)", fieldname: "modified_by", fieldtype: "Data" },
		{ label: "DocStatus (docstatus)", fieldname: "docstatus", fieldtype: "Int" },
	];

	/**
	 * Fetch metadata for a DocType and cache it.
	 * Follows Frappe pattern: frappe.model.with_doctype → frappe.get_meta
	 *
	 * @param {string} doctype - DocType name
	 * @returns {Promise<void>}
	 */
	async function fetch_metadata(doctype) {
		if (!doctype || doc_meta[doctype]) return;

		fetch_counter.value++;
		try {
			await new Promise((resolve) => {
				frappe.model.with_doctype(doctype, resolve);
			});

			const meta = frappe.get_meta(doctype);
			if (!meta) return;

			const fields = [];

			// Main table fields (doc.*)
			meta.fields.forEach((f) => {
				if (!EXCLUDED_FIELDTYPES.has(f.fieldtype)) {
					fields.push({
						label: `doc.${f.fieldname} (${f.label})`,
						value: `doc.${f.fieldname}`,
						fieldname: f.fieldname,
						fieldtype: f.fieldtype,
						options: f.options,
						is_main: true,
					});
				}
			});

			// Standard fields
			STANDARD_FIELDS.forEach((f) => {
				fields.push({
					label: `doc.${f.fieldname} (${f.label})`,
					value: `doc.${f.fieldname}`,
					fieldname: f.fieldname,
					fieldtype: f.fieldtype,
					is_std: true,
				});
			});

			// Assign reactively (spread for deep reactivity)
			doc_meta[doctype] = fields;

			// Pre-fetch child table metadata
			const tableFields = meta.fields.filter((f) => f.fieldtype === "Table" && f.options);
			for (const tf of tableFields) {
				await fetch_metadata(tf.options);
			}
		} catch (e) {
			console.warn("FlexiRule: Metadata fetch failed:", e);
			frappe.show_alert({
				message: __("Failed to fetch metadata for {0}", [doctype]),
				indicator: "orange",
			});
		} finally {
			fetch_counter.value--;
		}
	}

	/**
	 * Get fields for a DocType with an optional alias prefix.
	 *
	 * @param {string} doctype
	 * @param {string} alias - Variable prefix (default "doc")
	 * @returns {Array}
	 */
	function get_fields_for_doctype(doctype, alias = "doc") {
		if (!doctype || !doc_meta[doctype]) return [];

		return doc_meta[doctype].map((f) => ({
			...f,
			label: `${alias}.${f.fieldname} (${
				f.label.split("(")[1] ? f.label.split("(")[1].replace(")", "") : f.label
			})`,
			value: `${alias}.${f.fieldname}`,
		}));
	}

	/**
	 * Get raw Frappe meta for a DocType.
	 * @param {string} doctype
	 * @returns {Object|null}
	 */
	function get_raw_meta(doctype) {
		if (!doctype) return null;
		return frappe.get_meta(doctype);
	}

	function normalizeLinkRows(rows = []) {
		return (rows || []).reduce((acc, row, idx) => {
			let value = null;
			let label = null;
			let description = "";

			if (typeof row === "string") {
				value = row;
				label = row;
			} else if (Array.isArray(row)) {
				value = row[0];
				label = row[1] || row[0];
				description = row[2] || "";
			} else if (row && typeof row === "object") {
				value = row.value ?? row.name ?? row.id ?? row.fieldname ?? null;
				label = row.label ?? row.title ?? row.description ?? value;
				description = row.description ?? "";
			}

			const finalValue = String(value ?? "");
			const finalLabel = String(label ?? value ?? (finalValue || JSON.stringify(row)));

			if (!finalValue && finalValue !== "0") return acc;

			acc.push({
				value: finalValue,
				label: finalLabel,
				description: String(description || ""),
				_raw: row,
				_idx: idx,
			});
			return acc;
		}, []);
	}

	function uniqueOptions(rows = []) {
		const seen = new Set();
		const out = [];
		for (const row of rows || []) {
			const key = String(row?.value ?? "");
			if (!key || seen.has(key)) continue;
			seen.add(key);
			out.push(row);
		}
		return out;
	}

	function cacheKeyForLink(doctype, txt = "", filters = {}, start = 0, page_length = 40) {
		const serializedFilters = JSON.stringify(filters || {});
		return `${doctype}::${txt}::${serializedFilters}::${start}::${page_length}`;
	}

	async function search_link_options({
		doctype,
		txt = "",
		filters = {},
		start = 0,
		page_length = 40,
		force = false,
	} = {}) {
		if (!doctype || typeof doctype !== "string") return [];
		const key = cacheKeyForLink(doctype, txt, filters, start, page_length);
		if (!force && Array.isArray(link_options_cache[key])) {
			return link_options_cache[key];
		}

		const response = await frappe.call({
			method: "frappe.desk.search.search_link",
			args: {
				doctype,
				txt,
				filters: filters || {},
				start,
				page_length,
			},
		});
		const normalized = uniqueOptions(normalizeLinkRows(response?.message || []));
		link_options_cache[key] = normalized;
		return normalized;
	}

	async function get_doctype_field_options(doctype, force = false) {
		if (!doctype || typeof doctype !== "string") return [];
		if (!force && Array.isArray(doctype_fields_cache[doctype])) {
			return doctype_fields_cache[doctype];
		}
		try {
			const fields = await flexirule.utils.get_doctype_fields(doctype);
			const normalized = (fields || []).map((field, idx) => {
				const value = field?.value ?? field?.fieldname ?? `field_${idx}`;
				return {
					...field,
					value: String(value),
					label: String(field?.label || value),
					description: field?.description || "",
				};
			});
			doctype_fields_cache[doctype] = uniqueOptions(normalized);
			return doctype_fields_cache[doctype];
		} catch (_error) {
			doctype_fields_cache[doctype] = [];
			return [];
		}
	}

	function clear_option_caches() {
		Object.keys(link_options_cache).forEach((key) => delete link_options_cache[key]);
		Object.keys(doctype_fields_cache).forEach((key) => delete doctype_fields_cache[key]);
	}

	return {
		// State
		doc_meta,
		fetch_counter,

		// Computed
		meta_loading,

		// Actions
		fetch_metadata,
		get_fields_for_doctype,
		get_raw_meta,
		search_link_options,
		get_doctype_field_options,
		clear_option_caches,
		normalizeLinkRows,
		uniqueOptions,
	};
});
