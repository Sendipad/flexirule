/**
 * FlexiRule action policy and contract logic module.
 * Standalone ES module for contract evaluation and testing.
 */

export let ACTION_TYPE_CONTRACT = {};
export let ACTION_TYPE_MAP = {};
export let TRIGGER_TYPE_CONTRACT = {
	"DocType Event": {
		description:
			"Runs the rule automatically when events (such as Before Save, After Save, On Submission) occur on the selected DocType.",
		required_fields: ["document_type", "trigger_event"],
		optional_fields: ["trigger_condition", "compiled_expression"],
		hidden_fields: [],
	},
	"Scheduler Event": {
		description:
			"Runs the rule automatically on a scheduled time interval or recurring schedule.",
		required_fields: [],
		optional_fields: ["document_type"],
		hidden_fields: ["trigger_event", "trigger_condition", "compiled_expression"],
	},
	"Callable Event": {
		description:
			"Runs the rule when explicitly invoked by another rule, process, or custom code.",
		required_fields: [],
		optional_fields: ["document_type", "trigger_condition", "compiled_expression"],
		hidden_fields: ["trigger_event"],
	},
};
export let RELEASE_DISABLED_ACTION_TYPES = new Set();
export let RETURN_TYPE_OPTIONS = [];
export let MUTATION_MODE_OPTIONS = [];
export let ACTION_TYPES_WITH_REFERENCE_CONTEXT = new Set();
export let ACTION_TYPES_WITH_RETURN_SCHEMA = new Set();
export let CONFIG_MODAL_TYPES = new Set();
export let PROCESS_REGISTRY = [];
export let OPERATION_REGISTRY = [];
export let OPERATION_CONTRACT = {};
export let PROCESS_OPERATION_REGISTRY_V2 = {};
export let RUNTIME_FIELD_ALIASES = {};
export let ASSIGNMENT_OPERATOR_METADATA = {};

function withDescriptions(contractMap, descriptionsMap) {
	const merged = {};
	Object.entries(contractMap || {}).forEach(([actionType, contract]) => {
		merged[actionType] = {
			...(contract || {}),
			description: descriptionsMap?.[actionType] || contract?.description || "",
		};
	});
	return merged;
}

export function applyContractDto(dto = {}) {
	const descriptions = dto.action_type_descriptions || {};

	if (dto.action_type_contract && typeof dto.action_type_contract === "object") {
		ACTION_TYPE_CONTRACT = withDescriptions(dto.action_type_contract, descriptions);
	}

	if (dto.action_type_map && typeof dto.action_type_map === "object") {
		ACTION_TYPE_MAP = { ...dto.action_type_map };
	}

	if (dto.trigger_type_contract && typeof dto.trigger_type_contract === "object") {
		TRIGGER_TYPE_CONTRACT = { ...dto.trigger_type_contract };
	}

	if (Array.isArray(dto.release_disabled_action_types)) {
		RELEASE_DISABLED_ACTION_TYPES = new Set(dto.release_disabled_action_types);
	}

	if (Array.isArray(dto.return_type_options) && dto.return_type_options.length) {
		RETURN_TYPE_OPTIONS = [...dto.return_type_options];
	}

	if (Array.isArray(dto.mutation_mode_options) && dto.mutation_mode_options.length) {
		MUTATION_MODE_OPTIONS = [...dto.mutation_mode_options];
	}

	if (Array.isArray(dto.action_types_with_reference_context)) {
		ACTION_TYPES_WITH_REFERENCE_CONTEXT = new Set(dto.action_types_with_reference_context);
	}

	if (Array.isArray(dto.action_types_with_return_schema)) {
		ACTION_TYPES_WITH_RETURN_SCHEMA = new Set(dto.action_types_with_return_schema);
	}

	if (Array.isArray(dto.config_modal_types)) {
		CONFIG_MODAL_TYPES = new Set(dto.config_modal_types);
	}

	if (dto.runtime_field_aliases && typeof dto.runtime_field_aliases === "object") {
		RUNTIME_FIELD_ALIASES = { ...dto.runtime_field_aliases };
	}

	if (Array.isArray(dto.process_registry)) {
		PROCESS_REGISTRY = [...dto.process_registry];
	}

	if (Array.isArray(dto.operation_registry)) {
		OPERATION_REGISTRY = [...dto.operation_registry];
	}

	if (dto.operation_contract && typeof dto.operation_contract === "object") {
		OPERATION_CONTRACT = { ...dto.operation_contract };
	}

	if (
		dto.process_operation_registry_v2 &&
		typeof dto.process_operation_registry_v2 === "object"
	) {
		PROCESS_OPERATION_REGISTRY_V2 = { ...dto.process_operation_registry_v2 };
	}

	if (dto.assignment_operator_metadata && typeof dto.assignment_operator_metadata === "object") {
		ASSIGNMENT_OPERATOR_METADATA = { ...dto.assignment_operator_metadata };
	}
}

export function normalizeActionType(actionType) {
	if (!actionType) return "";

	const raw = String(actionType).trim();

	if (ACTION_TYPE_CONTRACT[raw]) return raw;

	const normalized = raw.toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();

	const canonicalKeys = Object.keys(ACTION_TYPE_CONTRACT);
	const match = canonicalKeys.find((k) => k.toLowerCase() === normalized);
	if (match) return match;

	const compact = normalized.replace(/[^a-z0-9]/g, "");
	const compactMatch = canonicalKeys.find(
		(k) => k.toLowerCase().replace(/[^a-z0-9]/g, "") === compact
	);
	if (compactMatch) return compactMatch;

	return actionType;
}

export function getContract(actionType) {
	actionType = normalizeActionType(actionType);
	return (
		ACTION_TYPE_CONTRACT[actionType] || {
			required_fields: [],
			has_next_true: true,
			has_next_false: false,
			terminal: false,
		}
	);
}

function mergePolicy(basePolicy = {}, overridePolicy = {}) {
	const merged = {
		...(basePolicy || {}),
		...(overridePolicy || {}),
	};
	if (basePolicy.field_labels || overridePolicy.field_labels) {
		merged.field_labels = {
			...(basePolicy.field_labels || {}),
			...(overridePolicy.field_labels || {}),
		};
	}
	return merged;
}

function parseJsonSafe(value, fallback = null) {
	if (value == null || value === "") return fallback;
	if (typeof value === "object") return value;
	try {
		return JSON.parse(value);
	} catch (_error) {
		return fallback;
	}
}

export function getProcessDefinition(processName) {
	if (!processName) return null;
	return (PROCESS_REGISTRY || []).find((proc) => proc?.name === processName) || null;
}

export function getProcessOperationDefinition(processName, operation) {
	const process = getProcessDefinition(processName);
	if (!process || !operation) return null;
	const base =
		(process.operations || []).find(
			(op) => (op?.func_name || op?.value) === operation || op?.label === operation
		) || null;
	const v2 = PROCESS_OPERATION_REGISTRY_V2?.[processName]?.[operation] || null;
	if (!base) {
		return v2 ? { ...v2, value: operation, func_name: operation, label: operation } : null;
	}
	return v2 ? { ...base, contract_v2: v2 } : base;
}

export function getProcessOperationPolicy(processName, operation) {
	if (!processName || !operation) return {};
	const v2Policy = PROCESS_OPERATION_REGISTRY_V2?.[processName]?.[operation]?.policy || {};
	const op = getProcessOperationDefinition(processName, operation);
	const contractPolicy = op?.contract_v2?.policy || {};
	return mergePolicy(v2Policy, contractPolicy);
}

export function hasResolvedOutputSchema(value) {
	if (!value) return false;
	const schema = parseJsonSafe(value, null);
	if (!schema) return false;
	if (Array.isArray(schema)) {
		return schema.some(
			(field) => field && typeof field === "object" && Boolean(field.fieldname)
		);
	}
	if (typeof schema === "object" && schema !== null) {
		const fields = schema.fields;
		if (Array.isArray(fields)) {
			if (
				fields.some(
					(field) => field && typeof field === "object" && Boolean(field.fieldname)
				)
			) {
				return true;
			}
		}
		const props = schema.properties;
		if (
			props &&
			typeof props === "object" &&
			!Array.isArray(props) &&
			Object.keys(props).length > 0
		) {
			return true;
		}
	}
	return false;
}

export function getEffectiveActionPolicy(actionType, ctx = {}) {
	const normalizedType = normalizeActionType(actionType);
	const operation = ctx?.operation || null;
	const processName = ctx?.processName || null;
	const contract = getContract(normalizedType);
	let effective = {
		allowed_mutations: [...(contract.allowed_mutations || [])],
		allowed_return_types: [...(contract.allowed_return_types || [])],
		default_return_type: contract.default_return_type || null,
		field_labels: { ...(contract.field_labels || {}) },
		show_return_type: contract.show_return_type,
		supports_return_schema:
			ACTION_TYPES_WITH_RETURN_SCHEMA.has(normalizedType) ||
			Boolean(contract.supports_return_schema),
		require_return_type: contract.require_return_type || false,
		show_return_variable: contract.show_return_variable,
		require_return_variable: contract.require_return_variable || false,
		show_mutation_mode: contract.show_mutation_mode,
		require_mutation_mode: contract.require_mutation_mode || false,
		produces_result: contract.produces_result,
		return_variable_mode: contract.return_variable_mode || null,
	};

	if (operation) {
		effective = mergePolicy(effective, (contract.operation_policies || {})[operation] || {});
	}

	if (normalizedType === "Process" && operation) {
		effective = mergePolicy(effective, getProcessOperationPolicy(processName, operation));
	}

	effective = normalizeOutputPolicy(effective);
	return effective;
}

function normalizeOutputPolicy(policy = {}) {
	const normalized = { ...policy };
	const allowedMutations = Array.isArray(normalized.allowed_mutations)
		? normalized.allowed_mutations
		: [];
	const allowedReturnTypes = Array.isArray(normalized.allowed_return_types)
		? normalized.allowed_return_types
		: [];
	const hasStorage =
		allowedMutations.length ||
		allowedReturnTypes.length ||
		normalized.show_return_variable ||
		normalized.require_return_variable;

	if (normalized.produces_result === undefined || normalized.produces_result === null) {
		normalized.produces_result = !!hasStorage;
	}
	if (normalized.produces_result === false) {
		normalized.allowed_mutations = [];
		normalized.allowed_return_types = [];
		normalized.default_return_type = null;
		normalized.show_mutation_mode = false;
		normalized.show_return_type = false;
		normalized.supports_return_schema = false;
		if (!normalized.show_return_variable) {
			normalized.show_return_variable = false;
			normalized.require_return_variable = false;
		}
		return normalized;
	}
	if (normalized.show_mutation_mode === undefined || normalized.show_mutation_mode === null) {
		normalized.show_mutation_mode = allowedMutations.length > 0;
	}
	if (normalized.show_return_type === undefined || normalized.show_return_type === null) {
		normalized.show_return_type = allowedReturnTypes.length > 0;
	}
	if (normalized.show_return_variable === undefined || normalized.show_return_variable === null) {
		normalized.show_return_variable = !!(
			allowedMutations.length ||
			allowedReturnTypes.length ||
			normalized.require_return_variable
		);
	}
	if (!normalized.return_variable_mode) {
		normalized.return_variable_mode = "context_key";
	}
	return normalized;
}

function evaluateFieldExpression(expression, doc = {}, parent = {}) {
	if (!expression) return true;
	if (typeof expression === "boolean") return expression;
	if (typeof expression !== "string") return Boolean(expression);
	if (!expression.startsWith("eval:")) return Boolean(doc?.[expression]);
	try {
		const frappeObj = (typeof window !== "undefined" ? window : globalThis).frappe;
		return frappeObj?.utils?.eval(expression.slice(5), { doc, parent });
	} catch (_error) {
		return false;
	}
}

function getOperationRuleActionFields(operationName) {
	return OPERATION_CONTRACT?.[operationName]?.["Rule Action"] || [];
}

export function getOperationFieldOverride(actionType, fieldname, ctx = {}) {
	const operation = ctx?.operation || null;
	const processName = ctx?.processName || null;
	const merged = {};
	for (const row of getOperationRuleActionFields(actionType)) {
		if (row?.fieldname === fieldname) Object.assign(merged, row);
	}
	if (operation) {
		for (const row of getOperationRuleActionFields(operation)) {
			if (row?.fieldname === fieldname) Object.assign(merged, row);
		}
	}

	const normalizedType = normalizeActionType(actionType);
	if (normalizedType === "Process" && processName && operation) {
		const op = getProcessOperationDefinition(processName, operation);
		const actionOverrides = parseJsonSafe(op?.action_overrides, {});
		const fieldOverrides = actionOverrides?.fields || {};
		if (fieldOverrides && typeof fieldOverrides[fieldname] === "object") {
			Object.assign(merged, fieldOverrides[fieldname]);
		}
	}
	return merged;
}

export function getDerivedFieldState(actionType, fieldname, doc = {}, parent = {}, ctx = {}) {
	const override = getOperationFieldOverride(actionType, fieldname, ctx);
	const hiddenByOverride = Boolean(
		override.hidden ? evaluateFieldExpression(override.hidden, doc, parent) : false
	);
	const visibleByDepends =
		override.depends_on !== undefined
			? evaluateFieldExpression(override.depends_on, doc, parent)
			: true;
	let required = Boolean(override.reqd);
	if (override.mandatory_depends_on !== undefined) {
		required = evaluateFieldExpression(override.mandatory_depends_on, doc, parent);
	}
	const readOnly = override.read_only_depends_on
		? evaluateFieldExpression(override.read_only_depends_on, doc, parent)
		: Boolean(override.read_only);
	return {
		hidden: hiddenByOverride || !visibleByDepends,
		reqd: required,
		read_only: readOnly,
		override,
	};
}

function suggestReturnVariableName(nodeData = {}) {
	const base = String(nodeData?.operation || nodeData?.action_type || "result")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "_")
		.replace(/^_+|_+$/g, "");
	return base || "result";
}

export function applyOutputPolicyDefaults(nodeData, opts = {}) {
	if (!nodeData || !nodeData.action_type) return false;
	const preserveUserChoices = opts.preserveUserChoices !== false;
	const ctx = {
		operation: nodeData.operation,
		processName: nodeData.process_name,
	};
	const policy = getEffectiveActionPolicy(nodeData.action_type, ctx);
	const allowedMutations = policy.allowed_mutations || [];
	const allowedReturnTypes = policy.allowed_return_types || [];
	const returnVarState = getDerivedFieldState(
		nodeData.action_type,
		"return_variable",
		nodeData,
		opts.parent || {},
		ctx
	);
	const mutationState = getDerivedFieldState(
		nodeData.action_type,
		"mutation_mode",
		nodeData,
		opts.parent || {},
		ctx
	);
	let changed = false;

	if (
		nodeData.mutation_mode &&
		(!!mutationState.hidden ||
			(allowedMutations.length && !allowedMutations.includes(nodeData.mutation_mode)))
	) {
		nodeData.mutation_mode = null;
		changed = true;
	}

	if (
		nodeData.return_type &&
		allowedReturnTypes.length &&
		!allowedReturnTypes.includes(nodeData.return_type)
	) {
		nodeData.return_type = null;
		changed = true;
	}

	if (!nodeData.return_type && policy.default_return_type) {
		nodeData.return_type = policy.default_return_type;
		changed = true;
	}

	if (
		policy.show_return_type === false &&
		nodeData.return_type &&
		policy.default_return_type &&
		nodeData.return_type !== policy.default_return_type
	) {
		nodeData.return_type = policy.default_return_type;
		changed = true;
	}

	const supportsReturnSchema = policy.supports_return_schema !== false;
	const hasSchema = hasResolvedOutputSchema(nodeData.resolved_output_schema);
	const showReturnType = policy.show_return_type !== false;
	const hasReturnType =
		showReturnType && Boolean(nodeData.return_type) && nodeData.return_type !== "Yes / No";

	const needsReturnVariable =
		!!nodeData.mutation_mode ||
		(supportsReturnSchema && (hasReturnType || hasSchema)) ||
		!!policy.require_return_variable;

	if (returnVarState.hidden && nodeData.return_variable) {
		nodeData.return_variable = null;
		changed = true;
	}

	if (
		!returnVarState.hidden &&
		needsReturnVariable &&
		!nodeData.return_variable &&
		!preserveUserChoices
	) {
		nodeData.return_variable = suggestReturnVariableName(nodeData);
		changed = true;
	}

	return changed;
}

function hasConfigDoctypeName(nodeData) {
	if (!nodeData?.config) return false;
	let cfg = nodeData.config;
	if (typeof cfg === "string") {
		cfg = parseJsonSafe(cfg, {});
	}
	if (typeof cfg === "object" && cfg !== null && cfg.doctype_name) {
		const dt = cfg.doctype_name;
		if (typeof dt === "object") {
			return Boolean(dt.value || dt.mode || dt.kind || dt.family);
		}
		return Boolean(dt);
	}
	return false;
}

export function validateAgainstContract(nodeData) {
	if (!nodeData || !nodeData.action_type) {
		return { valid: true, errors: [] };
	}

	const actionType = normalizeActionType(nodeData.action_type);
	const contract = getContract(actionType);
	const policy = getEffectiveActionPolicy(actionType, {
		operation: nodeData.operation,
		processName: nodeData.process_name,
	});
	const errors = [];

	if (RELEASE_DISABLED_ACTION_TYPES.has(actionType)) {
		const globalObj = typeof window !== "undefined" ? window : globalThis;
		const translate = globalObj.__ || ((s, args) => s);
		errors.push(translate("{0} is not available in this release", [actionType]));
	}

	for (const field of contract.required_fields || []) {
		const value = nodeData[field];
		if (value === undefined || value === null || value === "") {
			if (
				field === "reference_doctype" &&
				actionType === "Query Records" &&
				hasConfigDoctypeName(nodeData)
			) {
				continue;
			}
			errors.push(`Field '${field}' is required for ${actionType}`);
		}
	}

	if (nodeData.operation && contract.mandatory_fields?.[nodeData.operation]) {
		for (const field of contract.mandatory_fields[nodeData.operation]) {
			const value = nodeData[field];
			if (value === undefined || value === null || value === "") {
				errors.push(
					`Field '${field}' is required for ${actionType} in mode ${nodeData.operation}`
				);
			}
		}
	}

	if (contract.terminal) {
		if (nodeData.next_step_if_true || nodeData.next_step_if_false) {
			errors.push(`${actionType} is terminal and should not have next steps`);
		}
	}

	if (!contract.has_next_false && nodeData.next_step_if_false) {
		errors.push(`${actionType} does not support 'next step if false'`);
	}

	if (nodeData.mutation_mode) {
		const allowed = policy.allowed_mutations || [];
		if (Array.isArray(allowed) && allowed.length && !allowed.includes(nodeData.mutation_mode)) {
			errors.push(
				`Mutation mode '${nodeData.mutation_mode}' is not allowed for ${actionType}`
			);
		}
		if (allowed.length && !nodeData.return_variable) {
			errors.push("Mutation Mode requires a Return Variable Name");
		}
	}

	if (nodeData.return_type) {
		const allowedReturnTypes = policy.allowed_return_types || [];
		if (
			Array.isArray(allowedReturnTypes) &&
			allowedReturnTypes.length &&
			!allowedReturnTypes.includes(nodeData.return_type)
		) {
			errors.push(`Return type '${nodeData.return_type}' is not allowed for ${actionType}`);
		}
	}

	if (policy.require_return_type && !nodeData.return_type) {
		errors.push("Return type is required for this operation");
	}

	if (policy.require_return_variable && !nodeData.return_variable) {
		errors.push("Return Variable Name is required for this operation");
	}

	const supportsReturnSchema = policy.supports_return_schema !== false;
	const hasSchema = hasResolvedOutputSchema(nodeData.resolved_output_schema);
	const showReturnType = policy.show_return_type !== false;
	const hasReturnType =
		showReturnType && Boolean(nodeData.return_type) && nodeData.return_type !== "Yes / No";

	if (supportsReturnSchema && (hasReturnType || hasSchema) && !nodeData.return_variable) {
		errors.push("Return Schema requires a Return Variable Name");
	}

	const requiredConfigKeys = [
		...(policy.required_config_keys || []),
		...(contract.required_config_keys || []),
	];

	if (requiredConfigKeys.length) {
		const config = parseJsonSafe(nodeData.config, {});
		for (const key of requiredConfigKeys) {
			const value = config[key];
			const isEmpty =
				value === undefined ||
				value === null ||
				value === "" ||
				(Array.isArray(value) && value.length === 0);

			if (isEmpty) {
				const label = key.charAt(0).toUpperCase() + key.slice(1);
				errors.push(`${label} is required for ${actionType}`);
			}
		}
	}

	if (actionType === "Condition" || actionType === "Loop") {
		const config = parseJsonSafe(nodeData.config, {});
		if (actionType === "Condition") {
			const globalObj = typeof window !== "undefined" ? window : globalThis;
			const { getConditionPayload } = globalObj.flexirule?.utils?.condition_payload || {};
			const payload = getConditionPayload ? getConditionPayload(nodeData) : config.conditions;

			if (!payload || (Array.isArray(payload) && payload.length === 0)) {
				errors.push("At least one condition is required");
			}
		}
		if (actionType === "Loop" && !config.iterator) {
			errors.push("Iterator is required for Loop");
		}
	}

	return {
		valid: errors.length === 0,
		errors,
	};
}
