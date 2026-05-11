import BaseEngine from "./BaseEngine.js";
import SchemaUtils from "./schema.js";
import {
	getProcessOperationConfigFields,
	getProcessOperationDefinition,
	loadContractsFromBackend,
} from "./contracts.js";

/**
 * ProcessRuntime (ProcessEngine Logic)
 * Shared business logic for Process Adapters (Dialog & Vue).
 * Handles: Adapter Loading, Schema Resolution, Advanced Validation, DocField resolution.
 */
export default class ProcessRuntime extends BaseEngine {
	constructor(opts = {}) {
		super(opts);
		this.adapter = null;
		this.operation_def = null;
		this.schema = null;
		this.normalized_fields = [];
		this.initialized = false;
	}

	async init() {
		if (this.initialized) return;

		// 1. Load Adapter
		await this._load_adapter();

		// 2. Resolve Schema
		this.schema = this._resolve_schema();
		this.normalized_fields = await this._normalize_schema(this.schema);
		this._build_field_map(this.normalized_fields);

		// Ensure config is ready (subclasses might have set it after constructor)
		const config = this.config || {};

		// 3. Initial Dependency Evaluation
		await this.evaluate_dependencies(config, null, null, this.normalized_fields);

		// 4. Evaluate Child Rows (Recursively)
		const traverse_evaluate = async (fields, data) => {
			for (const field of fields) {
				if (field.fieldtype === "Table" && Array.isArray(data[field.fieldname])) {
					for (const row of data[field.fieldname]) {
						const table_name = row.__table_fieldname || field.fieldname;
						await this.evaluate_dependencies(
							config,
							row,
							table_name,
							this.normalized_fields
						);
						if (field.fields) {
							await traverse_evaluate(field.fields, row);
						}
					}
				}
			}
		};
		await traverse_evaluate(this.normalized_fields, config);

		this.initialized = true;
	}

	async _load_adapter() {
		await loadContractsFromBackend();
		this.operation_def = getProcessOperationDefinition(this.process_name, this.operation_name);

		// Optional composition hook for advanced/custom client behavior.
		if (!flexirule.utils.load_process_adapter) {
			return;
		}
		await flexirule.utils.load_process_adapter(this.process_name);
		this.adapter = flexirule.utils.get_process_adapter(this.process_name);

		const adapter_operation = this.adapter?.get_operation?.(this.operation_name) || null;
		if (this.operation_def && adapter_operation) {
			this.operation_def = { ...this.operation_def, ...adapter_operation };
		} else if (!this.operation_def) {
			this.operation_def = adapter_operation;
		}

		const ctx = this._get_context();
		if (this.adapter && typeof this.adapter.setup === "function") {
			await this.adapter.setup(ctx);
		}
		if (this.operation_def && typeof this.operation_def.setup === "function") {
			await this.operation_def.setup(this.config, ctx);
		}
	}

	_resolve_schema() {
		const contractFields = getProcessOperationConfigFields(
			this.process_name,
			this.operation_name
		);
		if (contractFields.length) {
			return contractFields;
		}

		if (!this.adapter) return [];
		const ctx = this._get_context();

		if (typeof this.adapter.get_schema === "function") {
			const schema = this.adapter.get_schema(this.operation_name, ctx);
			if (schema && schema.fields) return schema.fields;
			if (Array.isArray(schema)) return schema;
		}

		if (this.operation_def && typeof this.operation_def.get_config_fields === "function") {
			return this.operation_def.get_config_fields(ctx);
		}

		if (this.operation_def && this.operation_def.fields) {
			return this.operation_def.fields;
		}

		if (this.adapter.fields && !this.operation_name) {
			return this.adapter.fields;
		}

		return [];
	}

	_resolve_actions() {
		if (!this.adapter) return [];
		let actions = [];
		const ctx = this._get_context();

		if (typeof this.adapter.get_actions === "function") {
			const res = this.adapter.get_actions(this.operation_name, ctx);
			if (Array.isArray(res)) actions = actions.concat(res);
		}

		if (this.operation_def && typeof this.operation_def.get_actions === "function") {
			const res = this.operation_def.get_actions(ctx);
			if (Array.isArray(res)) actions = actions.concat(res);
		}

		return actions;
	}

	_resolve_output_schema(config) {
		if (this.operation_def?.output_schema) {
			try {
				return typeof this.operation_def.output_schema === "string"
					? JSON.parse(this.operation_def.output_schema)
					: this.operation_def.output_schema;
			} catch (_error) {
				// fall through
			}
		}
		if (this.adapter && typeof this.adapter.get_output_schema === "function") {
			const schema = this.adapter.get_output_schema(config, this._get_context());
			if (schema) return schema;
		}
		return null;
	}

	/**
	 * Custom Options Resolver for DocFields/Variables.
	 */
	async optionsResolver(field) {
		if (
			field.fieldtype === "Autocomplete" ||
			field.fieldtype === "DocField" ||
			field.fieldtype === "MultiSelectList" ||
			field.fieldtype === "MultiDocField"
		) {
			const ref = field.options;
			if (!ref) return [];

			let target = this.document_type;
			let is_meta_only = ref === "Variables" || ref === "Field Picker";

			if (
				!is_meta_only &&
				ref !== "DocField" &&
				typeof ref === "string" &&
				ref.indexOf(".") === -1
			) {
				target = ref;
			}

			const context_vars =
				typeof this.get_variable_options === "function"
					? await this.get_variable_options()
					: [];

			let fields = [];
			if (is_meta_only) {
				fields = context_vars;
			} else {
				fields = await flexirule.utils.get_combined_fields(target, context_vars);
			}

			// Autocomplete compatibility: Frappe prefers {label, value} objects
			// or primitive values. We ensure we return a clean list.
			return fields.map((f) => ({
				label: f.label || f.value || f,
				value: f.value || f,
				description: f.description || "",
			}));
		}
		return field.options;
	}

	async validate() {
		const result = await super.validate();
		const errors = result.errors;

		if (this.operation_def && typeof this.operation_def.validate === "function") {
			try {
				const customErr = await this.operation_def.validate(
					this.config,
					this._get_context()
				);
				if (customErr) {
					if (Array.isArray(customErr)) errors.push(...customErr);
					else
						errors.push(
							typeof customErr === "string" ? customErr : "Validation failed"
						);
				}
			} catch (e) {
				console.error("Validation error", e);
				errors.push(e.message);
			}
		}

		return {
			valid: errors.length === 0,
			errors: errors,
		};
	}
}
