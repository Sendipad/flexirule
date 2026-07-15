<template>
	<div class="output-panel fxr-accent-scope" :style="panelStyleVars">
		<div class="panel-header" v-if="!store.use_modern_layout">
			<h4>{{ __("Output & Mutation") }}</h4>
			<p class="text-muted small">{{ __("Manage results and data storage") }}</p>
		</div>

		<div class="panel-sections">
			<!-- Result Storage Configuration -->
			<div class="panel-section storage-section">
				<h5 class="section-title">{{ __("Result Storage") }}</h5>
				<div class="storage-controls mt-2">
					<div v-if="showMutationMode" class="storage-row">
						<ControlFactory
							ref="mutationModeRef"
							:df="mutationModeField"
							:modelValue="node.data?.mutation_mode"
							:read_only="readOnly"
							:showValidation="showValidation"
							@update:modelValue="updateField('mutation_mode', $event)"
						/>
					</div>

					<div v-if="showReturnVariable" class="storage-row">
						<ComboBoxControl
							v-if="useAutocompleteForReturnVariable"
							ref="returnVariableRef"
							:df="returnVariableField"
							:modelValue="node.data?.return_variable"
							:get_query="getReturnVariableOptions"
							:read_only="readOnly"
							:showValidation="showValidation"
							:autocompleteMode="autocompleteMode"
							:placeholder="returnVariablePlaceholder"
							@update:modelValue="updateField('return_variable', $event)"
						/>
						<ControlFactory
							v-else
							ref="returnVariableRef"
							:df="returnVariableField"
							:modelValue="node.data?.return_variable"
							:read_only="readOnly"
							:showValidation="showValidation"
							@update:modelValue="updateField('return_variable', $event)"
						/>
					</div>

					<div v-if="showReturnType" class="storage-row">
						<ControlFactory
							ref="returnTypeRef"
							:df="returnTypeField"
							:modelValue="node.data?.return_type"
							:read_only="readOnly"
							:showValidation="showValidation"
							@update:modelValue="updateField('return_type', $event)"
						/>
					</div>
				</div>
			</div>

			<div class="section-divider"></div>

			<!-- Output Mapping / Variable Assignments -->
			<div class="panel-section mapping-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Key Assignments") }}</h5>
					<button v-if="!readOnly" class="btn btn-xs btn-link" @click="addOutputMapping">
						<i class="fa fa-plus"></i> {{ __("Add") }}
					</button>
				</div>
				<p class="text-muted extra-small mb-2">
					{{ __("Map specific result keys to context variables.") }}
				</p>

				<div class="mapping-list">
					<div v-if="!outputMappings.length" class="empty-state">
						{{ __("No specific assignments.") }}
					</div>
					<div v-for="(m, idx) in outputMappings" :key="'out-' + idx" class="mapping-row">
						<div class="mapping-inputs">
							<input
								type="text"
								class="form-control input-xs"
								v-model="m.source"
								:placeholder="__('Result Key')"
								:disabled="readOnly"
								@change="saveOutputMappings"
							/>
							<i class="fa fa-arrow-right text-muted mx-1"></i>
							<ComboBoxControl
								:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
								:modelValue="m.target"
								:get_query="getVariableOptions"
								:placeholder="__('Var')"
								:read_only="readOnly"
								@update:modelValue="
									m.target = $event;
									saveOutputMappings();
								"
							/>
						</div>
						<button
							v-if="!readOnly"
							class="btn btn-xs btn-link text-danger"
							@click="removeOutputMapping(idx)"
						>
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			</div>

			<div class="section-divider"></div>

			<!-- Return Schema / Discovery -->
			<div class="panel-section schema-section">
				<h5 class="section-title">{{ __("Return Schema") }}</h5>
				<div class="detected-keys-list mt-2">
					<div v-if="!detectedKeys.length" class="empty-state">
						{{ __("No schema detected.") }}
					</div>
					<div v-else class="keys-grid">
						<div
							v-for="k in detectedKeys"
							:key="k.fieldname || k.key"
							class="key-tag"
							:title="`${k.fieldname || k.key} (${k.fieldtype || 'Data'})`"
						>
							<i class="fa fa-info-circle mr-1 opacity-70"></i>
							{{ k.label || k.fieldname || k.key }}
						</div>
					</div>
				</div>

				<div
					class="form-group mt-3"
					v-if="
						showResolvedSchema &&
						node.data?.return_type &&
						node.data?.return_type !== 'Yes / No'
					"
				>
					<label class="section-title mini">{{ __("Manual Schema (JSON)") }}</label>
					<ControlFactory
						:df="resolvedSchemaField"
						:modelValue="serializeSchema(node.data?.resolved_output_schema)"
						@update:modelValue="updateField('resolved_output_schema', $event)"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from "vue";
import { useStore } from "../../stores";
import ControlFactory from "../../controls/ControlFactory.vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import {
	applyOutputPolicyDefaults,
	getContract,
	getDerivedFieldState,
	getAllowedMutationModeOptions,
	getAllowedReturnTypeOptions,
	getEffectiveActionPolicy,
	getFieldLabel,
	isReturnTypeMandatory,
	shouldShowReturnType,
} from "../../../core/contracts.js";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
	showValidation: { type: Boolean, default: false },
});

const store = useStore();

const outputMappings = ref([]);
const availableVariables = ref([]);

const policyContext = computed(() => ({
	operation: props.node?.data?.operation,
	processName: props.node?.data?.process_name,
}));

const panelStyleVars = computed(() => {
	const actionType = props.node?.data?.action_type || props.node?.type;
	const accent = getContract(actionType)?.css?.color || "var(--fxr-accent)";
	return {
		"--fxr-node-accent": accent,
		"--fxr-node-accent-light": `color-mix(in srgb, ${accent} 12%, var(--fxr-surface))`,
	};
});

const showMutationMode = computed(() => {
	const actionType = props.node?.data?.action_type;
	const state = getDerivedFieldState(
		actionType,
		"mutation_mode",
		props.node?.data || {},
		store.rule_doc || {},
		policyContext.value
	);
	if (state.hidden) return false;
	return getAllowedMutationModeOptions(actionType, policyContext.value).length > 0;
});

const allowedReturnTypeOptions = computed(() =>
	getAllowedReturnTypeOptions(props.node?.data?.action_type, policyContext.value)
);

const showReturnType = computed(
	() =>
		shouldShowReturnType(props.node?.data?.action_type, policyContext.value) &&
		!getDerivedFieldState(
			props.node?.data?.action_type,
			"return_type",
			props.node?.data || {},
			store.rule_doc || {},
			policyContext.value
		).hidden
);

const showReturnVariable = computed(() => {
	const policy = getEffectiveActionPolicy(props.node?.data?.action_type, policyContext.value);
	const state = getDerivedFieldState(
		props.node?.data?.action_type,
		"return_variable",
		props.node?.data || {},
		store.rule_doc || {},
		policyContext.value
	);
	if (state.hidden) return false;
	if (policy.show_return_variable === false) return false;

	return (
		policy.show_return_variable ||
		policy.require_return_variable ||
		showMutationMode.value ||
		allowedReturnTypeOptions.value.length > 0
	);
});

const showResolvedSchema = computed(() => allowedReturnTypeOptions.value.length > 0);

// -- Field Definitions --
const returnTypeField = computed(() => ({
	fieldname: "return_type",
	fieldtype: "Select",
	label:
		getFieldLabel(props.node?.data?.action_type, "return_type", policyContext.value) ||
		__("Result Type"),
	options: ["", ...allowedReturnTypeOptions.value].join("\n"),
	reqd: isReturnTypeMandatory(props.node?.data?.action_type, policyContext.value) ? 1 : 0,
}));

const returnVariableField = computed(() => ({
	fieldname: "return_variable",
	fieldtype: useAutocompleteForReturnVariable.value ? "Autocomplete" : "Data",
	label:
		getFieldLabel(props.node?.data?.action_type, "return_variable", policyContext.value) ||
		__("Result Variable Name"),
	description:
		props.node.data?.return_type === "Yes / No"
			? __("Value assigned directly.")
			: __("Stored as this variable."),
	reqd:
		getDerivedFieldState(
			props.node?.data?.action_type,
			"return_variable",
			props.node?.data || {},
			store.rule_doc || {},
			policyContext.value
		).reqd || isReturnVariableMandatory.value
			? 1
			: 0,
}));

const useAutocompleteForReturnVariable = computed(() => {
	const mode = (props.node?.data?.mutation_mode || "").toString();
	return mode.includes("Context Variable");
});

const autocompleteMode = computed(() => {
	const mode = props.node?.data?.mutation_mode;
	if (mode === "Update Context Variable") return "strict";
	if (mode === "Set Context Variable") return "creatable";
	if (mode === "Append to Context Variable") return "prefix";
	return null;
});

const returnVariablePlaceholder = computed(() => {
	const mode = props.node?.data?.mutation_mode;
	if (mode === "Update Context Variable") return __("Select an existing variable...");
	if (mode === "Set Context Variable") return __("Select or enter a variable name...");
	if (mode === "Append to Context Variable") return __("Select a variable then continue typing...");
	return __("Result Variable Name");
});

const isReturnVariableMandatory = computed(() => {
	const data = props.node.data || {};
	const policy = getEffectiveActionPolicy(data.action_type, policyContext.value);
	return !!(
		data.mutation_mode ||
		(data.return_type && data.return_type !== "Yes / No") ||
		data.resolved_output_schema ||
		policy.require_return_variable
	);
});

const mutationModeField = computed(() => ({
	fieldname: "mutation_mode",
	fieldtype: "Select",
	label:
		getFieldLabel(props.node?.data?.action_type, "mutation_mode", policyContext.value) ||
		__("Result Handling"),
	options: getAllowedMutationModeOptions(props.node?.data?.action_type, policyContext.value).join(
		"\n"
	),
	reqd: getDerivedFieldState(
		props.node?.data?.action_type,
		"mutation_mode",
		props.node?.data || {},
		store.rule_doc || {},
		policyContext.value
	).reqd
		? 1
		: 0,
}));

const resolvedSchemaField = {
	fieldname: "resolved_output_schema",
	fieldtype: "Code",
	label: "",
	options: "JSON",
	read_only: props.readOnly,
};

const detectedKeys = computed(() => {
	const schema = props.node?.data?.resolved_output_schema;
	if (Array.isArray(schema)) return schema;
	try {
		return typeof schema === "string" ? JSON.parse(schema) : [];
	} catch (e) {
		return [];
	}
});

function serializeSchema(val) {
	if (!val) return "[]";
	if (typeof val === "string") return val;
	try {
		return JSON.stringify(val, null, 2);
	} catch (e) {
		return "[]";
	}
}

// -- Mapping Logic --
watch(
	() => props.node.data?.config,
	(val) => {
		const config = parseConfig(val);
		const mappingValue = config.output_mapping;
		if (mappingValue) {
			try {
				const obj =
					typeof mappingValue === "string" ? JSON.parse(mappingValue) : mappingValue;
				outputMappings.value = Object.entries(obj).map(([source, target]) => ({
					source,
					target,
				}));
			} catch (e) {
				outputMappings.value = [];
			}
		} else {
			outputMappings.value = [];
		}
	},
	{ immediate: true }
);

watch(
	() => [
		props.node?.data?.action_type,
		props.node?.data?.operation,
		props.node?.data?.process_name,
	],
	() => {
		if (!props.node?.data) return;
		let changed = applyOutputPolicyDefaults(props.node.data, {
			parent: store.rule_doc || {},
			preserveUserChoices: true,
		});
		if (changed) {
			store.mark_dirty();
		}
	},
	{ immediate: true }
);

function addOutputMapping() {
	outputMappings.value.push({ source: "", target: "" });
}

function removeOutputMapping(idx) {
	outputMappings.value.splice(idx, 1);
	saveOutputMappings();
}

function saveOutputMappings() {
	const obj = {};
	outputMappings.value.forEach((m) => {
		if (m.source && m.target) obj[m.source] = m.target;
	});
	updateConfigKey("output_mapping", Object.keys(obj).length ? obj : null);
}

function updateField(fieldname, value) {
	if (props.node.data) {
		if (props.node.data[fieldname] === value) return;
		props.node.data[fieldname] = value;

		const isDraft = !store.nodes.some((n) => n === props.node);
		if (!isDraft) {
			store.mark_dirty();
		}
	}
}

function parseConfig(configValue) {
	if (!configValue) return {};
	if (typeof configValue === "object") return configValue;
	try {
		return JSON.parse(configValue);
	} catch (e) {
		return {};
	}
}

function updateConfigKey(key, value) {
	if (!props.node?.data) return;
	const nextConfig = {
		...parseConfig(props.node.data.config),
	};

	if (
		value === null ||
		value === undefined ||
		value === "" ||
		(typeof value === "object" && !Array.isArray(value) && !Object.keys(value).length)
	) {
		delete nextConfig[key];
	} else {
		nextConfig[key] = value;
	}

	props.node.data.config = nextConfig;

	const isDraft = !store.nodes.some((n) => n === props.node);
	if (!isDraft) {
		store.mark_dirty();
	}
}

async function refreshVariables() {
	if (!props.node?.id) return;
	try {
		availableVariables.value = await store.getAvailableVariables(props.node.id);
	} catch (e) {
		availableVariables.value = [];
	}
}

function getVariableOptions() {
	return availableVariables.value.map((v) => ({ label: v.label, value: v.value }));
}

function getReturnVariableOptions() {
	const seen = new Set();
	const out = [];
	for (const v of availableVariables.value || []) {
		const raw = String(v?.value || "").trim();
		if (!raw.startsWith("vars.")) continue;
		const name = raw
			.replace(/^vars\./, "")
			.split(".")[0]
			.trim();
		if (!name || seen.has(name)) continue;
		seen.add(name);
		out.push({
			label: __("{0} ({1})", [name, __("existing")]),
			value: name,
		});
	}
	return out;
}

onMounted(() => {
	refreshVariables();
});

watch(
	() => [props.node.data?.mutation_mode, props.node.data?.return_type],
	([mut, ret]) => {
		if (
			(mut || (ret && ret !== "Yes / No")) &&
			!props.node.data?.return_variable &&
			!props.readOnly
		) {
			applyOutputPolicyDefaults(props.node.data, {
				parent: store.rule_doc || {},
				preserveUserChoices: false,
			});
			store.mark_dirty();
		}
	}
);

const mutationModeRef = ref(null);
const returnVariableRef = ref(null);
const returnTypeRef = ref(null);

async function validate() {
	const errors = [];

	const controlRefs = [
		mutationModeRef.value,
		returnVariableRef.value,
		returnTypeRef.value,
	].filter(Boolean);

	const results = await Promise.all(controlRefs.map((c) => c.validate()));
	results.forEach((res) => {
		if (!res.valid) errors.push(...res.errors);
	});

	if (isReturnVariableMandatory.value && !props.node.data?.return_variable) {
		errors.push(__("Result Variable Name is required when handling results"));
	}

	outputMappings.value.forEach((m, idx) => {
		if ((m.source && !m.target) || (!m.source && m.target)) {
			errors.push(__("Variable Assignment #{0} is incomplete", [idx + 1]));
		}
	});
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<style scoped>
.output-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background-color: var(--fxr-surface);
}

.panel-header {
	padding: 20px;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 15px;
	font-weight: 600;
}

.output-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
}

.panel-sections {
	flex: 1;
	overflow-y: auto;
	padding: var(--spacing-md);
	display: flex;
	flex-direction: column;
	gap: var(--spacing-md);
}

.panel-section {
	display: flex;
	flex-direction: column;
	padding: var(--spacing-md);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	background-color: var(--fxr-surface-soft);
}

.storage-controls {
	display: flex;
	flex-direction: column;
	gap: var(--spacing-sm);
}

.storage-row {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 8px;
}

.section-title {
	margin: 0;
	font-size: 10px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	color: var(--fxr-text-soft);
}

.section-divider {
	height: 1px;
	background-color: var(--fxr-border-subtle);
	margin: 0;
}

.mapping-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.mapping-row {
	display: flex;
	align-items: center;
	gap: 8px;
}

.mapping-inputs {
	flex: 1;
	display: flex;
	align-items: center;
	padding: 4px 8px;
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 12px;
	background-color: var(--fxr-bg-input);
	transition: border-color 0.2s;
}

.mapping-inputs:focus-within {
	border-color: var(--fxr-node-accent, var(--fxr-accent));
	background-color: var(--fxr-bg-input);
	box-shadow: 0 0 0 2px var(--fxr-node-accent-light, var(--fxr-accent-soft));
}

.mapping-inputs :deep(.autocomplete-control),
.mapping-inputs input {
	border: none;
	background: transparent;
	font-size: 12px;
	padding: 0;
	height: 24px;
}

.mapping-inputs :deep(.autocomplete-control) {
	flex: 1;
}

.empty-state {
	padding: 16px;
	text-align: center;
	color: var(--fxr-text-faint);
	font-size: 11px;
	background-color: var(--fxr-surface-soft);
	border: 1px dashed var(--fxr-border-subtle);
	border-radius: 8px;
}

.extra-small {
	font-size: 10px;
}

.input-xs {
	height: 24px !important;
	padding: 0 4px !important;
	font-size: 11px !important;
}

.keys-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}

.key-tag {
	font-size: 10px;
	font-weight: 600;
	padding: 2px 8px;
	background-color: var(--fxr-bg-muted);
	color: var(--fxr-text-soft);
	border-radius: 4px;
	border: 1px solid var(--fxr-border-subtle);
}

:deep(.form-control:focus),
:deep(.awesomplete input:focus),
:deep(.multiselect__input:focus) {
	border-color: var(--fxr-node-accent, var(--fxr-border-focus)) !important;
	box-shadow: 0 0 0 2px var(--fxr-node-accent-light, var(--fxr-accent-light)) !important;
}

@media (max-width: 768px) {
	.panel-sections {
		padding: var(--fxr-space-4);
		gap: var(--fxr-space-5);
	}

	.mapping-row {
		align-items: stretch;
		flex-direction: column;
	}

	.mapping-inputs {
		width: 100%;
	}
}

:deep(.control-factory) {
	margin-bottom: 0;
}
</style>
