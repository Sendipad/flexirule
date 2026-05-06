<template>
	<div class="action-settings-container">
		<!-- ═══════════════ EXECUTION SETTINGS ═══════════════ -->
		<div class="settings-section">
			<h6 class="section-title-mini">{{ __("Execution Settings") }}</h6>
			<div class="settings-grid">
				<div class="grid-item">
					<ControlFactory
						:df="
							ro({
								fieldname: 'is_enabled',
								fieldtype: 'Check',
								label: __('Enabled'),
							})
						"
						:modelValue="node.data?.is_enabled"
						@update:modelValue="(v) => emit_field('is_enabled', v)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="
							ro({
								fieldname: 'is_async',
								fieldtype: 'Check',
								label: __('Run Asynchronously'),
							})
						"
						:modelValue="node.data?.is_async"
						@update:modelValue="(v) => emit_field('is_async', v)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="
							ro({
								fieldname: 'on_error',
								fieldtype: 'Select',
								label: __('On Error'),
								options: '\nStop\nContinue\nRetry\nRollback\nEscalate',
							})
						"
						:modelValue="node.data?.on_error"
						@update:modelValue="(v) => emit_field('on_error', v)"
					/>
				</div>
				<div class="grid-item" v-if="node.data?.on_error === 'Retry'">
					<ControlFactory
						:df="
							ro({
								fieldname: 'retry_count',
								fieldtype: 'Int',
								label: __('Retry Count'),
							})
						"
						:modelValue="node.data?.retry_count"
						@update:modelValue="(v) => emit_field('retry_count', v)"
					/>
				</div>
				<div class="grid-item">
					<ControlFactory
						:df="
							ro({ fieldname: 'timeout', fieldtype: 'Int', label: __('Timeout (s)') })
						"
						:modelValue="node.data?.timeout"
						@update:modelValue="(v) => emit_field('timeout', v)"
					/>
				</div>
			</div>
		</div>

		<!-- ═══════════════ OUTPUT SETTINGS ═══════════════ -->
		<!-- Hidden for Condition / Loop / Switch / Stop — they don't store a return variable -->
		<template v-if="showReturnVariable">
			<div class="section-divider my-4"></div>
			<div class="settings-section">
				<h6 class="section-title-mini">{{ __("Output Settings") }}</h6>
				<div class="settings-grid">
					<div class="grid-item span-2">
						<ControlFactory
							:df="
								ro({
									fieldname: 'return_variable',
									fieldtype: 'Data',
									label: __('Return Variable Name'),
									placeholder: __('e.g. my_result'),
									description: __(
										'The variable where the action result will be stored.'
									),
								})
							"
							:modelValue="node.data?.return_variable"
							@update:modelValue="(v) => emit_field('return_variable', v)"
						/>
					</div>
				</div>
			</div>
		</template>

		<!-- ═══════════════ FLOW CONTROL ═══════════════ -->
		<!-- Hidden for terminal actions (Stop) -->
		<template v-if="!isTerminal">
			<div class="section-divider my-4"></div>
			<div class="settings-section">
				<h6 class="section-title-mini">{{ __("Flow Control") }}</h6>
				<p class="text-muted extra-small mb-3">
					{{ __("Select the next node to execute on each path.") }}
				</p>
				<div class="flow-control-grid">
					<!-- Primary path -->
					<div class="flow-control-item">
						<label class="flow-label">
							<span
								class="flow-dot"
								:style="{ background: flowMeta.primaryColor }"
							></span>
							{{ __(flowMeta.primary) }}
						</label>
						<AutocompleteControl
							:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
							:modelValue="primaryNodeLabel"
							:get_options="getNodeOptions"
							:placeholder="__('Select next node…')"
							:read_only="readOnly"
							@update:modelValue="onSelectPrimary"
						/>
					</div>

					<!-- Secondary path (Condition NO / Loop After Last / Switch default) -->
					<div class="flow-control-item" v-if="flowMeta.hasSecondary">
						<label class="flow-label">
							<span class="flow-dot" style="background: #ef4444"></span>
							{{ __(flowMeta.secondary) }}
						</label>
						<AutocompleteControl
							:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
							:modelValue="secondaryNodeLabel"
							:get_options="getNodeOptions"
							:placeholder="__('Select next node…')"
							:read_only="readOnly"
							@update:modelValue="onSelectSecondary"
						/>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../stores";
import ControlFactory from "../../controls/ControlFactory.vue";
import AutocompleteControl from "../../controls/AutocompleteControl.vue";
import { getContract, getDerivedFieldState } from "../../../core/contracts.js";

const props = defineProps({ node: Object, readOnly: Boolean });
const emit = defineEmits(["update:field"]);
const store = useStore();

// ── Helpers ───────────────────────────────────────────────────────────────
const ro = (field) => ({ ...field, read_only: props.readOnly });
const emit_field = (fieldname, value) => emit("update:field", { fieldname, value });

// ── Contract state ────────────────────────────────────────────────────────
const actionType = computed(() => props.node?.data?.action_type);
const contract = computed(() => getContract(actionType.value));
const isTerminal = computed(() => contract.value.terminal);

const showReturnVariable = computed(() => {
	const state = getDerivedFieldState(
		actionType.value,
		"return_variable",
		props.node?.data || {},
		store.rule_doc || {},
		{
			operation: props.node?.data?.operation,
			processName: props.node?.data?.process_name,
		}
	);
	if (state.hidden) return false;
	return !["Condition", "Loop", "Switch", "Stop", "Entry Action"].includes(actionType.value);
});

// ── Flow control metadata per action type ─────────────────────────────────
const FLOW_META = {
	Condition: {
		primary: "YES (If True)",
		secondary: "NO (If False)",
		primaryColor: "#22c55e",
		hasSecondary: true,
	},
	Loop: {
		primary: "For Each (body)",
		secondary: "After Last (continue)",
		primaryColor: "#f59e0b",
		hasSecondary: true,
	},
	Switch: {
		primary: "True / Matched",
		secondary: "Default / False",
		primaryColor: "#06b6d4",
		hasSecondary: true,
	},
};
const flowMeta = computed(
	() =>
		FLOW_META[actionType.value] ?? {
			primary: "Next Step",
			secondary: null,
			primaryColor: "#6366f1",
			hasSecondary: false,
		}
);

// ── Node autocomplete ─────────────────────────────────────────────────────
function getNodeOptions() {
	const cid = props.node?.id;
	return (store.nodes || [])
		.filter((n) => n.id !== cid && n.type !== "start" && n.id !== "root")
		.map((n) => ({ label: n.data?.action_label || n.label || n.id, value: n.id }));
}

function resolveLabel(nodeId) {
	if (!nodeId) return "";
	const n = (store.nodes || []).find((nd) => nd.id === nodeId);
	return n ? n.data?.action_label || n.label || nodeId : nodeId;
}

const primaryNodeLabel = computed(() => resolveLabel(props.node?.data?.next_step_if_true));
const secondaryNodeLabel = computed(() => resolveLabel(props.node?.data?.next_step_if_false));

function resolveId(labelOrId) {
	if (!labelOrId) return null;
	const byId = (store.nodes || []).find((n) => n.id === labelOrId);
	if (byId) return byId.id;
	const byLabel = (store.nodes || []).find(
		(n) => (n.data?.action_label || n.label) === labelOrId
	);
	return byLabel ? byLabel.id : labelOrId;
}

function onSelectPrimary(val) {
	const id = resolveId(val);
	emit_field("next_step_if_true", id);
	store.reconnect_node_edge?.(props.node?.id, "true", id);
}

function onSelectSecondary(val) {
	const id = resolveId(val);
	emit_field("next_step_if_false", id);
	store.reconnect_node_edge?.(props.node?.id, "false", id);
}
</script>

<style scoped>
.action-settings-container {
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.settings-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16px;
}
.grid-item.span-2 {
	grid-column: 1 / -1;
}

.section-title-mini {
	font-size: 11px;
	font-weight: 800;
	color: #64748b;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	margin-bottom: 12px;
}
.section-divider {
	height: 1px;
	background: #e2e8f0;
	margin: 8px 0;
}
.extra-small {
	font-size: 10px;
}

/* ── Flow Control ── */
.flow-control-grid {
	display: flex;
	flex-direction: column;
	gap: 14px;
}
.flow-control-item {
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.flow-label {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 11px;
	font-weight: 700;
	color: #374151;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	margin: 0;
}
.flow-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	flex-shrink: 0;
}

:deep(.autocomplete-control) {
	border-radius: 8px;
	font-size: 13px;
}
</style>
