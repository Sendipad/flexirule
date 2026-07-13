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
							<input
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

const target_schema = computed(() => {
	// For now, we use existing targets as the schema.
	// In the future, we should fetch actual sub-rule params.
	const targets = mapping_rows.value.map((r) => r.target).filter(Boolean);
	return [...new Set(targets)].map((t) => ({
		label: t,
		value: t,
		fieldtype: "Data",
	}));
});

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
	if (props.node?.data?.ignore_permissions && !props.node?.data?.permission_audit_reason) {
		errors.push(__("Permission Audit Reason is required when bypassing permissions."));
	}

	return { valid: errors.length === 0, errors };
}

watch(
	() => props.node.data.rule,
	(newRule) => {
		if (newRule) {
			store.fetch_available_rules();
		}
	}
);

onMounted(() => {
	if (!store.available_rules.length) {
		store.fetch_available_rules();
	}
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
