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

			<div class="settings-grid">
				<div
					v-for="df in settings_fields"
					:key="df.fieldname"
					class="grid-item"
					:class="{ 'span-2': is_wide_field(df) }"
				>
					<template v-if="needs_autocomplete(df)">
						<ComboBoxControl
							:df="{
								...df,
								reqd: is_mandatory(df),
								read_only: is_field_read_only(df),
							}"
							:modelValue="get_normalized_value(df)"
							:get_query="(txt) => get_autocomplete_options(df)"
							:doc="node.data"
							:read_only="is_field_read_only(df)"
							@update:modelValue="update_normalized_value(df, $event)"
						/>
					</template>
					<template v-else>
						<ControlFactory
							:df="{
								...df,
								reqd: is_mandatory(df),
								read_only: is_field_read_only(df),
							}"
							:modelValue="get_normalized_value(df)"
							:read_only="is_field_read_only(df)"
							:doc="node.data"
							@update:modelValue="update_normalized_value(df, $event)"
						/>
					</template>
				</div>
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
import { computed, onMounted } from "vue";
import { useStore } from "../../stores";
import ControlFactory from "../../controls/ControlFactory.vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import {
	getContract,
	getFieldLabel,
	getOperationOptions,
	normalizeActionType,
} from "../../../core/contracts.js";
import { useNodeConfigPolicy } from "../../composables/useNodeConfigPolicy";
import { toCodeString, fromCodeString, isJsonField } from "../../utils/serialization";

const props = defineProps({ node: Object, readOnly: Boolean });
const emit = defineEmits(["update:field"]);
const store = useStore();

// ── Policy & Schema ───────────────────────────────────────────────────────
const actionType = computed(() => normalizeActionType(props.node?.data?.action_type || ""));
const operation = computed(() => props.node?.data?.operation || "");
const processName = computed(() => props.node?.data?.process_name || "");

const { getPolicyField, getPolicyValue } = useNodeConfigPolicy({
	actionType,
	operation,
	processName,
});

// ── Metadata-driven fields ───────────────────────────────────────────────
const LAYOUT_FIELDS = ["Section Break", "Column Break", "Tab Break"];

const rule_action_meta = computed(() => frappe.get_meta("Rule Action"));

const settings_fields = computed(() => {
	const meta = rule_action_meta.value;
	if (!meta || !meta.field_order) return [];

	const fields = [];
	let in_settings_section = false;

	for (const fieldname of meta.field_order) {
		const df = meta.fields.find((f) => f.fieldname === fieldname);
		if (!df) continue;

		if (df.fieldtype === "Section Break") {
			if (df.fieldname === "settings_section") {
				in_settings_section = true;
				continue;
			} else if (in_settings_section) {
				// Stop when we hit the next section
				break;
			}
		}

		if (in_settings_section) {
			// Skip layout fields
			if (LAYOUT_FIELDS.includes(df.fieldtype)) continue;

			// Policy Check: Hidden
			if (df.hidden) continue;
			if (getPolicyValue(df.fieldname, "hidden", false)) continue;

			// Depends On Check
			if (!evaluate_depends_on(df.depends_on)) continue;

			// Resolve Dynamic Label
			let resolved = { ...df };
			const policyLabel = getFieldLabel(actionType.value, df.fieldname, {
				operation: operation.value,
				processName: processName.value,
			});

			// Get policy overrides
			resolved = getPolicyField(resolved.fieldname, resolved);

			if (policyLabel) {
				resolved.label = __(policyLabel);
			}

			fields.push(resolved);
		}
	}
	return fields;
});

// ── Evaluators & Helpers ──────────────────────────────────────────────────
function evaluate_depends_on(expression) {
	if (!expression) return true;
	const doc = props.node?.data;
	if (!doc) return true;

	if (typeof expression === "boolean") return expression;

	if (expression.startsWith("eval:")) {
		try {
			const parent = store.rule_doc;
			return frappe.utils.eval(expression.substr(5), { doc, parent });
		} catch (e) {
			return false;
		}
	}
	return !!doc[expression];
}

function is_mandatory(df) {
	if (df.reqd) return true;
	if (!df.mandatory_depends_on) return false;
	return evaluate_depends_on(df.mandatory_depends_on);
}

function is_field_read_only(df) {
	if (props.readOnly) return true;
	if (df.read_only) return true;
	if (!df.read_only_depends_on) return false;
	return evaluate_depends_on(df.read_only_depends_on);
}

function is_wide_field(df) {
	return ["Small Text", "Text", "Code", "Markdown Editor", "HTML Editor"].includes(df.fieldtype);
}

function get_normalized_value(df) {
	const val = props.node?.data?.[df.fieldname];
	if (isJsonField(df)) {
		return toCodeString(val);
	}
	return val;
}

function update_normalized_value(df, value) {
	let nextValue = value;
	if (isJsonField(df)) {
		nextValue = fromCodeString(value);
	}
	emit("update:field", { fieldname: df.fieldname, value: nextValue });
}

function needs_autocomplete(df) {
	return (
		df.fieldtype === "Autocomplete" ||
		df.fieldtype === "Link" ||
		df.fieldtype === "Dynamic Link" ||
		df.fieldname === "operation" ||
		df.options === "action_id"
	);
}

async function get_autocomplete_options(df) {
	if (df.fieldname === "operation") {
		const options = getOperationOptions(actionType.value, { processName: processName.value });
		return options.map((op) => ({
			value: op.value || op.func_name,
			label: __(op.label || op.value || op.func_name),
			description: op.description || "",
		}));
	}
	if (df.options === "action_id") {
		return getNodeOptions();
	}
	return [];
}

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

onMounted(async () => {
	if (!frappe.get_meta("Rule Action")) {
		await frappe.model.with_doctype("Rule Action");
	}
});
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
</style>
