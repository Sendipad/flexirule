<template>
	<div class="action-settings-container">
		<!-- ═══════════════ DYNAMIC EXECUTION SETTINGS ═══════════════ -->
		<div class="settings-section">
			<h6 class="section-title-mini">{{ __("Execution Settings") }}</h6>

			<!-- Side-effect Warning Badge (if any) -->
			<div
				v-if="side_effect_warning"
				:class="['side-effect-warning', 'alert-' + side_effect_warning.type]"
			>
				<i :class="['fa', side_effect_warning.icon]"></i>
				<span>{{ side_effect_warning.message }}</span>
			</div>

			<div class="dynamic-settings-fields">
				<ActionFieldProperties
					:nodeData="node.data"
					:readOnly="readOnly"
					section="settings_section"
					:excludeFields="EXCLUDE_FIELDS"
					@update:field="(f, v) => emit('update:field', { fieldname: f, value: v })"
				/>
			</div>
		</div>

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
						<ComboBoxControl
							:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
							:modelValue="primaryNodeLabel"
							:get_query="getNodeOptions"
							:placeholder="__('Select next node…')"
							:read_only="readOnly"
							:hideLabel="true"
							@update:modelValue="onSelectPrimary"
						/>
					</div>

					<!-- Secondary path (Condition NO / Loop After Last / Switch default) -->
					<div class="flow-control-item" v-if="flowMeta.hasSecondary">
						<label class="flow-label">
							<span class="flow-dot" style="background: #ef4444"></span>
							{{ __(flowMeta.secondary) }}
						</label>
						<ComboBoxControl
							:df="{ fieldtype: 'Autocomplete', label: '', read_only: readOnly }"
							:modelValue="secondaryNodeLabel"
							:get_query="getNodeOptions"
							:placeholder="__('Select next node…')"
							:read_only="readOnly"
							:hideLabel="true"
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
import ActionFieldProperties from "../ActionFieldProperties.vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import { getContract, normalizeActionType } from "../../../core/contracts.js";

const props = defineProps({ node: Object, readOnly: Boolean });
const emit = defineEmits(["update:field"]);
const store = useStore();

const EXCLUDE_FIELDS = ["is_enabled"];

const actionType = computed(() => normalizeActionType(props.node?.data?.action_type || ""));
const operation = computed(() => props.node?.data?.operation || "");
const processName = computed(() => props.node?.data?.process_name || "");

// ── Side-effect Warning ───────────────────────────────────────────────────
const side_effect_warning = computed(() => {
	if (actionType.value !== "Process" || !processName.value || !operation.value) return null;
	const process = store.processes?.find((p) => p.name === processName.value);
	const op = process?.operations?.find((o) => o.func_name === operation.value);
	if (!op) return null;

	if (op.writes_to === "Database") {
		return {
			type: "danger",
			icon: "fa-database",
			message: __(
				"This operation writes directly to the database. Side-effects cannot be rolled back."
			),
		};
	} else if (op.writes_to === "Document") {
		return {
			type: "warning",
			icon: "fa-file-text",
			message: __("This operation modifies the document. Ensure this is intentional."),
		};
	}
	return null;
});

// ── Flow Control Logic ───────────────────────────────────────────────────
const contract = computed(() => getContract(actionType.value));
const isTerminal = computed(() => contract.value.terminal);

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
	emit("update:field", { fieldname: "next_step_if_true", value: id });
	store.reconnect_node_edge?.(props.node?.id, "true", id);
}

function onSelectSecondary(val) {
	const id = resolveId(val);
	emit("update:field", { fieldname: "next_step_if_false", value: id });
	store.reconnect_node_edge?.(props.node?.id, "false", id);
}
</script>

<style scoped>
.action-settings-container {
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.section-title-mini {
	font-size: 11px;
	font-weight: 800;
	color: var(--fxr-text-soft, #64748b);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	margin-bottom: 12px;
}
.section-divider {
	height: 1px;
	background: var(--fxr-border-subtle, #e2e8f0);
	margin: 8px 0;
}
.extra-small {
	font-size: 10px;
}

.side-effect-warning {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	padding: 8px 10px;
	border-radius: 4px;
	font-size: 11px;
	margin-bottom: 12px;
}

.side-effect-warning.alert-danger {
	background-color: var(--fxr-danger-soft);
	border: 1px solid var(--fxr-border-danger);
	color: var(--fxr-text-danger);
}

.side-effect-warning.alert-warning {
	background-color: var(--fxr-warning-soft);
	border: 1px solid var(--fxr-border-focus);
	color: var(--fxr-text-secondary);
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
	color: var(--fxr-text-strong, #374151);
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

/* Adjust ActionFieldProperties for settings bar layout */
:deep(.action-field-properties) {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16px;
}

:deep(.field-wrapper) {
	margin-bottom: 0;
}

/* Some fields might need full width in settings too */
:deep(.field-wrapper:has(.text-generator-control), .field-wrapper:has(textarea), .field-wrapper:has(.code-control)) {
	grid-column: 1 / -1;
}
</style>
