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
		{ label: "Name", fieldname: "name", fieldtype: "Data" },
		{ label: "Owner", fieldname: "owner", fieldtype: "Link", options: "User" },
		{ label: "Creation", fieldname: "creation", fieldtype: "Datetime" },
		{ label: "Modified", fieldname: "modified", fieldtype: "Datetime" },
		{ label: "Modified By", fieldname: "modified_by", fieldtype: "Link", options: "User" },
		{
			label: "DocStatus",
			fieldname: "docstatus",
			fieldtype: "Select",
			options: [
				{ label: "0 (Draft)", value: "0" },
				{ label: "1 (Submitted)", value: "1" },
				{ label: "2 (Cancelled)", value: "2" },
			],
		},
		{ label: "Index", fieldname: "idx", fieldtype: "Int" },
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

			// Main table fields
			meta.fields.forEach((f) => {
				if (!EXCLUDED_FIELDTYPES.has(f.fieldtype)) {
					fields.push({
						...f,
						original_label: f.label || f.fieldname,
						is_main: true,
					});
				}
			});

			// Standard fields
			STANDARD_FIELDS.forEach((f) => {
				fields.push({
					...f,
					original_label: f.label,
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
	 * Get fields for a DocType with configurable value and label formatting.
	 * Returns standardized objects ready for FieldPicker and ComboBoxControl.
	 *
	 * @param {string} doctype
	 * @param {string|Object} options - Alias string (legacy) or configuration object
	 * @param {string} [options.alias="doc"] - Prefix for expression mode
	 * @param {string} [options.valueMode="expression"] - "expression" (doc.field) or "fieldname" (field)
	 * @returns {Array}
	 */
	function get_fields_for_doctype(doctype, options = "doc") {
		if (!doctype || !doc_meta[doctype]) return [];

		// Handle legacy string alias or new options object
		const config = typeof options === "string" ? { alias: options } : options || {};
		const alias = config.alias !== undefined ? config.alias : "doc";
		const valueMode = config.valueMode || "expression";

		return doc_meta[doctype].map((f) => {
			const isSpecial = f.fieldname === "docstatus" || f.fieldname === "name" || f.is_std;
			const prefix = alias ? `${alias}.` : "";

			let value = f.fieldname;
			let labelSuffix = f.fieldname;

			if (valueMode === "expression") {
				value = `${prefix}${f.fieldname}`;
				labelSuffix = `${prefix}${f.fieldname}`;
			}

			return {
				...f,
				label: `${f.original_label || f.fieldname} (${labelSuffix})`,
				value: value,
				icon: isSpecial ? "fa fa-asterisk" : "fa fa-columns",
			};
		});
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
				label = row.label ?? row.title ?? value;
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
				filters: filters ? JSON.stringify(filters) : "{}",
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

	async function execute_get_query(
		df,
		search,
		reference_doctype,
		start = 0,
		page_length = 40,
		filters = {}
	) {
		if (!df || typeof df.get_query !== "function") return [];

		try {
			// Execute the native Frappe get_query function
			const query_config = await df.get_query(search || "", filters);

			if (Array.isArray(query_config)) {
				// Some custom get_query methods return an array directly
				return uniqueOptions(normalizeLinkRows(query_config));
			}

			// It returned a query configuration object { query: "...", filters: {...} }
			const target_doctype = df.options || reference_doctype;

			let method = "frappe.desk.search.search_link";
			const args = {
				doctype: target_doctype,
				txt: search || "",
				filters: "{}",
				searchfield: "name",
				start: start,
				page_length: page_length,
			};

			if (query_config && typeof query_config === "object") {
				if (query_config.query) {
					method = query_config.query;
				}
				if (query_config.filters) {
					args.filters = JSON.stringify(query_config.filters);
				}
			}

			const response = await frappe.call({
				method: method,
				args: args,
			});

			return uniqueOptions(normalizeLinkRows(response?.message || []));
		} catch (e) {
			console.warn("FlexiRule: get_query execution failed", e);
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
		execute_get_query,
		get_doctype_field_options,
		clear_option_caches,
		normalizeLinkRows,
		uniqueOptions,
	};
});
