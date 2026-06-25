/**
 * FlexiRule action contracts
 *
 * CANONICAL SOURCE: flexirule/ruleflow/core/contracts.py
 *
 * This module provides a frontend implementation of the action contracts.
 * It is primarily used for:
 * 1. UI rendering (icons, colors, labels)
 * 2. Real-time canvas status (getNodeStatus)
 * 3. Reactive frontend validation (validateAgainstContract)
 *
 * Fallbacks defined here MUST match the backend definitions in contracts.py.
 * The system attempts to load fresh contracts via 'loadContractsFromBackend'
 * but uses these as static defaults.
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
	Assignment:
		"Declare one or more batch state mutations applied sequentially. Supports doc.* and vars.* targets with type-aware operators (set, clear, increment, decrement, toggle, append, merge).",
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
		node_type: "start",
		category: "Control Flow",
		configurable: false,
	},
	Condition: {
		required_fields: ["config"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-code-fork", color: "#3b82f6" },
		validation: { frontend: "validate_condition" },
		node_type: "condition",
		category: "Control Flow",
		configurable: true,
		config_component: "ConditionStep",
	},
	Process: {
		required_fields: ["process_name", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		dynamic_fields: true,
		css: { icon: "fa fa-cog", color: "#8b5cf6" },
		node_type: "process",
		category: "Processes",
		configurable: true,
		config_component: "ProcessConfig",
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
		node_type: "loop",
		category: "Control Flow",
		configurable: true,
		config_component: "LoopConfig",
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
		node_type: "stop",
		category: "Control Flow",
		configurable: false,
	},
	Switch: {
		required_fields: ["config"],
		has_next_true: false,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-random", color: "#06b6d4" },
		node_type: "switch",
		category: "Control Flow",
		configurable: true,
		config_component: "SwitchConfig",
	},
	Wait: {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-clock-o", color: "#64748b" },
		node_type: "wait",
		category: "Control Flow",
		configurable: true,
		config_component: "WaitConfig",
	},
	"Sub-Rule": {
		required_fields: ["rule"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-cube", color: "#ec4899" },
		node_type: "sub-rule",
		category: "Control Flow",
		configurable: true,
		config_component: "SubRuleConfig",
	},
	Assignment: {
		required_fields: ["config"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-list-ol", color: "#14b8a6" },
		field_labels: { config: "Assignments" },
		show_return_variable: false,
		show_return_type: false,
		node_type: "assignment",
		category: "Data Actions",
		configurable: true,
		config_component: "AssignmentConfig",
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
		node_type: "notify",
		category: "Notifications",
		configurable: true,
		config_component: "NotifyConfig",
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
		node_type: "raise-error",
		category: "Control Flow",
		configurable: true,
		config_component: "RaiseErrorConfig",
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
		node_type: "query",
		category: "Data Actions",
		configurable: true,
		config_component: "QueryRecordsConfig",
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
		node_type: "documentaction",
		category: "Data Actions",
		configurable: true,
		config_component: "DocumentActionConfig",
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
	"Assignment",
];
const DEFAULT_ACTION_TYPES_WITH_RETURN_SCHEMA = ["Process", "Query Records", "Document Action"];
const DEFAULT_CONFIG_MODAL_TYPES = [
	"Process",
	"Condition",
	"Assignment",
	"Stop",
	"Raise Error",
	"Notify",
	"Wait",
	"Sub-Rule",
	"Document Action",
	"Loop",
];

// Operator metadata for the Assignment action type.
// Mirrors operators.py AssignmentOperatorRegistry metadata.
// Used by AssignmentConfig.vue for target-aware operator filtering.
export const ASSIGNMENT_OPERATOR_METADATA = {
	set: {
		label: "Set Value",
		requires_value: true,
		supported_target_types: [], // All types
		is_idempotent: true,
	},
	clear: {
		label: "Clear",
		requires_value: false,
		supported_target_types: [], // All types
		is_idempotent: true,
	},
	increment: {
		label: "Increment By",
		requires_value: true,
		supported_target_types: ["Int", "Float", "Currency", "Percent"],
		is_idempotent: false,
	},
	decrement: {
		label: "Decrement By",
		requires_value: true,
		supported_target_types: ["Int", "Float", "Currency", "Percent"],
		is_idempotent: false,
	},
	append: {
		label: "Append To List",
		requires_value: true,
		supported_target_types: ["Table", "Table MultiSelect"],
		is_idempotent: false,
	},
	merge: {
		label: "Merge Object",
		requires_value: true,
		supported_target_types: ["JSON", "Code", "Text"],
		is_idempotent: false,
	},
	toggle: {
		label: "Toggle Boolean",
		requires_value: false,
		supported_target_types: ["Check"],
		is_idempotent: false,
	},
};
const DEFAULT_FEATURE_FLAGS = {
	supports_logic_builder: false,
	supports_reference_context: false,
	supports_return_schema: false,
};

export let ACTION_TYPE_CONTRACT = withDescriptions(DEFAULT_ACTION_TYPE_CONTRACT);
export let ACTION_TYPE_MAP = {};
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
export let PROCESS_OPERATION_REGISTRY_V2 = {};
export let RUNTIME_FIELD_ALIASES = {};

let _contractsLoaded = false;
const CONTRACT_CACHE_KEY = "flexirule:contract_dto:v3";

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
}

function getCachedContractDto() {
	try {
		const raw = window.sessionStorage?.getItem(CONTRACT_CACHE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (!parsed || typeof parsed !== "object") return null;
		if (typeof parsed.contract_version_hash !== "string" || !parsed.contract_version_hash) {
			return null;
		}
		return parsed;
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

export async function loadProcessScript(processName) {
	if (!processName) return;
	if (window.flexirule?.processes?.[processName]) return;

	try {
		const r = await frappe.call({
			method: "flexirule.ruleflow.doctype.process.process.get_process_script",
			args: { process_name: processName },
		});
		if (r.message && r.message.script) {
			frappe.dom.eval(r.message.script);
		}
	} catch (e) {
		console.warn(`Failed to load script for process ${processName}`, e);
	}
}

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

export function getActionPresentation(actionType) {
	const contract = getContract(actionType);
	const css = contract?.css || {};
	return {
		icon: css.icon || contract.icon || "fa fa-circle",
		color: css.color || contract.color || "#6b7280",
		background: css.bg || `color-mix(in srgb, ${css.color || "#6b7280"} 14%, white)`,
		label: normalizeActionType(actionType) || __("Action"),
		description: contract?.description || "",
	};
}

export function getActionFeatureFlags(actionType) {
	const normalized = normalizeActionType(actionType);
	const contract = getContract(normalized);
	return {
		...DEFAULT_FEATURE_FLAGS,
		supports_logic_builder: CONFIG_MODAL_TYPES.has(normalized),
		supports_reference_context: ACTION_TYPES_WITH_REFERENCE_CONTEXT.has(normalized),
		supports_return_schema: ACTION_TYPES_WITH_RETURN_SCHEMA.has(normalized),
		...(contract?.feature_flags || {}),
	};
}

export function normalizeActionType(actionType) {
	if (!actionType) return "";

	const raw = String(actionType).trim();

	// 1. Direct match with canonical keys
	if (ACTION_TYPE_CONTRACT[raw]) return raw;

	// 2. Try to map hyphenated/machine types back to canonical
	// Normalized for easy lookup: e.g. "set-value" -> "set value"
	const normalized = raw.toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();

	// Case-insensitive direct match: "assignment" -> "Assignment"
	const canonicalKeys = Object.keys(ACTION_TYPE_CONTRACT);
	const match = canonicalKeys.find((k) => k.toLowerCase() === normalized);
	if (match) return match;

	// 3. Compact match for common UI variants:
	//    "subrule" / "sub-rule" -> "Sub-Rule", "raiseerror" -> "Raise Error"
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

export function getProcessOperationConfigFields(processName, operation) {
	const op = getProcessOperationDefinition(processName, operation);
	if (!op) return [];
	const v2 = PROCESS_OPERATION_REGISTRY_V2?.[processName]?.[operation] || op?.contract_v2;
	if (v2 && Array.isArray(v2.config_schema?.ui_schema)) {
		return v2.config_schema.ui_schema;
	}
	const parsed = parseJsonSafe(op.config_schema, op.config_schema);
	if (Array.isArray(parsed)) return parsed;
	if (parsed && Array.isArray(parsed.fields)) return parsed.fields;
	return [];
}

export function getProcessOperationPolicy(processName, operation) {
	if (!processName || !operation) return {};
	const v2Policy = PROCESS_OPERATION_REGISTRY_V2?.[processName]?.[operation]?.policy || {};
	const op = getProcessOperationDefinition(processName, operation);
	const contractPolicy = op?.contract_v2?.policy || {};
	return mergePolicy(v2Policy, contractPolicy);
}

function evaluateFieldExpression(expression, doc = {}, parent = {}) {
	if (!expression) return true;
	if (typeof expression === "boolean") return expression;
	if (typeof expression !== "string") return Boolean(expression);
	if (!expression.startsWith("eval:")) return Boolean(doc?.[expression]);
	try {
		return frappe.utils.eval(expression.slice(5), { doc, parent });
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

	const actionType = normalizeActionType(nodeData.action_type);
	const contract = getContract(actionType);
	const policy = getEffectiveActionPolicy(actionType, {
		operation: nodeData.operation,
		processName: nodeData.process_name,
	});
	const errors = [];

	if (RELEASE_DISABLED_ACTION_TYPES.has(actionType)) {
		errors.push(__("{0} is not available in this release", [actionType]));
	}

	// 1. Base Required Fields
	for (const field of contract.required_fields || []) {
		const value = nodeData[field];
		if (value === undefined || value === null || value === "") {
			errors.push(__("Field '{0}' is required for {1}", [field, actionType]));
		}
	}

	// 2. Operation-specific Mandatory Fields
	if (nodeData.operation && contract.mandatory_fields?.[nodeData.operation]) {
		for (const field of contract.mandatory_fields[nodeData.operation]) {
			const value = nodeData[field];
			if (value === undefined || value === null || value === "") {
				errors.push(
					__("Field '{0}' is required for {1} in mode {2}", [
						field,
						actionType,
						nodeData.operation,
					])
				);
			}
		}
	}

	// 3. Flow Integrity
	if (contract.terminal) {
		if (nodeData.next_step_if_true || nodeData.next_step_if_false) {
			errors.push(__("{0} is terminal and should not have next steps", [actionType]));
		}
	}

	if (!contract.has_next_false && nodeData.next_step_if_false) {
		errors.push(__("{0} does not support 'next step if false'", [actionType]));
	}

	// 4. Output/Mutation Policies
	if (nodeData.mutation_mode) {
		const allowed = policy.allowed_mutations || [];
		if (Array.isArray(allowed) && allowed.length && !allowed.includes(nodeData.mutation_mode)) {
			errors.push(
				__("Mutation mode '{0}' is not allowed for {1}", [
					nodeData.mutation_mode,
					actionType,
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
				__("Return type '{0}' is not allowed for {1}", [nodeData.return_type, actionType])
			);
		}
	}

	if (policy.require_return_type && !nodeData.return_type) {
		errors.push(__("Return type is required for this operation"));
	}

	if (policy.require_return_variable && !nodeData.return_variable) {
		errors.push(__("Return Variable Name is required for this operation"));
	}

	const showReturnType = policy.show_return_type !== false;
	if (
		((showReturnType && nodeData.return_type && nodeData.return_type !== "Yes / No") ||
			nodeData.resolved_output_schema) &&
		!nodeData.return_variable
	) {
		errors.push(__("Return Schema requires a Return Variable Name"));
	}

	// 5. Action-specific deep validation (Policy & Contract based)
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
				errors.push(__("{0} is required for {1}", [label, actionType]));
			}
		}
	}

	// 6. Action-specific deep validation (Condition & Loop legacy)
	if (actionType === "Condition" || actionType === "Loop") {
		const config = parseJsonSafe(nodeData.config, {});
		if (actionType === "Condition") {
			const { getConditionPayload } = window.flexirule?.utils?.condition_payload || {};
			const payload = getConditionPayload ? getConditionPayload(nodeData) : config.conditions;

			if (!payload || (Array.isArray(payload) && payload.length === 0)) {
				errors.push(__("At least one condition is required"));
			}
		}
		if (actionType === "Loop" && !config.iterator) {
			errors.push(__("Iterator is required for Loop"));
		}
	}

	return {
		valid: errors.length === 0,
		errors,
	};
}

/**
 * Get the status of a node based on its configuration and validation.
 * @param {Object} nodeData - The node's data object
 * @returns {'not-configured' | 'configured' | 'invalid'}
 */
export function getNodeStatus(nodeData) {
	if (!nodeData || !nodeData.action_type) {
		return "not-configured";
	}

	const actionType = normalizeActionType(nodeData.action_type);
	if (actionType === "Entry Action") return "configured";

	const contract = getContract(actionType);

	// Check if basic required fields are set
	const requiredFields = contract.required_fields || [];
	const hasRequiredFields = requiredFields.every((f) => {
		const val = nodeData[f];
		return val !== undefined && val !== null && val !== "";
	});

	if (!hasRequiredFields) {
		return "not-configured";
	}

	// For actions with a config object, check if it's empty
	if (requiredFields.includes("config")) {
		const config = parseJsonSafe(nodeData.config);
		const isEmpty =
			!config ||
			(Array.isArray(config) && config.length === 0) ||
			(typeof config === "object" && Object.keys(config).length === 0);

		if (isEmpty) {
			return "not-configured";
		}
	}

	// If configured, check if it's valid
	const validation = validateAgainstContract(nodeData);
	return validation.valid ? "configured" : "invalid";
}

/**
 * Get all action type options from registry (memory).
 */
export function getActionTypeOptions() {
	if (
		ACTION_TYPE_MAP &&
		typeof ACTION_TYPE_MAP === "object" &&
		Object.keys(ACTION_TYPE_MAP).length
	) {
		return Object.keys(ACTION_TYPE_MAP).sort();
	}

	const bootMap = window.frappe?.boot?.action_type_map;
	if (bootMap && typeof bootMap === "object") {
		return Object.keys(bootMap).sort();
	}

	// Fallback to contract keys if registry not available
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
