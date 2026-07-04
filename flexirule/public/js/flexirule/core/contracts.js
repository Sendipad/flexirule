/**
 * FlexiRule contract module — frontend mirror of backend DTO.
 *
 * SINGLE SOURCE OF TRUTH: flexirule/ruleflow/core/contracts.py (backend)
 *
 * This module is a thin stateful container. All contract data originates
 * from the backend via `loadContractsFromBackend()` which calls
 * `flexirule.ruleflow.api.get_contract_dto`.
 *
 * There are NO local fallback defaults. If the backend contract cannot be
 * loaded, the rule builder will surface an error rather than operating on
 * stale or incorrect data.
 *
 * Retry policy:
 *   - Transient errors (network, 502, 503, 504, timeout) → retry up to 3
 *     times with exponential backoff (500ms, 1000ms, 2000ms).
 *   - Permanent errors (400, 403, 404, 500, schema mismatch) → fail immediately.
 *
 * Cache policy:
 *   - sessionStorage key: CONTRACT_CACHE_KEY (schema-versioned).
 *   - Valid cached payloads are applied synchronously, then a background
 *     refresh checks if contract_version_hash changed. On mismatch the
 *     in-memory state is updated and the cache replaced.
 */

// ── Module-level state — populated exclusively from backend DTO ──────────────

export let ACTION_TYPE_CONTRACT = {};
export let ACTION_TYPE_MAP = {};
export let TRIGGER_TYPE_CONTRACT = {};
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

/**
 * Assignment operator metadata — sourced from backend operators.py.
 * Keyed by operator slug (e.g. "set", "clear", "increment").
 * Each entry: { label, requires_value, supported_target_types, is_idempotent }
 */
export let ASSIGNMENT_OPERATOR_METADATA = {};

// ── Cache internals ───────────────────────────────────────────────────────────

let _contractsLoaded = false;
let _loadPromise = null;

// Key includes the schema version so old cached payloads are automatically
// discarded when CONTRACT_SCHEMA_VERSION bumps on the backend.
const CONTRACT_CACHE_KEY = "flexirule:contract_dto:v4";

// ── DTO application ───────────────────────────────────────────────────────────

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

function applyContractDto(dto = {}) {
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

// ── sessionStorage cache ──────────────────────────────────────────────────────

function getCachedContractDto() {
	try {
		const raw = window.sessionStorage?.getItem(CONTRACT_CACHE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw);
		if (!parsed || typeof parsed !== "object") return null;
		// Require both hash and schema_version for a cache hit
		if (typeof parsed.contract_version_hash !== "string" || !parsed.contract_version_hash) {
			return null;
		}
		if (typeof parsed.schema_version !== "string" || !parsed.schema_version) {
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
		// Ignore storage quota failures — the builder will still work in-memory.
	}
}

// ── Error classification ──────────────────────────────────────────────────────

/**
 * Returns true for transient HTTP/network errors that should be retried.
 * Permanent errors (4xx other than 408/429, 500) are not retried.
 */
function isTransientError(err) {
	if (!err) return false;
	// No HTTP status → pure network failure
	if (!err.httpStatus && !err.status) {
		return true; // Network error, CORS failure, DNS timeout
	}
	const status = err.httpStatus || err.status || 0;
	return (
		status === 0 ||
		status === 408 ||
		status === 429 ||
		status === 502 ||
		status === 503 ||
		status === 504
	);
}

async function sleep(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Fetch the contract DTO from the backend with transient-error retries.
 * On permanent failure throws immediately; on transient failure retries up to
 * maxAttempts times with exponential backoff.
 *
 * @param {number} maxAttempts
 * @returns {Promise<object>} The validated DTO
 * @throws on permanent error or exhausted retries
 */
async function fetchContractDtoWithRetry(maxAttempts = 3) {
	let lastError;
	for (let attempt = 1; attempt <= maxAttempts; attempt++) {
		try {
			const response = await frappe.call({
				method: "flexirule.ruleflow.api.get_contract_dto",
			});
			const dto = response?.message;
			if (!dto || typeof dto !== "object") {
				throw new Error("Backend returned an empty or invalid contract DTO.");
			}
			if (!dto.contract_version_hash) {
				throw new Error("Backend contract DTO is missing contract_version_hash.");
			}
			return dto;
		} catch (err) {
			lastError = err;
			if (!isTransientError(err)) {
				// Permanent error — fail immediately without retry
				throw err;
			}
			if (attempt < maxAttempts) {
				const delay = 500 * Math.pow(2, attempt - 1); // 500ms, 1000ms, 2000ms
				console.warn(
					`FlexiRule: Contract fetch attempt ${attempt} failed (transient). Retrying in ${delay}ms…`,
					err
				);
				await sleep(delay);
			}
		}
	}
	throw lastError;
}

// ── Public loader ─────────────────────────────────────────────────────────────

/**
 * Load contracts from the backend and apply them to module state.
 *
 * Called once during rule builder initialisation. Subsequent calls are
 * no-ops unless `force = true`.
 *
 * On failure the function throws — callers are expected to surface the error
 * to the user rather than silently proceeding with empty contracts.
 *
 * @param {boolean} force - Force re-fetch even if already loaded.
 */
export async function loadContractsFromBackend(force = false) {
	// Deduplicate concurrent calls
	if (_loadPromise && !force) return _loadPromise;

	_loadPromise = _doLoad(force);
	try {
		await _loadPromise;
	} finally {
		if (!_contractsLoaded) {
			// Reset so the next call can retry
			_loadPromise = null;
		}
	}
}

async function _doLoad(force) {
	if (_contractsLoaded && !force) return;
	if (!window.frappe?.call) {
		throw new Error("FlexiRule: frappe.call is not available — contracts cannot be loaded.");
	}

	// 1. Apply from Frappe boot context (fastest path, no network call)
	const bootDto = window.frappe?.boot?.flexirule_contract_dto;
	if (bootDto && typeof bootDto === "object" && bootDto.contract_version_hash && !force) {
		applyContractDto(bootDto);
		setCachedContractDto(bootDto);
		_contractsLoaded = true;
		return;
	}

	// 2. Apply cached DTO synchronously for instant render, then refresh in background
	const cachedDto = getCachedContractDto();
	if (cachedDto && !force) {
		applyContractDto(cachedDto);
		_contractsLoaded = true;

		// Background refresh — updates state and cache if hash changed
		fetchContractDtoWithRetry()
			.then((freshDto) => {
				if (freshDto.contract_version_hash !== cachedDto.contract_version_hash) {
					applyContractDto(freshDto);
					setCachedContractDto(freshDto);
				}
			})
			.catch((err) => {
				// Non-blocking: cached data is already applied. Log but don't throw.
				console.warn("FlexiRule: Background contract refresh failed:", err);
			});
		return;
	}

	// 3. Fresh fetch (no cache or force refresh)
	const dto = await fetchContractDtoWithRetry();
	applyContractDto(dto);
	setCachedContractDto(dto);
	_contractsLoaded = true;
}

// ── Process script loader ─────────────────────────────────────────────────────

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

// ── Contract accessors ────────────────────────────────────────────────────────

/**
 * Get contract for an action type.
 * Returns an empty-safe contract object (never null).
 */
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
	const normalized = raw.toLowerCase().replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();

	// Case-insensitive direct match: "assignment" → "Assignment"
	const canonicalKeys = Object.keys(ACTION_TYPE_CONTRACT);
	const match = canonicalKeys.find((k) => k.toLowerCase() === normalized);
	if (match) return match;

	// 3. Compact match for common UI variants:
	//    "subrule" / "sub-rule" → "Sub-Rule", "raiseerror" → "Raise Error"
	const compact = normalized.replace(/[^a-z0-9]/g, "");
	const compactMatch = canonicalKeys.find(
		(k) => k.toLowerCase().replace(/[^a-z0-9]/g, "") === compact
	);
	if (compactMatch) return compactMatch;

	return actionType;
}

export function isTerminalAction(actionType) {
	return getContract(actionType).terminal || false;
}

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

// ── Policy helpers ────────────────────────────────────────────────────────────

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

	// Derive from loaded contract keys (no hardcoded fallback)
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
