/**
 * flexirule/core/schema.js
 * Centralized schema logic for FlexiRule.
 */

import CoreUtils from "./CoreUtils.js";

const SchemaUtils = {
	/**
	 * Standardize field definitions.
	 */
	async normalizeField(field, config, context, optionsResolver) {
		const f = { ...field };
		const sourceFieldtype = f.fieldtype;

		// 1. Standardize Flags
		f.reqd = f.reqd || 0;
		f.read_only = f.read_only || 0;
		f.hidden = f.hidden || 0;
		if (f.in_list_view === undefined) f.in_list_view = 1;

		if (f.width) f.columns = f.width;

		// 2. Map Fieldtypes
		f.fieldtype = CoreUtils.map_fieldtype(f.fieldtype);
		f._source_fieldtype = sourceFieldtype;

		// 3. Resolve Options (Initial)
		f.options = await this.resolveOptions(f, config, context, optionsResolver);

		// 4. Handle Child Tables
		if (f.fieldtype === "Table") {
			const children = f.fields || f.table_fields || [];
			if (!f._is_normalized) {
				const normalizedChildren = [];
				for (const cf of children) {
					normalizedChildren.push(
						await this.normalizeField(cf, config, context, optionsResolver)
					);
				}
				f.fields = normalizedChildren;
				f._is_normalized = true;
			}
			if (config && config[f.fieldname] === undefined) {
				config[f.fieldname] = [];
			}
		}

		if (f.fieldtype === "MultiCheck" && !f.formatter) {
			f.formatter = (value) => {
				if (Array.isArray(value)) return value.join(", ");
				return value || "";
			};
		}

		if (f.onchange && !f._onchange_logic) {
			f._onchange_logic = f.onchange;
			delete f.onchange;
		}

		return f;
	},

	/**
	 * Handles dynamic options resolution.
	 */
	async resolveOptions(field, config, context, optionsResolver) {
		const getter =
			field.get_options || (typeof field.options === "function" ? field.options : null);
		if (getter) {
			try {
				return await getter(config, context, context?.meta || context?.doc_meta);
			} catch (e) {
				console.warn(`Failed to resolve dynamic options for ${field.fieldname}`, e);
				return [];
			}
		}

		if (typeof field.options === "string") {
			if (field.options.startsWith("doc.")) {
				const key = field.options.replace("doc.", "");
				return config ? config[key] : "";
			}
			if (field.options.startsWith("vars.") || field.options.startsWith("parent.")) {
				const key = field.options.replace("vars.", "").replace("parent.", "");
				return context[key] || (context.parent ? context.parent[key] : "");
			}
		}

		if (optionsResolver) {
			return await optionsResolver(field);
		}

		return field.options || "";
	},

	/**
	 * Evaluate dependencies for a specific context (root or row).
	 */
	async evaluateDependencies(
		config,
		row,
		table_fieldname,
		fields,
		field_map,
		context,
		state_registry
	) {
		const context_id = row ? row.name : "root";
		if (!state_registry[context_id]) {
			state_registry[context_id] = {};
		}

		let target_fields = [];
		if (row) {
			if (table_fieldname) {
				const field_def = field_map[table_fieldname];
				target_fields = field_def ? field_def.fields || [] : [];
			}
		} else {
			target_fields = fields;
		}

		const eval_context = {
			...context,
			doc: row || config,
			row: row,
			parent: config,
		};

		const changes = {};

		for (const field of target_fields) {
			// Tables themselves are evaluated for visibility/mandatory, but not their columns here
			if (!row && field.fieldtype === "Table") {
				// Evaluate table itself
				await this._evaluate_single_field(
					field,
					eval_context,
					context_id,
					state_registry,
					changes
				);

				// Evaluate table columns (stored under table fieldname as shared state for all rows)
				await this.evaluateDependencies(
					config,
					{ name: field.fieldname },
					field.fieldname,
					fields,
					field_map,
					context,
					state_registry
				);
				continue;
			}

			await this._evaluate_single_field(
				field,
				eval_context,
				context_id,
				state_registry,
				changes
			);
		}

		return changes;
	},

	async _evaluate_single_field(field, eval_context, context_id, state_registry, changes) {
		const oldState = state_registry[context_id][field.fieldname] || {};
		const newState = {
			reqd: field.reqd || 0,
			read_only: field.read_only || 0,
			hidden: field.hidden || 0,
			options: null,
		};

		if (field.depends_on) {
			newState.hidden = CoreUtils.eval_condition(field.depends_on, eval_context) ? 0 : 1;
		}
		if (field.mandatory_depends_on) {
			newState.reqd = CoreUtils.eval_condition(field.mandatory_depends_on, eval_context)
				? 1
				: 0;
		}
		if (field.read_only_depends_on) {
			newState.read_only = CoreUtils.eval_condition(field.read_only_depends_on, eval_context)
				? 1
				: 0;
		}

		const has_dynamic_options =
			field.get_options ||
			typeof field.options === "function" ||
			(typeof field.options === "string" &&
				(field.options.startsWith("doc.") ||
					field.options.startsWith("vars.") ||
					field.options.startsWith("parent.")));

		if (has_dynamic_options) {
			newState.options = await this.resolveOptions(field, eval_context.doc, eval_context);
		} else {
			newState.options = field.options;
		}

		if (JSON.stringify(oldState) !== JSON.stringify(newState)) {
			changes[field.fieldname] = newState;
		}

		state_registry[context_id][field.fieldname] = newState;
	},

	/**
	 * Validates config against schema and dependency states.
	 */
	validate(config, normalized_fields, state_registry, json_schema = null) {
		const result = CoreUtils.validate_schema(config, normalized_fields, state_registry);
		if (json_schema) {
			const jsonErrors = CoreUtils.validate_json_schema(config, json_schema);
			if (jsonErrors.length > 0) {
				result.valid = false;
				result.errors.push(...jsonErrors);
			}
		}
		return result;
	},
};

export default SchemaUtils;
frappe.provide("flexirule.core");
flexirule.core.SchemaUtils = SchemaUtils;
