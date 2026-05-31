import BaseEngine from "./BaseEngine.js";
import SchemaUtils from "./schema.js";
import {
	getProcessOperationConfigFields,
	getProcessOperationDefinition,
	loadContractsFromBackend,
	loadProcessScript,
} from "./contracts.js";

/**
 * ProcessRuntime (ProcessEngine Logic)
 * Shared business logic for Process Adapters (Dialog & Vue).
 * Handles: Adapter Loading, Schema Resolution, Advanced Validation, DocField resolution.
 */
export default class ProcessRuntime extends BaseEngine {
	constructor(opts = {}) {
		super(opts);
		this.operation_def = null;
		this.schema = null;
		this.normalized_fields = [];
		this.initialized = false;
	}

	async init() {
		if (this.initialized) return;

		// 1. Load backend-provided operation contract
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
				if (
					(field.fieldtype === "Table" ||
						field._source_fieldtype === "FlexiGrid" ||
						field._source_fieldtype === "flexigrid") &&
					Array.isArray(data[field.fieldname])
				) {
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
		await loadProcessScript(this.process_name);
		this.operation_def = getProcessOperationDefinition(this.process_name, this.operation_name);
	}

	_resolve_schema() {
		const contractFields = getProcessOperationConfigFields(
			this.process_name,
			this.operation_name
		);
		if (contractFields.length) {
			// Merge child fields from the JS process registry for any Table
			// field that is missing its child column definitions in the backend
			// ui_schema. This happens when the JSON fixture was generated without
			// the full child field list.
			const jsProcess = window.flexirule?.processes?.[this.process_name];
			const jsOperation = jsProcess?.get_operation?.(this.operation_name);
			const jsFields =
				typeof jsOperation?.get_config_fields === "function"
					? jsOperation.get_config_fields(this._get_context())
					: [];

			if (jsFields.length) {
				const jsFieldMap = {};
				jsFields.forEach((f) => {
					if (f.fieldname) jsFieldMap[f.fieldname] = f;
				});
				return contractFields.map((f) => {
					if (
						(f.fieldtype === "Table" ||
							f.fieldtype === "FlexiGrid" ||
							f.fieldtype === "flexigrid") &&
						(!f.fields || f.fields.length === 0)
					) {
						const jsF = jsFieldMap[f.fieldname];
						if (jsF && Array.isArray(jsF.fields) && jsF.fields.length) {
							return { ...f, fields: jsF.fields };
						}
					}
					return f;
				});
			}

			return contractFields;
		}

		// Fall back to JS-side schema definition
		const jsProcess = window.flexirule?.processes?.[this.process_name];
		const jsOperation = jsProcess?.get_operation?.(this.operation_name);
		if (typeof jsOperation?.get_config_fields === "function") {
			return jsOperation.get_config_fields(this._get_context());
		}

		return [];
	}

	_resolve_actions() {
		return [];
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
		return null;
	}

	/**
	 * Custom Options Resolver for DocFields/Variables.
	 */
	async optionsResolver(field) {
		const sourceFieldtype = field?._source_fieldtype;
		const isDocFieldLike =
			sourceFieldtype === "DocField" ||
			sourceFieldtype === "FieldPicker" ||
			field.options === "DocField";

		if (
			field.fieldtype === "Autocomplete" ||
			field.fieldtype === "DocField" ||
			field.fieldtype === "MultiSelectList" ||
			field.fieldtype === "MultiDocField"
		) {
			const ref = field.options;
			if (!ref && !isDocFieldLike) return [];

			let target = this.document_type;
			let is_meta_only =
				ref === "Variables" || ref === "Field Picker" || sourceFieldtype === "FieldPicker";

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
				// DocField-like process schemas often omit options intentionally;
				// fall back to the current rule document type in that case.
				if (!target && isDocFieldLike) {
					target = this.document_type;
				}
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
		return await super.validate();
	}
}
