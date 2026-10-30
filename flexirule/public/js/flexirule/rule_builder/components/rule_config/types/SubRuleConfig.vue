<template>
	<div class="sub-rule-config">
		<div v-if="!node.data?.rule" class="empty-mode-state text-center p-5">
			<i class="fa fa-cube fa-3x text-muted mb-3 opacity-20"></i>
			<p class="text-muted">
				{{ __("Please select a Sub-Rule in the Setup panel to proceed.") }}
			</p>
		</div>

		<div v-else class="config-container">
			<div class="sub-section section-subcard">
				<h6>{{ __("Execution Permission") }}</h6>
				<ControlFactory
					:ref="setControlRef"
					:df="{
						fieldname: 'ignore_permissions',
						fieldtype: 'Check',
						label: __('Skip Permissions'),
						description: __(
							'Bypass callee permission checks for this sub-rule call. Requires audit reason.'
						),
						read_only: read_only,
					}"
					:modelValue="node?.data?.ignore_permissions"
					@update:modelValue="(val) => update_action_key('ignore_permissions', val)"
				/>
				<ControlFactory
					v-if="!!node?.data?.ignore_permissions"
					:ref="setControlRef"
					:df="{
						fieldname: 'permission_audit_reason',
						fieldtype: 'Small Text',
						label: __('Permission Audit Reason'),
						read_only: read_only,
						reqd: 1,
					}"
					:modelValue="node?.data?.permission_audit_reason"
					:showValidation="showValidation"
					@update:modelValue="(val) => update_action_key('permission_audit_reason', val)"
				/>
			</div>

			<div class="alert alert-info py-2 px-3 small mb-3">
				<i class="fa fa-info-circle"></i>
				{{ __("Configuring Sub-Rule: {0}").replace("{0}", node.data.rule) }}
			</div>
			<div v-if="contractLoading" class="alert alert-secondary py-2 px-3 small mb-3">
				<i class="fa fa-spinner fa-spin"></i> {{ __("Loading Sub-Rule interface...") }}
			</div>
			<div v-else-if="contractErrors.length" class="alert alert-warning py-2 px-3 small mb-3">
				<strong>{{ __("Sub-Rule interface needs attention") }}</strong>
				<div v-for="error in contractErrors" :key="error">{{ error }}</div>
			</div>
			<div
				v-else-if="subRuleContract && !subRuleContract.input_schema_declared"
				class="alert alert-light py-2 px-3 small mb-3"
			>
				{{
					__(
						"This Sub-Rule uses inferred legacy inputs. Declaring an Input Schema on the target Rule makes the interface explicit and validates mappings against it."
					)
				}}
			</div>

			<div class="sub-section section-subcard">
				<div class="d-flex justify-content-between align-items-center mb-2">
					<h6 class="mb-0">{{ __("Input Mappings") }}</h6>
					<div class="btn-group">
						<button
							class="btn btn-xs"
							:class="view === 'list' ? 'btn-primary' : 'btn-default'"
							@click="view = 'list'"
						>
							<i class="fa fa-list"></i>
						</button>
						<button
							class="btn btn-xs"
							:class="view === 'visual' ? 'btn-primary' : 'btn-default'"
							@click="view = 'visual'"
						>
							<i class="fa fa-exchange"></i>
						</button>
					</div>
					<button
						v-if="!read_only && view === 'list'"
						class="btn btn-xs btn-outline-primary"
						@click="add_mapping"
					>
						<i class="fa fa-plus"></i> {{ __("Add Mapping") }}
					</button>
				</div>
				<p class="text-muted small mb-2">
					{{ __("Map variables from the parent context to sub-rule parameters.") }}
				</p>

				<div v-if="view === 'list'" class="table-rows">
					<div v-for="(row, idx) in mapping_rows" :key="idx" class="row-item mapping-row">
						<div class="mapping-cell">
							<label class="small text-muted mb-1">{{ __("Parent Variable") }}</label>
							<ComboBoxControl
								:ref="setControlRef"
								fieldname="config.input_mapping.source"
								:df="{ label: '', fieldtype: 'Autocomplete' }"
								v-model="row.source"
								:get_query="get_variable_options"
								:read_only="read_only"
								:hideLabel="true"
								:showValidation="showValidation"
								@update:modelValue="sync_local_config"
							/>
						</div>
						<div class="mapping-arrow text-center">
							<i class="fa fa-arrow-right text-muted"></i>
						</div>
						<div class="mapping-cell">
							<label class="small text-muted mb-1">{{ __("Sub-Rule Param") }}</label>
							<select
								v-if="hasInputTargetOptions"
								class="form-control form-control-sm"
								v-model="row.target"
								:disabled="read_only"
								@change="sync_local_config"
							>
								<option value="">{{ __("Select Sub-Rule input") }}</option>
								<option
									v-for="target in inputTargetOptions"
									:key="target.fieldname"
									:value="target.fieldname"
								>
									{{ target.label }} ({{ target.fieldname }})
								</option>
								<option
									v-if="
										row.target &&
										!inputTargetOptions.some(
											(target) => target.fieldname === row.target
										)
									"
									:value="row.target"
								>
									{{ row.target }} — {{ __("not declared by target") }}
								</option>
							</select>
							<input
								v-else
								type="text"
								class="form-control form-control-sm"
								v-model="row.target"
								:placeholder="__('Sub-Rule Parameter')"
								:disabled="read_only"
								@input="sync_local_config"
							/>
						</div>
						<div class="mapping-actions">
							<button
								v-if="!read_only"
								class="btn btn-xs btn-link text-danger mt-4"
								@click="remove_mapping(idx)"
							>
								<i class="fa fa-trash"></i>
							</button>
						</div>
					</div>
					<div
						v-if="!mapping_rows.length"
						class="text-center p-3 border rounded dashed bg-light"
					>
						<span class="text-muted small">{{ __("No mappings defined") }}</span>
					</div>
				</div>

				<div v-else class="visual-mapper">
					<TransformControl
						:ref="setControlRef"
						fieldname="config.input_mapping"
						:modelValue="visual_mappings"
						:sourceSchema="source_schema"
						:targetSchema="target_schema"
						:readOnly="read_only"
						:showValidation="showValidation"
						@update:modelValue="update_visual_mappings"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, computed, onBeforeUpdate } from "vue";
import { useStore } from "../../../stores";
import { fromCodeString } from "../../../utils/serialization";
import ComboBoxControl from "../../../controls/ComboBoxControl.vue";
import TransformControl from "../../../controls/TransformControl.vue";
import ControlFactory from "../../../controls/ControlFactory.vue";

const props = defineProps({
	node: Object,
	read_only: Boolean,
	showValidation: { type: Boolean, default: false },
});

const store = useStore();
const emit = defineEmits(["update:field"]);

const mapping_rows = ref([]);
const view = ref("list");
const controlRefs = ref([]);
const subRuleContract = ref(null);
const contractLoading = ref(false);
const contractErrors = ref([]);
let contractRequestId = 0;

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

const source_schema = computed(() => {
	const vars = store.variables || [];
	return vars.map((v) => ({
		label: v.label || v.name,
		value: v.name || v.value,
		fieldtype: v.type || "Data",
	}));
});

const inputTargetOptions = computed(() => {
	const declared = Array.isArray(subRuleContract.value?.input_schema)
		? subRuleContract.value.input_schema
		: [];
	const existingTargets = mapping_rows.value.map((row) => row.target).filter(Boolean);
	const seen = new Set(declared.map((field) => field.fieldname));
	return [
		...declared,
		...existingTargets
			.filter((target) => !seen.has(target))
			.map((fieldname) => ({
				fieldname,
				label: `${fieldname} (${__("legacy mapping")})`,
				fieldtype: "Data",
				reqd: 0,
			})),
	];
});
const hasInputTargetOptions = computed(
	() => inputTargetOptions.value.length > 0 || !!subRuleContract.value?.input_schema_declared
);
const target_schema = computed(() =>
	inputTargetOptions.value.map((field) => ({
		label: field.label || field.fieldname,
		value: field.fieldname,
		fieldtype: field.fieldtype || "Data",
	}))
);

const visual_mappings = computed(() => {
	return mapping_rows.value.map((r) => ({
		source: r.source,
		target: r.target,
		source_label: r.source,
		target_label: r.target,
	}));
});

function update_visual_mappings(mappings) {
	mapping_rows.value = mappings.map((m) => ({
		source: m.source,
		target: m.target,
	}));
	sync_local_config();
}

// Method for Parent Variable autocomplete options
const get_variable_options = async () => {
	const vars = store.variables || [];
	return vars.map((v) => ({
		value: v.name || v.value,
		label: v.label || v.name,
		description: v.description || v.type || "",
	}));
};

function add_mapping() {
	mapping_rows.value.push({ source: "", target: "" });
	// Don't sync yet, wait for user input
}

function remove_mapping(idx) {
	mapping_rows.value.splice(idx, 1);
	sync_local_config();
}

function sync_local_config() {
	const mappings = mapping_rows.value
		.filter((r) => r.source || r.target) // Allow partial rows during edit
		.map((r) => ({ source: r.source, target: r.target }));

	// Update the 'config' object in node data
	const currentConfig =
		typeof props.node.data.config === "string"
			? fromCodeString(props.node.data.config)
			: props.node.data.config || {};

	const newConfig = {
		...currentConfig,
		input_mapping: mappings.length ? mappings : null,
	};

	emit("update:field", "config", newConfig);
}

function update_action_key(key, value) {
	emit("update:field", key, value);
}

function load_local_config() {
	const config =
		typeof props.node.data.config === "string"
			? fromCodeString(props.node.data.config)
			: props.node.data.config || {};
	const mappings = config.input_mapping || [];
	mapping_rows.value = Array.isArray(mappings)
		? mappings.map((m) => ({
				source: m.source || m.source_expression || "",
				target: m.target || "",
		  }))
		: [];
}

async function validate() {
	const errors = [];

	if (subRuleContract.value?.input_schema_declared) {
		const declaredInputs = new Map(
			(subRuleContract.value.input_schema || []).map((field) => [field.fieldname, field])
		);
		const mappedTargets = new Set(mapping_rows.value.map((row) => row.target).filter(Boolean));
		const unknownTargets = [...mappedTargets].filter((target) => !declaredInputs.has(target));
		if (unknownTargets.length) {
			errors.push(
				__("Mappings target inputs not declared by the selected Sub-Rule: {0}").replace(
					"{0}",
					unknownTargets.join(", ")
				)
			);
		}
		const missingRequired = [...declaredInputs.values()]
			.filter(
				(field) =>
					field.reqd && field.default == null && !mappedTargets.has(field.fieldname)
			)
			.map((field) => field.fieldname);
		if (missingRequired.length) {
			errors.push(
				__("Required Sub-Rule inputs are not mapped: {0}").replace(
					"{0}",
					missingRequired.join(", ")
				)
			);
		}
	}

	// 1. Core Control Validation (Aggregated)
	const results = await Promise.all(
		(controlRefs.value || []).map((ctrl) => {
			if (ctrl && typeof ctrl.validate === "function") {
				return ctrl.validate();
			}
			return { valid: true };
		})
	);
	results.forEach((res) => {
		if (!res.valid && res.errors) errors.push(...res.errors);
	});

	// 2. Logic-based Validation
	const incomplete = mapping_rows.value.find(
		(row) => (row.source && !row.target) || (!row.source && row.target)
	);
	if (incomplete) {
		errors.push(
			__("Each input mapping row must include both Parent Variable and Sub-Rule Param.")
		);
	}

	// 3. Permission Audit Reason (Global check)
	if (
		props.node?.data?.ignore_permissions &&
		!String(props.node?.data?.permission_audit_reason ?? "").trim()
	) {
		errors.push(__("Permission Audit Reason is required when bypassing permissions."));
	}

	return { valid: errors.length === 0, errors };
}

async function load_sub_rule_contract(ruleName) {
	const requestId = ++contractRequestId;
	if (!ruleName) {
		subRuleContract.value = null;
		contractErrors.value = [];
		contractLoading.value = false;
		return;
	}

	contractLoading.value = true;
	contractErrors.value = [];
	try {
		const response = await frappe.call({
			method: "flexirule.ruleflow.api.get_sub_rule_contract",
			args: { rule_name: ruleName },
		});
		if (requestId !== contractRequestId) return;
		const contract = response.message || null;
		subRuleContract.value = contract;
		contractErrors.value = contract?.errors || [];
		if (Array.isArray(contract?.output_schema)) {
			emit("update:field", "resolved_output_schema", contract.output_schema);
		}
	} catch (error) {
		if (requestId !== contractRequestId) return;
		subRuleContract.value = null;
		contractErrors.value = [error?.message || __("Unable to load Sub-Rule interface.")];
	} finally {
		if (requestId === contractRequestId) contractLoading.value = false;
	}
}

watch(
	() => props.node.data.rule,
	async (newRule) => {
		if (!store.available_rules.length) await store.fetch_available_rules();
		await load_sub_rule_contract(newRule);
	},
	{ immediate: true }
);

onMounted(() => {
	if (!store.available_rules.length) store.fetch_available_rules();
	load_local_config();
});

defineExpose({ validate });
</script>

<style scoped>
.config-container {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.section-subcard {
	border: 1px solid var(--fxr-border-subtle);
	border-radius: 8px;
	padding: 16px;
	background-color: var(--fxr-bg-card);
	box-shadow: var(--fxr-shadow-sm);
}

.table-rows {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.mapping-row {
	display: grid;
	grid-template-columns: 1fr 24px 1fr auto;
	gap: 8px;
	align-items: flex-start;
	padding-bottom: 12px;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.mapping-row:last-child {
	border-bottom: none;
	padding-bottom: 0;
}

.mapping-cell {
	display: flex;
	flex-direction: column;
}

.mapping-arrow {
	padding-top: 28px;
}

.dashed {
	border-style: dashed !important;
}

.fa-arrow-right {
	font-size: 14px;
	opacity: 0.5;
}
</style>
