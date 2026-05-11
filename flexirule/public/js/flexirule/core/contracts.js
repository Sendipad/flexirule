/**
 * FlexiRule action contracts
 *
 * Backend is the canonical source. This module keeps a local fallback so the
 * builder still works if the contract API is temporarily unavailable.
 */

const ACTION_TYPE_DESCRIPTION = {
	"Entry Action": "The starting point of your rule flow. Defines when the rule is triggered.",
	Condition:
		"Branch your flow based on a logical condition. If true, following the 'True' path; otherwise, follow 'False'.",
	Process:
		"Execute a specific business process or operation. Operations can interact with the database, current document, or external systems.",
	Loop: "Iterate over a list of items and execute actions for each item.",
	Stop: "Terminates the rule execution as Success or Error.",
	Switch: "Direct the flow to different paths based on the value of a specific field or expression.",
	Wait: "Introduce a delay or wait for a specific event before proceeding.",
	"Sub-Rule": "Invoke another rule as a reusable component within this flow.",
	"Set Value": "Update a field in the current document with a calculated value.",
	Notify: "Send a notification as a toast, realtime message, email, Notification Log entry, or provider dispatch.",
	"Raise Error": "Stop execution immediately with a configured error message.",
	"Query Records":
		"Query records from a DocType. Supports Query List, Query Doc, Exist Record, and Query Report modes.",
	"Document Action":
		"Create, update, or delete documents, including convenience modes for linked ToDos and timeline comments.",
};

const DEFAULT_ACTION_TYPE_CONTRACT = {
	"Entry Action": {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-play", color: "#22c55e" },
	},
	Condition: {
		required_fields: ["config"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-code-fork", color: "#3b82f6" },
		validation: { frontend: "validate_condition" },
	},
	Process: {
		required_fields: ["process_name", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		dynamic_fields: true,
		css: { icon: "fa fa-cog", color: "#8b5cf6" },
	},
	Loop: {
		required_fields: ["config", "return_variable"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-refresh", color: "#f59e0b" },
		field_labels: {
			return_variable: "Item Alias",
		},
		show_return_variable: true,
		require_return_variable: true,
	},
	Stop: {
		required_fields: ["operation"],
		has_next_true: false,
		has_next_false: false,
		terminal: true,
		css: { icon: "fa fa-stop", color: "#ef4444" },
		operation_label: "Terminal Mode",
		operation_options: ["Success", "Error"],
		mandatory_fields: {
			Error: ["value_template"],
		},
	},
	Switch: {
		required_fields: ["config"],
		has_next_true: false,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-random", color: "#06b6d4" },
	},
	Wait: {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-clock-o", color: "#64748b" },
	},
	"Sub-Rule": {
		required_fields: ["rule"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-cube", color: "#ec4899" },
	},
	"Set Value": {
		required_fields: ["operation", "value_template"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		operation_label: "Target Type",
		operation_options: ["Current Document", "Context Variable", "Reference Document"],
		allowed_mutations: [],
		allowed_return_types: ["Yes / No", "Single Record", "List of Values"],
		css: { icon: "fa fa-edit", color: "#14b8a6" },
		default_return_type: "Yes / No",
		show_return_type: false,
		require_return_type: false,
		operation_policies: {
			"Current Document": {
				allowed_mutations: [
					"Set Doc Field",
					"Update Doc Field",
					"Set Context Variable",
					"Update Context Variable",
				],
				allowed_return_types: ["Yes / No"],
				default_return_type: "Yes / No",
				show_return_type: false,
				require_return_type: false,
				field_labels: {
					target_field: "Current Document Field",
					value_template: "New Field Value Template",
					mutation_mode: "Result Handling (Optional)",
					return_variable: "Result Variable Name (Optional)",
				},
			},
			"Context Variable": {
				allowed_mutations: ["Set Context Variable", "Update Context Variable"],
				allowed_return_types: ["Yes / No"],
				default_return_type: "Yes / No",
				show_return_type: false,
				require_return_type: false,
				field_labels: {
					variable_name: "Context Variable Name",
					value_template: "Variable Value Template",
					mutation_mode: "Result Handling (Optional)",
					return_variable: "Result Variable Name (Optional)",
				},
			},
			"Reference Document": {
				allowed_mutations: ["Set Doc Field", "Update Doc Field"],
				allowed_return_types: ["Yes / No"],
				default_return_type: "Yes / No",
				show_return_type: false,
				require_return_type: false,
				field_labels: {
					reference_doctype: "Reference DocType",
					reference_docname: "Reference Document Name",
					target_field: "Reference Document Field",
					value_template: "New Field Value Template",
					mutation_mode: "Result Handling (Optional)",
					return_variable: "Result Variable Name (Optional)",
				},
			},
		},
		validation: {
			check_target_field_editable: true,
		},
		field_labels: {
			operation: "Target Type",
			target_field: "Field to Update",
			value_template: "Value Template",
			reference_doctype: "Target DocType",
			reference_docname: "Target Record",
			variable_name: "Variable Name",
		},
	},
	Notify: {
		required_fields: ["value_template", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-bell", color: "#0ea5e9" },
		operation_label: "Notification Type",
		operation_options: ["Toast", "System", "Email", "System Notification", "Provider"],
		operation_policies: {
			Email: {
				required_config_keys: ["subject", "recipients"],
			},
			"System Notification": {
				required_config_keys: ["subject"],
			},
			Provider: {
				required_config_keys: ["provider", "recipient"],
			},
		},
	},
	"Raise Error": {
		required_fields: ["value_template"],
		has_next_true: false,
		has_next_false: false,
		terminal: true,
		css: { icon: "fa fa-exclamation-triangle", color: "#dc2626" },
		field_labels: {
			value_template: "Error Message Template",
			config: "Error Details",
		},
	},
	"Query Records": {
		required_fields: ["reference_doctype", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		allowed_mutations: [
			"Set Context Variable",
			"Append to Context Variable",
			"Update Context Variable",
		],
		css: { icon: "fa fa-search", color: "#0891b2" },
		operation_label: "Query Mode",
		operation_options: [
			"Query List",
			"Query Doc",
			"Exist Record",
			"Query Report",
			"Count",
			"Sum",
			"Average",
			"Min",
			"Max",
			"Group By",
		],
		mandatory_fields: {
			"Exist Record": ["reference_doctype"],
		},
	},
	"Document Action": {
		required_fields: ["reference_doctype", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		operation_label: "Document Mode",
		operation_options: [
			"Create New",
			"Update Existing",
			"Delete Record",
			"Create ToDo",
			"Add Comment",
		],
		allowed_mutations: ["Set Doc Field", "Set Context Variable"],
		operation_policies: {
			"Create New": {
				allowed_return_types: ["Single Record", "Full Document"],
				default_return_type: "Single Record",
				allowed_mutations: ["Set Context Variable", "Update Context Variable"],
				show_return_type: true,
				require_return_type: true,
				field_labels: { return_type: "Created Document Output" },
			},
			"Update Existing": {
				allowed_return_types: ["Single Record", "Full Document"],
				default_return_type: "Single Record",
				allowed_mutations: [
					"Set Context Variable",
					"Update Context Variable",
					"Set Doc Field",
				],
				show_return_type: true,
				require_return_type: true,
				field_labels: { return_type: "Updated Document Output" },
			},
			"Delete Record": {
				allowed_return_types: ["Yes / No"],
				default_return_type: "Yes / No",
				allowed_mutations: ["Set Context Variable"],
				show_return_type: false,
				require_return_type: false,
				field_labels: { return_type: "Deletion Result Type" },
			},
			"Create ToDo": {
				allowed_return_types: ["Single Record"],
				default_return_type: "Single Record",
				allowed_mutations: ["Set Context Variable", "Update Context Variable"],
				show_return_type: false,
				require_return_type: false,
				required_config_keys: ["assigned_to", "description"],
				field_labels: { return_type: "ToDo Output Type" },
			},
			"Add Comment": {
				allowed_return_types: ["Single Record"],
				default_return_type: "Single Record",
				allowed_mutations: ["Set Context Variable", "Update Context Variable"],
				show_return_type: false,
				require_return_type: false,
				required_config_keys: ["comment_text"],
				field_labels: { return_type: "Comment Output Type" },
			},
		},
		css: { icon: "fa fa-file-text", color: "#059669" },
	},
};

const DEFAULT_TRIGGER_TYPE_CONTRACT = {
	"DocType Event": {
		required_fields: ["document_type", "trigger_event"],
		optional_fields: ["trigger_condition", "compiled_expression"],
		hidden_fields: [],
	},
	"Scheduler Event": {
		required_fields: [],
		optional_fields: ["document_type"],
		hidden_fields: ["trigger_event", "trigger_condition", "compiled_expression"],
	},
	"Callable Event": {
		required_fields: [],
		optional_fields: ["document_type", "trigger_condition", "compiled_expression"],
		hidden_fields: ["trigger_event"],
	},
};

const DEFAULT_RELEASE_DISABLED_ACTION_TYPES = ["Switch"];
const DEFAULT_RETURN_TYPE_OPTIONS = [
	"Yes / No",
	"Single Record",
	"List of Values",
	"List of Records",
	"Full Document",
];
const DEFAULT_MUTATION_MODE_OPTIONS = [
	"Set Doc Field",
	"Update Doc Field",
	"Set Context Variable",
	"Update Context Variable",
	"Append to Context Variable",
	"Batch Database Set",
];

const DEFAULT_ACTION_TYPES_WITH_REFERENCE_CONTEXT = [
	"Query Records",
	"Document Action",
	"Process",
	"Set Value",
];
const DEFAULT_ACTION_TYPES_WITH_RETURN_SCHEMA = ["Process", "Query Records", "Document Action"];
const DEFAULT_CONFIG_MODAL_TYPES = [
	"Process",
	"Condition",
	"Set Value",
	"Stop",
	"Raise Error",
	"Notify",
	"Wait",
	"Sub-Rule",
	"Document Action",
	"Loop",
];

export let ACTION_TYPE_CONTRACT = withDescriptions(DEFAULT_ACTION_TYPE_CONTRACT);
export let TRIGGER_TYPE_CONTRACT = { ...DEFAULT_TRIGGER_TYPE_CONTRACT };
export let RELEASE_DISABLED_ACTION_TYPES = new Set(DEFAULT_RELEASE_DISABLED_ACTION_TYPES);
export let RETURN_TYPE_OPTIONS = [...DEFAULT_RETURN_TYPE_OPTIONS];
export let MUTATION_MODE_OPTIONS = [...DEFAULT_MUTATION_MODE_OPTIONS];
export let ACTION_TYPES_WITH_REFERENCE_CONTEXT = new Set(
	DEFAULT_ACTION_TYPES_WITH_REFERENCE_CONTEXT
);
export let ACTION_TYPES_WITH_RETURN_SCHEMA = new Set(DEFAULT_ACTION_TYPES_WITH_RETURN_SCHEMA);
export let CONFIG_MODAL_TYPES = new Set(DEFAULT_CONFIG_MODAL_TYPES);
export let PROCESS_REGISTRY = [];
export let OPERATION_REGISTRY = [];
export let OPERATION_CONTRACT = {};
export let PROCESS_OPERATION_POLICIES = {};
export let RUNTIME_FIELD_ALIASES = {};

let _contractsLoaded = false;
const CONTRACT_CACHE_KEY = "flexirule:contract_dto:v1";

function withDescriptions(contractMap) {
	const merged = {};
	Object.entries(contractMap || {}).forEach(([actionType, contract]) => {
		merged[actionType] = {
			...(contract || {}),
			description: ACTION_TYPE_DESCRIPTION[actionType] || contract?.description || "",
		};
	});
	return merged;
}

function applyContractDto(dto = {}) {
	if (dto.action_type_contract && typeof dto.action_type_contract === "object") {
		ACTION_TYPE_CONTRACT = withDescriptions(dto.action_type_contract);
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

	if (dto.process_operation_policies && typeof dto.process_operation_policies === "object") {
		PROCESS_OPERATION_POLICIES = { ...dto.process_operation_policies };
	}
}

function getCachedContractDto() {
	try {
		const raw = window.sessionStorage?.getItem(CONTRACT_CACHE_KEY);
		if (!raw) return null;
		return JSON.parse(raw);
	} catch (_error) {
		return null;
	}
}

function setCachedContractDto(dto) {
	try {
		window.sessionStorage?.setItem(CONTRACT_CACHE_KEY, JSON.stringify(dto || {}));
	} catch (_error) {
		// Ignore storage failures.
	}
}

export async function loadContractsFromBackend(force = false) {
	if (_contractsLoaded && !force) return;
	if (!window.frappe?.call) return;

	const bootDto = window.frappe?.boot?.flexirule_contract_dto;
	if (bootDto && typeof bootDto === "object" && !force) {
		applyContractDto(bootDto);
		setCachedContractDto(bootDto);
		_contractsLoaded = true;
		return;
	}

	if (!force) {
		const cachedDto = getCachedContractDto();
		if (cachedDto && typeof cachedDto === "object") {
			applyContractDto(cachedDto);
			_contractsLoaded = true;
		}
	}

	try {
		const response = await frappe.call({
			method: "flexirule.ruleflow.api.get_contract_dto",
		});
		if (response?.message) {
			applyContractDto(response.message);
			setCachedContractDto(response.message);
			_contractsLoaded = true;
		}
	} catch (_error) {
		// Keep local fallbacks silently.
	}
}

// Fire-and-forget canonical sync.
loadContractsFromBackend();

/**
 * Get contract for an action type with sensible defaults.
 */
export function getContract(actionType) {
	actionType = normalizeActionType(actionType);
	return (
		ACTION_TYPE_CONTRACT[actionType] || {
			required_fields: [],
			has_next_true: true,
			has_next_false: false,
			terminal: false,
			icon: "fa fa-circle",
			color: "#6b7280",
		}
	);
}

export function normalizeActionType(actionType) {
	if (!actionType) return "";

	const raw = String(actionType).trim();

	// 1. Direct match with canonical keys
	if (ACTION_TYPE_CONTRACT[raw]) return raw;

	// 2. Try to map hyphenated/machine types back to canonical
	// Normalized for easy lookup: e.g. "set-value" -> "set value"
	const normalized = raw.toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();

	// Case-insensitive direct match: "set value" -> "Set Value"
	const canonicalKeys = Object.keys(ACTION_TYPE_CONTRACT);
	const match = canonicalKeys.find((k) => k.toLowerCase() === normalized);
	if (match) return match;

	// 3. Compact match for common UI variants:
	//    "setvalue" -> "Set Value", "subrule" / "sub-rule" -> "Sub-Rule"
	const compact = normalized.replace(/[^a-z0-9]/g, "");
	const compactMatch = canonicalKeys.find(
		(k) => k.toLowerCase().replace(/[^a-z0-9]/g, "") === compact
	);
	if (compactMatch) return compactMatch;

	return actionType;
}

/**
 * Check if action type terminates the flow.
 */
export function isTerminalAction(actionType) {
	return getContract(actionType).terminal || false;
}

/**
 * Get required fields for an action type.
 */
export function getRequiredFields(actionType) {
	return getContract(actionType).required_fields || [];
}

export function getTriggerTypeContract(triggerType) {
	return (
		TRIGGER_TYPE_CONTRACT[triggerType] || {
			required_fields: [],
			optional_fields: [],
			hidden_fields: [],
		}
	);
}

export function getReturnTypeOptions() {
	return [...RETURN_TYPE_OPTIONS];
}

export function getMutationModeOptions() {
	return [...MUTATION_MODE_OPTIONS];
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
	return (
		(process.operations || []).find(
			(op) => (op?.func_name || op?.value) === operation || op?.label === operation
		) || null
	);
}

export function getProcessOperationConfigFields(processName, operation) {
	const op = getProcessOperationDefinition(processName, operation);
	if (!op) return [];
	const parsed = parseJsonSafe(op.config_schema, op.config_schema);
	if (Array.isArray(parsed)) return parsed;
	if (parsed && Array.isArray(parsed.fields)) return parsed.fields;
	return [];
}

export function getProcessOperationPolicy(processName, operation) {
	if (!processName || !operation) return {};
	const basePolicy = PROCESS_OPERATION_POLICIES?.[processName]?.[operation] || {};
	const op = getProcessOperationDefinition(processName, operation);
	const actionOverrides = parseJsonSafe(op?.action_overrides, {});
	const overridePolicy =
		actionOverrides && typeof actionOverrides.policy === "object" ? actionOverrides.policy : {};
	return mergePolicy(basePolicy, overridePolicy);
}

function evaluateFieldExpression(expression, doc = {}, parent = {}) {
	if (!expression) return true;
	if (typeof expression === "boolean") return expression;
	if (typeof expression !== "string") return Boolean(expression);
	if (!expression.startsWith("eval:")) return Boolean(doc?.[expression]);
	try {
		return frappe.utils.eval(expression.slice(5), { doc, parent });
	} catch (_error) {
		return true;
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

export function getOperationOptions(actionType, ctx = {}) {
	const normalizedType = normalizeActionType(actionType);
	const processName = ctx?.processName || null;

	const fromRegistry = (OPERATION_REGISTRY || []).filter((row) => {
		if (row?.action_type !== normalizedType) return false;
		if (normalizedType !== "Process") return !row?.process_name;
		if (!processName) return true;
		return row?.process_name === processName;
	});

	if (fromRegistry.length) {
		return fromRegistry.map((row) => ({
			value: row.value,
			label: row.label || row.value,
			process_name: row.process_name || null,
			policy: row.policy || {},
		}));
	}

	const contract = getContract(normalizedType);
	return (contract.operation_options || []).map((value) => ({
		value,
		label: value,
		process_name: null,
		policy: (contract.operation_policies || {})[value] || {},
	}));
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
		require_return_type: contract.require_return_type || false,
	};

	if (operation) {
		effective = mergePolicy(effective, (contract.operation_policies || {})[operation] || {});
	}

	if (normalizedType === "Process" && operation) {
		effective = mergePolicy(effective, getProcessOperationPolicy(processName, operation));
	}

	return effective;
}

export function getAllowedReturnTypeOptions(actionType, ctx = {}) {
	const normalizedType = normalizeActionType(actionType);
	const policy = getEffectiveActionPolicy(actionType, ctx);
	const allowed = policy.allowed_return_types || [];
	if (allowed.length) return [...allowed];
	if (ACTION_TYPES_WITH_RETURN_SCHEMA.has(normalizedType)) return [...RETURN_TYPE_OPTIONS];
	return [];
}

export function getAllowedMutationModeOptions(actionType, ctx = {}) {
	const policy = getEffectiveActionPolicy(actionType, ctx);
	const allowed = policy.allowed_mutations || [];
	return allowed.length ? [...allowed] : [...MUTATION_MODE_OPTIONS];
}

export function getFieldLabel(actionType, fieldname, ctx = {}) {
	const policy = getEffectiveActionPolicy(actionType, ctx);
	return policy?.field_labels?.[fieldname] || null;
}

export function shouldShowReturnType(actionType, ctx = {}) {
	const policy = getEffectiveActionPolicy(actionType, ctx);
	const options = getAllowedReturnTypeOptions(actionType, ctx);
	if (!options.length) return false;
	return policy.show_return_type !== false;
}

export function isReturnTypeMandatory(actionType, ctx = {}) {
	const policy = getEffectiveActionPolicy(actionType, ctx);
	return Boolean(policy.require_return_type);
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

	const needsReturnVariable =
		!!nodeData.mutation_mode ||
		(nodeData.return_type && nodeData.return_type !== "Yes / No") ||
		!!nodeData.resolved_output_schema ||
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

/**
 * Validate node data against contract.
 * @param {Object} nodeData - The node's data object
 * @returns {{ valid: boolean, errors: string[] }}
 */
export function validateAgainstContract(nodeData) {
	if (!nodeData || !nodeData.action_type) {
		return { valid: true, errors: [] };
	}

	const contract = getContract(nodeData.action_type);
	const policy = getEffectiveActionPolicy(nodeData.action_type, {
		operation: nodeData.operation,
		processName: nodeData.process_name,
	});
	const errors = [];

	if (RELEASE_DISABLED_ACTION_TYPES.has(nodeData.action_type)) {
		errors.push(__("{0} is not available in this release", [nodeData.action_type]));
	}

	for (const field of contract.required_fields || []) {
		const value = nodeData[field];
		if (value === undefined || value === null || value === "") {
			errors.push(__("Field '{0}' is required for {1}", [field, nodeData.action_type]));
		}
	}

	if (nodeData.operation && contract.mandatory_fields?.[nodeData.operation]) {
		for (const field of contract.mandatory_fields[nodeData.operation]) {
			const value = nodeData[field];
			if (value === undefined || value === null || value === "") {
				errors.push(
					__("Field '{0}' is required for {1} in mode {2}", [
						field,
						nodeData.action_type,
						nodeData.operation,
					])
				);
			}
		}
	}

	if (contract.terminal) {
		if (nodeData.next_step_if_true || nodeData.next_step_if_false) {
			errors.push(
				__("{0} is terminal and should not have next steps", [nodeData.action_type])
			);
		}
	}

	// We no longer strictly require a false path for actions that support it (e.g., Loop, Condition).
	// An empty path simply implies the execution terminates for that branch.

	if (!contract.has_next_false && nodeData.next_step_if_false) {
		errors.push(__("{0} does not support 'next step if false'", [nodeData.action_type]));
	}

	if (nodeData.mutation_mode) {
		const allowed = policy.allowed_mutations || [];
		if (Array.isArray(allowed) && allowed.length && !allowed.includes(nodeData.mutation_mode)) {
			errors.push(
				__("Mutation mode '{0}' is not allowed for {1}", [
					nodeData.mutation_mode,
					nodeData.action_type,
				])
			);
		}
		if (!nodeData.return_variable) {
			errors.push(__("Mutation Mode requires a Return Variable Name"));
		}
	}

	if (nodeData.return_type) {
		const allowedReturnTypes = policy.allowed_return_types || [];
		if (
			Array.isArray(allowedReturnTypes) &&
			allowedReturnTypes.length &&
			!allowedReturnTypes.includes(nodeData.return_type)
		) {
			errors.push(
				__("Return type '{0}' is not allowed for {1}", [
					nodeData.return_type,
					nodeData.action_type,
				])
			);
		}
	}

	if (policy.require_return_type && !nodeData.return_type) {
		errors.push(__("Return type is required for this operation"));
	}

	const showReturnType = policy.show_return_type !== false;
	if (
		((showReturnType && nodeData.return_type && nodeData.return_type !== "Yes / No") ||
			nodeData.resolved_output_schema) &&
		!nodeData.return_variable
	) {
		errors.push(__("Return Schema requires a Return Variable Name"));
	}

	return {
		valid: errors.length === 0,
		errors,
	};
}

/**
 * Get all action type options for Select field.
 */
export function getActionTypeOptions() {
	return Object.keys(ACTION_TYPE_CONTRACT).filter(
		(actionType) => !RELEASE_DISABLED_ACTION_TYPES.has(actionType)
	);
}

/**
 * Check if action type supports dynamic fields (e.g., Process with operation schema).
 */
export function hasDynamicFields(actionType) {
	return getContract(actionType).dynamic_fields || false;
}

export default ACTION_TYPE_CONTRACT;
