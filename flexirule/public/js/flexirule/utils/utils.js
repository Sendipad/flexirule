/**
 * Metadata Utilities for FlexiRule
 */

frappe.provide("flexirule.utils");
frappe.provide("flexirule.meta_cache");

/**
 * Get all fields for a DocType, including standard/system fields and child table fields.
 * Results are cached globally in flexirule.meta_cache.
 *
 * @param {string} doctype - The name of the DocType
 * @param {string} prefix - Optional prefix for field values (e.g. 'doc')
 * @returns {Promise<Array>} - List of field options in {label, value, fieldtype, doctype} format
 */
flexirule.utils.get_doctype_fields = async function (doctype, prefix = "") {
	if (!doctype) return [];

	const cache_key = prefix ? `${doctype}:${prefix}` : doctype;
	if (flexirule.meta_cache[cache_key]) return flexirule.meta_cache[cache_key];

	return new Promise((resolve) => {
		frappe.model.with_doctype(doctype, async () => {
			const meta = frappe.get_meta(doctype);
			const options = [];
			const seen_fields = new Set();

			if (!meta) {
				resolve([]);
				return;
			}

			/**
			 * Internal helper to add a field option with FieldSelect-style labels.
			 */
			const add_option = (df, parent_table, table_prefix = "") => {
				if (
					frappe.model.no_value_type.includes(df.fieldtype) &&
					!["Table", "Table MultiSelect"].includes(df.fieldtype)
				)
					return;
				if (df.is_virtual) return;

				let fieldname = df.fieldname;
				if (table_prefix) {
					fieldname = `${table_prefix}.${df.fieldname}`;
				} else if (prefix) {
					fieldname = `${prefix}.${df.fieldname}`;
				}

				if (seen_fields.has(fieldname)) return;

				let label = "";
				if (parent_table === doctype) {
					label = __(df.label, null, parent_table);
					if (prefix && !table_prefix) {
						label = `${prefix}.${df.fieldname} (${label})`;
					}
				} else {
					// Match FieldSelect format: Label (Table)
					label = __(df.label, null, parent_table) + " (" + __(parent_table) + ")";
					if (table_prefix) {
						label = `${table_prefix}.${df.fieldname} (${__(
							df.label,
							null,
							parent_table
						)})`;
					}
				}

				options.push({
					label: label,
					value: fieldname,
					fieldname: df.fieldname,
					doctype: parent_table,
					fieldtype: df.fieldtype,
					options: df.options,
					// Fallback Description: Type -> Options
					description:
						df.description ||
						(df.options ? `${df.fieldtype} → ${df.options}` : df.fieldtype),
				});
				seen_fields.add(fieldname);
			};

			// 1. Standard Fields
			const stdFields = [
				{ label: __("Name"), fieldname: "name", fieldtype: "Data" },
				{ label: __("Owner"), fieldname: "owner", fieldtype: "Data" },
				{ label: __("Creation"), fieldname: "creation", fieldtype: "Datetime" },
				{ label: __("Modified"), fieldname: "modified", fieldtype: "Datetime" },
				{ label: __("Modified By"), fieldname: "modified_by", fieldtype: "Data" },
				{ label: __("DocStatus"), fieldname: "docstatus", fieldtype: "Int" },
			];
			stdFields.forEach((f) => add_option(f, doctype));

			// 2. Main Table Fields
			const fields = meta.fields || [];
			frappe.utils.sort(fields, "label", "string").forEach((df) => {
				add_option(df, doctype);
			});

			// 3. Child Tables
			const table_fields = fields.filter(
				(f) => (f.fieldtype === "Table" || f.fieldtype === "Table MultiSelect") && f.options
			);

			for (const tf of table_fields) {
				await new Promise((res) => {
					frappe.model.with_doctype(tf.options, () => {
						const child_meta = frappe.get_meta(tf.options);
						if (child_meta) {
							const child_fields = child_meta.fields || [];
							frappe.utils.sort(child_fields, "label", "string").forEach((cf) => {
								add_option(cf, tf.options, tf.fieldname);
							});
						}
						res();
					});
				});
			}

			flexirule.meta_cache[cache_key] = options;
			resolve(options);
		});
	});
};

/**
 * Combine cached doctype fields with given context variables.
 *
 * @param {string} doctype - DocType name
 * @param {Array} context_vars - List of variable objects {label, value, type}
 * @param {string} prefix - Optional prefix for DocType fields
 * @returns {Promise<Array>}
 */
flexirule.utils.get_combined_fields = async function (doctype, context_vars = [], prefix = "") {
	const base_fields = doctype ? await flexirule.utils.get_doctype_fields(doctype, prefix) : [];
	const seen_values = new Set(base_fields.map((f) => f.value));

	// Normalize variables and filter out duplicates found in base_fields
	const vars = (context_vars || [])
		.filter((v) => {
			if (seen_values.has(v.value)) return false;
			return true;
		})
		.map((v) => {
			const ft = v.fieldtype || v.type || "Data";
			return {
				...v,
				label: `${__(v.label)} (${__("Variable")})`,
				value: v.value,
				fieldtype: ft,
				type: ft, // Backward compatibility
				is_variable: true,
			};
		});

	// Reverse variables so lastly added appear first
	vars.reverse();

	// Put variables first, then base document fields
	const combined = [...vars, ...base_fields];

	return combined;
};

/**
 * Normalize operation records from API/DB/adapter into a stable object shape.
 *
 * @param {Array} operations
 * @returns {Array<{value:string, func_name:string, label:string}>}
 */
flexirule.utils.normalize_process_operations = function (operations = []) {
	return (operations || [])
		.map((op) => {
			if (typeof op === "string") {
				return { value: op, func_name: op, label: op };
			}

			const value = op?.value || op?.func_name;
			if (!value) return null;

			const config_schema = flexirule.utils.safe_json_parse(
				op?.config_schema,
				op?.config_schema
			);
			const result_schema = flexirule.utils.safe_json_parse(
				op?.result_schema || op?.output_schema,
				op?.result_schema || op?.output_schema
			);
			return {
				...op,
				value,
				func_name: op?.func_name || value,
				label: op?.label || value,
				config_schema,
				result_schema,
				output_schema: result_schema,
				ui_schema:
					op?.ui_schema ||
					(config_schema && typeof config_schema === "object"
						? config_schema.ui_schema
						: null),
			};
		})
		.filter(Boolean);
};

/**
 * Get operations for a process from backend contract DTO data.
 *
 * @param {string} process_name - Name of the process
 * @param {Array} db_operations - Optional pre-loaded operations from DB
 * @returns {Promise<Array>}
 */
flexirule.utils.get_process_operations = async function (process_name) {
	if (!process_name) return [];

	// Backend contract v2 API is authoritative.
	flexirule.meta_cache.process_operations = flexirule.meta_cache.process_operations || {};
	if (flexirule.meta_cache.process_operations[process_name]) {
		return flexirule.meta_cache.process_operations[process_name];
	}
	const response = await frappe.call({
		method: "flexirule.ruleflow.api.get_process_operations",
		args: { process_name },
	});
	const operations = flexirule.utils.normalize_process_operations(response?.message || []);
	flexirule.meta_cache.process_operations[process_name] = operations;
	return operations;
};

/**
 * Filter operations based on eligibility constraints from Process Operation metadata.
 *
 * Enforces:
 * - enabled === 1
 * - visible_in_builder === 1
 * - for_doctype matches context.document_type (or is empty)
 * - doctype_filters eval passes
 * - requires_doc is satisfied based on context.has_doc
 *
 * @param {Array} operations - List of operation objects
 * @param {Object} context - { document_type, has_doc, doctype_meta }
 * @returns {Array} - Filtered list of eligible operations
 */
flexirule.utils.filter_eligible_operations = function (operations, context = {}) {
	if (!operations || !Array.isArray(operations)) return [];

	const { document_type, has_doc = true, doctype_meta } = context;

	return operations.filter((op) => {
		// 1. Check enabled (default true if not specified)
		if (op.enabled === 0) return false;

		// 2. Check visible_in_builder (default true if not specified)
		if (op.visible_in_builder === 0) return false;

		// 3. Check for_doctype constraint
		if (op.for_doctype && document_type && op.for_doctype !== document_type) {
			return false;
		}

		// 4. Check doctype_filters (JSON array of Frappe-style filters)
		if (op.doctype_filters && doctype_meta) {
			try {
				const filters =
					typeof op.doctype_filters === "string"
						? JSON.parse(op.doctype_filters)
						: op.doctype_filters;

				if (Array.isArray(filters) && filters.length > 0) {
					// Each filter is [doctype, field, operator, value]
					// We check against doctype_meta properties
					const passes = filters.every((f) => {
						if (!Array.isArray(f) || f.length < 4) return true;
						const [, field, operator, value] = f;
						const meta_value = doctype_meta[field];

						// Simple operator support
						switch (operator) {
							case "=":
								return meta_value == value;
							case "!=":
								return meta_value != value;
							case "in":
								return Array.isArray(value) && value.includes(meta_value);
							case "not in":
								return Array.isArray(value) && !value.includes(meta_value);
							default:
								return true;
						}
					});
					if (!passes) return false;
				}
			} catch (e) {
				console.warn(`Failed to parse doctype_filters for ${op.func_name || op.name}:`, e);
			}
		}

		// 5. Check requires_doc constraint
		// If operation requires doc but context has no doc, skip it
		if (op.requires_doc === 1 && has_doc === false) {
			return false;
		}

		return true;
	});
};

/**
 * Get config fields for an operation, ensuring the adapter is loaded.
 */
flexirule.utils.get_operation_config_fields = async function (process_name, operation_name, frm) {
	if (!process_name || !operation_name) return [];
	const ops = await flexirule.utils.get_process_operations(process_name);
	const op = ops.find((row) => (row.func_name || row.value) === operation_name);
	if (!op) return [];
	if (Array.isArray(op.ui_schema)) return op.ui_schema;
	const parsed = flexirule.utils.safe_json_parse(op.config_schema, op.config_schema);
	if (Array.isArray(parsed)) return parsed;
	if (parsed && Array.isArray(parsed.ui_schema)) return parsed.ui_schema;
	if (parsed && Array.isArray(parsed.fields)) return parsed.fields;
	return [];
};

/**
 * Get field property (type and options) for a field in a DocType.
 * Useful for resolving metadata for mapped fields.
 *
 * @param {string} doctype
 * @param {string} fieldname
 * @returns {Promise<{fieldtype: string, options: string|null}>}
 */
/**
 * Get DocType metadata, ensuring it's loaded into the model.
 *
 * @param {string} doctype
 * @returns {Promise<Object>}
 */
flexirule.utils.get_doctype_meta = function (doctype) {
	if (!doctype) return Promise.resolve(null);
	return new Promise((resolve) => {
		frappe.model.with_doctype(doctype, () => {
			resolve(frappe.get_meta(doctype));
		});
	});
};

/**
 * Safely parse JSON string with error logging.
 * Returns default value on failure.
 *
 * @param {string} json_str
 * @param {any} default_val
 * @returns {any}
 */
flexirule.utils.safe_json_parse = function (json_str, default_val = null) {
	if (!json_str) return default_val;
	if (typeof json_str === "object") return json_str;
	try {
		return JSON.parse(json_str);
	} catch (e) {
		if (String(json_str) === "[object Object]") {
			console.warn(
				"JSON Parse Error: Input is '[object Object]' string. Falling back to default."
			);
		} else {
			console.warn("JSON Parse Error:", e, "Input:", json_str);
		}
		return default_val;
	}
};

/**
 * Convert string to Title Case (e.g. "create docs" -> "Create Docs")
 */
flexirule.utils.to_title_case = function (str) {
	if (!str) return "";
	return str.replace(/\w\S*/g, (txt) => {
		return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
	});
};

flexirule.utils.generate_short_id = function () {
	const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
	let result = "";
	for (let i = 0; i < 6; i++) {
		result += chars.charAt(Math.floor(Math.random() * chars.length));
	}
	return `act_${result}`;
};

flexirule.utils.debounce = function (func, wait) {
	let timeout;
	return function (...args) {
		const context = this;
		clearTimeout(timeout);
		timeout = setTimeout(() => func.apply(context, args), wait);
	};
};
