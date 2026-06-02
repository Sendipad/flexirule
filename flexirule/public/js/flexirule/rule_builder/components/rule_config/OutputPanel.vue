<template>
	<div class="output-panel fxr-accent-scope" :style="panelStyleVars">
		<div class="panel-header" v-if="!store.use_modern_layout">
			<h4>{{ __("Output & Mutation") }}</h4>
			<p class="text-muted small">{{ __("Manage results and data storage") }}</p>
		</div>

		<div class="panel-sections v2-scrollbar">
			<!-- Result Storage Configuration -->
			<div class="panel-section storage-section">
				<h5 class="section-title">{{ __("Result Storage") }}</h5>
				<div class="storage-controls mt-3">
					<ControlFactory
						v-if="showReturnType"
						:df="returnTypeField"
						:modelValue="node.data?.return_type"
						:read_only="readOnly"
						@update:modelValue="updateField('return_type', $event)"
					/>

					<ComboBoxControl
						v-if="showReturnVariable && useAutocompleteForReturnVariable"
						:df="returnVariableField"
						:modelValue="node.data?.return_variable"
						:get_query="getReturnVariableOptions"
						:read_only="readOnly"
						@update:modelValue="updateField('return_variable', $event)"
					/>
					<ControlFactory
						v-else-if="showReturnVariable"
						:df="returnVariableField"
						:modelValue="node.data?.return_variable"
						:read_only="readOnly"
						@update:modelValue="updateField('return_variable', $event)"
					/>

					<ControlFactory
						v-if="showMutationMode"
						:df="mutationModeField"
						:modelValue="node.data?.mutation_mode"
						:read_only="readOnly"
						@update:modelValue="updateField('mutation_mode', $event)"
					/>
				</div>
			</div>

			<div class="section-divider"></div>

			<!-- Output Mapping / Variable Assignments -->
			<div class="panel-section mapping-section">
				<div class="section-header">
					<h5 class="section-title">{{ __("Key Assignments") }}</h5>
					<button v-if="!readOnly" class="btn-add" @click="addOutputMapping">
						<i class="fa fa-plus"></i> {{ __("Add") }}
					</button>
				</div>
				<p class="text-muted extra-small mb-3">
					{{ __("Map specific result keys to context variables.") }}
				</p>

				<div class="mapping-list">
					<div v-if="!outputMappings.length" class="empty-state compact">
						<p>{{ __("No specific assignments.") }}</p>
					</div>
					<div
						v-for="(m, idx) in outputMappings"
						:key="'out-' + idx"
						class="mapping-card"
					>
						<div class="mapping-inputs">
							<div class="input-wrapper">
								<span class="input-label">{{ __("Key") }}</span>
								<input
									type="text"
									class="mapping-input-field"
									v-model="m.source"
									:placeholder="__('source_key')"
									:disabled="read_only"
									@change="saveOutputMappings"
								/>
							</div>
							<div class="mapping-arrow">
								<i class="fa fa-arrow-right"></i>
							</div>
							<div class="input-wrapper">
								<span class="input-label">{{ __("Target") }}</span>
								<ComboBoxControl
									:df="{
										fieldtype: 'Autocomplete',
										label: '',
										read_only: readOnly,
									}"
									:modelValue="m.target"
									:get_query="getVariableOptions"
									:placeholder="__('variable')"
									:read_only="readOnly"
									hideLabel
									@update:modelValue="
										m.target = $event;
										saveOutputMappings();
									"
								/>
							</div>
						</div>
						<button
							v-if="!readOnly"
							class="btn-remove"
							@click="removeOutputMapping(idx)"
							:title="__('Remove Mapping')"
						>
							<i class="fa fa-times"></i>
						</button>
					</div>
				</div>
			</div>

			<div class="section-divider"></div>

			<!-- Return Schema / Discovery -->
			<div class="panel-section schema-section">
				<h5 class="section-title">{{ __("Return Schema") }}</h5>
				<div class="detected-keys-list mt-3">
					<div v-if="!detectedKeys.length" class="empty-state compact">
						<p>{{ __("No schema detected.") }}</p>
					</div>
					<div v-else class="keys-grid">
						<div
							v-for="k in detectedKeys"
							:key="k.fieldname || k.key"
							class="schema-tag"
							:title="`${k.fieldname || k.key} (${k.fieldtype || 'Data'})`"
						>
							<span class="tag-label">{{ k.label || k.fieldname || k.key }}</span>
							<span class="tag-type">{{ k.fieldtype || "Data" }}</span>
						</div>
					</div>
				</div>

				<div
					class="manual-schema-box mt-4"
					v-if="
						showResolvedSchema &&
						node.data?.return_type &&
						node.data?.return_type !== 'Yes / No'
					"
				>
					<label class="section-title mini mb-2">{{ __("Manual Schema (JSON)") }}</label>
					<div class="schema-editor-wrapper">
						<ControlFactory
							:df="resolvedSchemaField"
							:modelValue="serializeSchema(node.data?.resolved_output_schema)"
							@update:modelValue="updateField('resolved_output_schema', $event)"
						/>
					</div>
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
	const accent = getContract(actionType)?.css?.color || "var(--fr-primary)";
	return {
		"--fxr-node-accent": accent,
		"--fxr-node-accent-light": `color-mix(in srgb, ${accent} 12%, white)`,
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
		props.node.data[fieldname] = value;
		store.mark_dirty();
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
	store.mark_dirty();
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

function validate() {
	const errors = [];

	if (isReturnVariableMandatory.value && !props.node.data?.return_variable) {
		errors.push(__("Result Variable Name is required when handling results"));
	}

	outputMappings.value.forEach((m, idx) => {
		if ((m.source && !m.target) || (!m.source && m.target)) {
			errors.push(__("Variable Assignment #{0} is incomplete", [idx + 1]));
		}
	});
	return errors.length ? { valid: false, errors } : { valid: true };
}

defineExpose({ validate });
</script>

<style scoped>
.output-panel {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: var(--fr-bg-page);
}

.panel-header {
	padding: 16px 20px;
	border-bottom: 1px solid var(--fr-border);
	background: var(--fr-bg-surface);
}

.panel-header h4 {
	margin: 0 0 4px 0;
	font-size: 14px;
	font-weight: 700;
	color: var(--fr-text);
}

.panel-sections {
	flex: 1;
	overflow-y: auto;
	padding: 16px;
	display: flex;
	flex-direction: column;
	gap: 32px;
}

.panel-section {
	display: flex;
	flex-direction: column;
}

.section-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.section-title {
	margin: 0;
	font-size: 11px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	color: var(--fr-text-muted);
}

.section-divider {
	height: 1px;
	background: var(--fr-border-subtle);
	margin: 0;
}

.btn-add {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 4px 10px;
	background: var(--fr-gray-900);
	color: var(--fr-gray-0);
	border: none;
	border-radius: 6px;
	font-size: 11px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.15s;
}

.btn-add:hover {
	background: var(--fr-gray-800);
	transform: translateY(-1px);
}

.mapping-list {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.mapping-card {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	background: var(--fr-bg-surface);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	padding: 12px;
	box-shadow: var(--fr-shadow-sm);
	position: relative;
}

.mapping-inputs {
	flex: 1;
	display: flex;
	align-items: center;
	gap: 12px;
}

.input-wrapper {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.input-label {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	color: var(--fr-text-muted);
	letter-spacing: 0.02em;
}

.mapping-input-field {
	height: 32px;
	width: 100%;
	padding: 0 8px;
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	background: var(--fr-bg-muted);
	font-size: 12px;
	font-family: var(--fxr-font-mono);
	outline: none;
	transition: all 0.15s;
}

.mapping-input-field:focus {
	background: var(--fr-bg-surface);
	border-color: var(--fr-primary);
	box-shadow: 0 0 0 2px var(--fr-primary-subtle);
}

.mapping-arrow {
	color: var(--fr-text-muted);
	opacity: 0.5;
	margin-top: 18px;
}

.btn-remove {
	width: 20px;
	height: 20px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	background: var(--fr-gray-100);
	border: none;
	border-radius: 50%;
	color: var(--fr-text-muted);
	cursor: pointer;
	transition: all 0.15s;
	flex-shrink: 0;
	margin-top: -6px;
	margin-right: -6px;
}

.btn-remove:hover {
	background: #fee2e2;
	color: var(--fr-danger);
}

.empty-state.compact {
	padding: 20px;
	text-align: center;
	background: var(--fr-bg-muted);
	border: 1px dashed var(--fr-border);
	border-radius: var(--fr-radius-lg);
	color: var(--fr-text-muted);
	font-size: 12px;
}

.keys-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
}

.schema-tag {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 4px 10px;
	background: var(--fr-bg-surface);
	border: 1px solid var(--fr-border);
	border-radius: 20px;
	box-shadow: var(--fr-shadow-sm);
}

.tag-label {
	font-size: 12px;
	font-weight: 600;
	color: var(--fr-text);
}

.tag-type {
	font-size: 10px;
	font-weight: 700;
	color: var(--fr-text-muted);
	text-transform: uppercase;
	background: var(--fr-gray-100);
	padding: 1px 6px;
	border-radius: 4px;
}

.schema-editor-wrapper {
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	overflow: hidden;
	box-shadow: var(--fr-shadow-sm);
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}
.v2-scrollbar::-webkit-scrollbar-thumb {
	background: var(--fr-gray-300);
	border-radius: 10px;
}

.extra-small {
	font-size: 11px;
}

@media (max-width: 768px) {
	.mapping-inputs {
		flex-direction: column;
		align-items: stretch;
		gap: 8px;
	}
	.mapping-arrow {
		margin: 0;
		text-align: center;
		transform: rotate(90deg);
	}
}
</style>
