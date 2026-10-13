/**
 * Variable Dependency Validator for FlexiRule
 *
 * Enforces reads_vars/writes_vars contracts at design-time.
 * Every reads_vars entry must be produced by a prior operation's writes_vars.
 */

frappe.provide("flexirule.validation");

// Ensure translation function is available
const __ =
	window.__ ||
	((s, args) => {
		if (!args) return s;
		if (Array.isArray(args)) {
			args.forEach((a, i) => {
				s = s.replace(`{${i}}`, a);
			});
		}
		return s;
	});

const RELEASE_DISABLED_ACTION_TYPES = new Set(["Loop", "Switch"]);
const ACTION_TYPES_REQUIRING_FALSE_PATH = new Set(["Condition"]);
const TERMINAL_ACTION_TYPES = new Set(["Stop"]);

function hasConfiguredOutputSchema(value) {
	if (value == null || value === "") return false;
	let schema = value;
	if (typeof schema === "string") {
		if (!schema.trim()) return false;
		try {
			schema = JSON.parse(schema);
		} catch (_error) {
			return true;
		}
	}
	return Array.isArray(schema) ? schema.length > 0 : Boolean(schema);
}

function supportsReturnSchema(actionType) {
	const types = window.frappe?.boot?.flexirule_contract_dto?.action_types_with_return_schema;
	return Array.isArray(types) && types.includes(actionType);
}

/**
 * Validate variable dependencies across a list of actions in topological order.
 *
 * @param {Array} actions - List of action objects with process_name, operation metadata
 * @param {Object} operation_metadata - Map of operation func_name -> { reads_vars, writes_vars }
 * @returns {Object} - { valid: boolean, errors: Array<string>, warnings: Array<string> }
 */
flexirule.validation.validate_variable_dependencies = function (actions, operation_metadata = {}) {
	const errors = [];
	const warnings = [];
	const available_vars = new Set();

	// Standard context variables always available
	available_vars.add("doc");
	available_vars.add("old_doc");
	available_vars.add("frappe");

	for (const action of actions) {
		// Skip Entry Action / Start nodes
		if (action.action_type === "Entry Action" || action.action_id === "root") {
			continue;
		}

		// Skip disabled actions
		if (action.is_enabled === 0) {
			continue;
		}

		const op_key = `${action.process_name}:${action.operation}`;
		const op_meta = operation_metadata[op_key] || {};

		// Parse reads_vars (may be array or JSON string)
		let reads_vars = [];
		if (op_meta.reads_vars) {
			try {
				reads_vars =
					typeof op_meta.reads_vars === "string"
						? JSON.parse(op_meta.reads_vars)
						: op_meta.reads_vars;
			} catch (e) {
				warnings.push(`${action.action_label}: Failed to parse reads_vars`);
			}
		}

		// Check each required variable
		if (Array.isArray(reads_vars)) {
			for (const varDef of reads_vars) {
				const varName = typeof varDef === "string" ? varDef : varDef.fieldname;
				const isRequired = typeof varDef === "object" ? varDef.reqd : 1;

				if (isRequired && varName && !available_vars.has(varName)) {
					errors.push(
						__(
							"Action '{0}' requires variable '{1}' which is not produced by any prior action",
							[action.action_label, varName]
						)
					);
				}
			}
		}

		// Parse writes_vars and add to available pool
		let writes_vars = [];
		if (op_meta.writes_vars) {
			try {
				writes_vars =
					typeof op_meta.writes_vars === "string"
						? JSON.parse(op_meta.writes_vars)
						: op_meta.writes_vars;
			} catch (e) {
				warnings.push(`${action.action_label}: Failed to parse writes_vars`);
			}
		}

		if (Array.isArray(writes_vars)) {
			for (const varDef of writes_vars) {
				const varName = typeof varDef === "string" ? varDef : varDef.fieldname;
				if (varName) {
					available_vars.add(varName);
				}
			}
		}

		// Also add return_variable if specified
		if (action.return_variable) {
			available_vars.add(action.return_variable);
		}
	}

	return {
		valid: errors.length === 0,
		errors,
		warnings,
	};
};

/**
 * Validate flow constraints (is_terminal, writes_to warnings).
 *
 * @param {Array} actions - List of action objects in topological order
 * @param {Object} operation_metadata - Map of operation key -> metadata
 * @param {Array} edges - List of edge objects { source, target }
 * @returns {Object} - { valid: boolean, errors: Array<string>, warnings: Array<string> }
 */
flexirule.validation.validate_flow_constraints = function (
	actions,
	operation_metadata = {},
	edges = []
) {
	const errors = [];
	const warnings = [];

	// Build adjacency for outgoing edges
	const outgoing = {};
	edges.forEach((e) => {
		if (!outgoing[e.source]) outgoing[e.source] = [];
		outgoing[e.source].push(e.target);
	});

	const startAction = actions.find(
		(action) => action.action_type === "Entry Action" || action.action_id === "root"
	);
	if (startAction) {
		const reachable = new Set();
		const queue = [startAction.action_id || startAction.name];

		while (queue.length) {
			const current = queue.shift();
			if (!current || reachable.has(current)) continue;
			reachable.add(current);
			(outgoing[current] || []).forEach((target) => queue.push(target));
		}

		for (const action of actions) {
			const actionId = action.action_id || action.name;
			if (!reachable.has(actionId)) {
				errors.push(
					__("Action '{0}' is unreachable from the start node.", [action.action_label])
				);
			}
		}
	}

	for (const action of actions) {
		// Skip Entry Action
		if (action.action_type === "Entry Action" || action.action_id === "root") {
			continue;
		}

		const op_key = `${action.process_name}:${action.operation}`;
		const op_meta = operation_metadata[op_key] || {};
		const action_id = action.action_id || action.name;
		const downstream = outgoing[action_id] || [];

		if (TERMINAL_ACTION_TYPES.has(action.action_type) && downstream.length > 0) {
			errors.push(
				__("{0} is terminal and should not have downstream actions", [action.action_label])
			);
		}

		if (
			ACTION_TYPES_REQUIRING_FALSE_PATH.has(action.action_type) &&
			!action.next_step_if_false
		) {
			errors.push(
				__("Action '{0}' is missing its required false path.", [action.action_label])
			);
		}

		// 1. Check is_terminal constraint
		if (op_meta.is_terminal === 1) {
			if (downstream.length > 0) {
				errors.push(
					__(
						"Action '{0}' is marked as terminal but has downstream actions. Remove connections to: {1}",
						[action.action_label, downstream.join(", ")]
					)
				);
			}
		}

		// 2. Collect writes_to warnings (Document/Database are side-effects)
		if (op_meta.writes_to === "Database") {
			warnings.push(
				__(
					"Action '{0}' writes directly to the database. This is a side-effect that cannot be rolled back.",
					[action.action_label]
				)
			);
		} else if (op_meta.writes_to === "Document") {
			warnings.push(
				__("Action '{0}' modifies the document. Ensure this is intentional.", [
					action.action_label,
				])
			);
		}

		// 3. Check can_stop_save flag
		if (op_meta.can_stop_save === 1) {
			// This is informational - not an error but worth knowing
			// Could add warning if desired
		}
	}

	return {
		valid: errors.length === 0,
		errors,
		warnings,
	};
};

/**
 * Build operation metadata map from process list.
 * This fetches reads_vars/writes_vars/is_terminal/writes_to for each operation.
 *
 * @param {Array} processes - List of process objects with operations child table
 * @returns {Object} - Map of "process_name:operation" -> metadata
 */
flexirule.validation.build_operation_metadata = function (processes) {
	const metadata = {};

	for (const proc of processes) {
		if (!proc.operations) continue;

		for (const op of proc.operations) {
			const key = `${proc.name}:${op.func_name}`;
			metadata[key] = {
				reads_vars: op.reads_vars,
				writes_vars: op.writes_vars,
				is_terminal: op.is_terminal,
				writes_to: op.writes_to,
				can_stop_save: op.can_stop_save,
				requires_doc: op.requires_doc,
				transactional: op.transactional,
				config_schema: op.config_schema,
				output_schema: op.output_schema,
			};
		}
	}

	return metadata;
};

/**
 * Validate action type-specific constraints.
 *
 * @param {Array} actions - List of action objects
 * @param {Object} operation_metadata - Map of operation key -> metadata
 * @param {String} current_rule_name - Current rule name (for Sub-Rule self-reference check)
 * @returns {Object} - { valid: boolean, errors: Array<string>, warnings: Array<string> }
 */
flexirule.validation.validate_action_types = function (
	actions,
	operation_metadata = {},
	current_rule_name = null
) {
	const errors = [];
	const warnings = [];

	for (const action of actions) {
		// Skip Entry Action
		if (action.action_type === "Entry Action" || action.action_id === "root") {
			continue;
		}

		const action_type = action.action_type;
		const label = action.action_label || action.action_id;

		if (RELEASE_DISABLED_ACTION_TYPES.has(action_type)) {
			errors.push(
				__("Action '{0}' uses {1}, which is not available in this release.", [
					label,
					action_type,
				])
			);
		}

		// Sub-Rule validation
		if (action_type === "Sub-Rule") {
			if (!action.rule) {
				errors.push(__("Action '{0}' is a Sub-Rule but no Rule is selected.", [label]));
			}
			if (action.rule && action.rule === current_rule_name) {
				errors.push(__("Action '{0}' cannot reference its own Rule as Sub-Rule.", [label]));
			}
		}

		// Condition validation
		if (action_type === "Condition") {
			if (!action.condition_json && !action.compiled_expression) {
				errors.push(
					__("Action '{0}' is a Condition but no condition is defined.", [label])
				);
			}
		}

		// Loop validation
		if (action_type === "Loop") {
			let config = {};
			try {
				config = action.config
					? typeof action.config === "string"
						? JSON.parse(action.config)
						: action.config
					: {};
			} catch (e) {
				/* ignore */
			}

			if (!config.iterator_var && !config.collection) {
				warnings.push(
					__("Action '{0}' is a Loop but iterator configuration may be incomplete.", [
						label,
					])
				);
			}
		}

		// Switch validation
		if (action_type === "Switch") {
			let config = {};
			try {
				config = action.config
					? typeof action.config === "string"
						? JSON.parse(action.config)
						: action.config
					: {};
			} catch (e) {
				/* ignore */
			}

			if (!config.cases) {
				warnings.push(__("Action '{0}' is a Switch but no cases are defined.", [label]));
			}
		}

		// Process validation: return_variable enforcement
		if (action_type === "Process" && action.process_name && action.operation) {
			const op_key = `${action.process_name}:${action.operation}`;
			const op_meta = operation_metadata[op_key] || {};

			const writes_to_context = op_meta.writes_to === "Context";
			const has_writes_vars = op_meta.writes_vars && op_meta.writes_vars !== "[]";
			const has_output_schema = !!op_meta.output_schema;

			if (
				(writes_to_context || has_writes_vars || has_output_schema) &&
				!action.return_variable
			) {
				errors.push(
					__(
						"Action '{0}' uses operation '{1}' which writes to context. Please specify a Return Variable Name.",
						[label, action.operation]
					)
				);
			}
		}

		// Mutation mode requires return variable
		if (action.mutation_mode && !action.return_variable) {
			errors.push(
				__("Action '{0}' has Mutation Mode set but no Return Variable Name is provided.", [
					label,
				])
			);
		}

		// Only action types that declare return-schema support can require a result variable.
		if (
			supportsReturnSchema(action.action_type) &&
			(action.return_type || hasConfiguredOutputSchema(action.resolved_output_schema)) &&
			!action.return_variable
		) {
			errors.push(
				__(
					"Action '{0}' defines a Return Schema but no Return Variable Name is provided.",
					[label]
				)
			);
		}
	}

	return {
		valid: errors.length === 0,
		errors,
		warnings,
	};
};
