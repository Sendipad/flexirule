<template>
	<div class="action-settings-container">
		<div v-for="(section, sIdx) in visibleSections" :key="section.id" class="settings-section">
			<h6 v-if="section.label" class="section-title-mini">{{ __(section.label) }}</h6>
			<div class="settings-grid">
				<div
					v-for="df in section.fields"
					:key="df.fieldname"
					class="grid-item"
					:class="{ 'span-2': isFullWidth(df) }"
				>
					<!-- Button fields -->
					<template v-if="isButtonField(df)">
						<button class="btn btn-default btn-sm w-100" @click="handleButtonClick(df)">
							<i v-if="getButtonIcon(df)" :class="['fa', getButtonIcon(df)]"></i>
							{{ __(df.label) }}
						</button>
					</template>

					<!-- Autocomplete / Link fields -->
					<template v-else-if="needsAutocomplete(df)">
						<ComboBoxControl
							ref="controlRefs"
							:df="{
								...df,
								reqd: isMandatory(df),
								read_only: isReadOnly(df),
							}"
							:modelValue="getDisplayValue(df)"
							:doctype="getDoctypeForLink(df)"
							:get_query="(txt) => getAutocompleteOptions(df, txt)"
							:doc="node.data"
							:read_only="isReadOnly(df)"
							:showValidation="showValidation"
							@update:modelValue="updateNormalizedValue(df, $event)"
						/>
					</template>

					<!-- Standard fields -->
					<template v-else>
						<ControlFactory
							ref="controlRefs"
							:df="{
								...df,
								reqd: isMandatory(df),
								read_only: isReadOnly(df),
							}"
							:modelValue="getNormalizedValue(df)"
							:read_only="isReadOnly(df)"
							:showValidation="showValidation"
							:doc="node.data"
							@update:modelValue="updateNormalizedValue(df, $event)"
						/>
					</template>
				</div>
			</div>
			<div v-if="sIdx < visibleSections.length - 1" class="section-divider my-4"></div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUpdate } from "vue";
import { useStore } from "../../stores";
import ControlFactory from "../../controls/ControlFactory.vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import {
	getContract,
	getFieldLabel,
	getOperationOptions,
	getActionTypeOptions,
} from "../../../core/contracts.js";
import { useNodeConfigPolicy } from "../../composables/useNodeConfigPolicy";
import { toCodeString, fromCodeString, isJsonField } from "../../utils/serialization";

const props = defineProps({
	node: Object,
	readOnly: Boolean,
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:field", "open:conditions", "open:config"]);

const store = useStore();
const { getPolicyField, getPolicyValue } = useNodeConfigPolicy({
	actionType: () => props.node?.data?.action_type || "",
	operation: () => props.node?.data?.operation || "",
	processName: () => props.node?.data?.process_name || "",
});

const LAYOUT_FIELDS = ["Section Break", "Column Break", "Tab Break"];

const ruleActionMeta = computed(() => frappe.get_meta("Rule Action"));

const docFields = computed(() => {
	if (!ruleActionMeta.value?.fields) return [];

	return ruleActionMeta.value.fields
		.filter((df) => {
			if (LAYOUT_FIELDS.includes(df.fieldtype)) return false;
			return true;
		})
		.map((df) => {
			let resolved = { ...df, hidden: false };
			const actionType = props.node?.data?.action_type;
			const policyLabel = actionType
				? getFieldLabel(actionType, df.fieldname, {
						operation: props.node?.data?.operation,
						processName: props.node?.data?.process_name,
				  })
				: null;

			resolved = getPolicyField(resolved.fieldname, resolved);

			if (policyLabel) {
				resolved.label = __(policyLabel);
			}
			return resolved;
		});
});

const visibleSections = computed(() => {
	if (!ruleActionMeta.value?.fields) return [];

	const sections = [];
	let currentSection = { id: "default", label: "", fields: [] };

	ruleActionMeta.value.fields.forEach((df, idx) => {
		if (df.fieldtype === "Section Break") {
			if (currentSection.fields.length > 0) {
				sections.push(currentSection);
			}
			currentSection = {
				id: df.fieldname || `section_${idx}`,
				label: df.label || "",
				fields: [],
			};
		} else if (!LAYOUT_FIELDS.includes(df.fieldtype)) {
			const processedField = docFields.value.find((f) => f.fieldname === df.fieldname);
			if (processedField) {
				currentSection.fields.push(processedField);
			}
		}
	});

	if (currentSection.fields.length > 0) {
		sections.push(currentSection);
	}

	return sections;
});

function evaluateDependsOn(expression) {
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

	const value = doc[expression];
	return Array.isArray(value) ? !!value.length : !!value;
}

function isMandatory(df) {
	if (df.reqd) return true;
	if (!df.mandatory_depends_on) return false;
	return evaluateDependsOn(df.mandatory_depends_on);
}

function isReadOnly(df) {
	if (props.readOnly) return true;
	if (df.read_only) return true;
	if (!df.read_only_depends_on) return false;
	return evaluateDependsOn(df.read_only_depends_on);
}

function getNormalizedValue(df) {
	const val = props.node?.data?.[df.fieldname];
	return isJsonField(df) ? toCodeString(val) : val;
}

function getDisplayValue(df) {
	const val = props.node?.data?.[df.fieldname];
	if (df.options === "action_id" && val) {
		const targetNode = (store.nodes || []).find((n) => n.id === val);
		return targetNode ? targetNode.data?.action_label || targetNode.label || val : val;
	}
	return getNormalizedValue(df);
}

function updateNormalizedValue(df, value) {
	let nextValue = value;
	if (isJsonField(df)) {
		nextValue = fromCodeString(value);
	}

	// Resolve Label back to ID if it's an action_id field
	if (df.options === "action_id" && nextValue) {
		const target = (store.nodes || []).find(
			(n) => n.id === nextValue || (n.data?.action_label || n.label) === nextValue
		);
		if (target) {
			nextValue = target.id;
		}
	}

	const oldValue = props.node?.data?.[df.fieldname];
	if (oldValue === nextValue) return;

	// Emit with standard object signature expected by RuleConfigModal
	emit("update:field", { fieldname: df.fieldname, value: nextValue });

	// Handle flow control edge reconnection
	if (df.fieldname === "next_step_if_true" || df.fieldname === "next_step_if_false") {
		const branch = df.fieldname === "next_step_if_true" ? "true" : "false";
		store.reconnect_node_edge?.(props.node?.id, branch, nextValue);
	}
}

function isButtonField(df) {
	return df.fieldtype === "Button";
}

function getButtonIcon(df) {
	if (df.fieldname === "configure_operation" || df.fieldname === "configures") return "fa-cog";
	if (df.fieldname === "set_conditions") return "fa-code-fork";
	return null;
}

function handleButtonClick(df) {
	if (df.fieldname === "configure_operation" || df.fieldname === "configures") {
		emit("open:config");
	} else if (df.fieldname === "set_conditions") {
		emit("open:conditions");
	}
}

function needsAutocomplete(df) {
	return (
		["Autocomplete", "Link", "Dynamic Link"].includes(df.fieldtype) ||
		df.options === "action_id"
	);
}

function getDoctypeForLink(df) {
	if (df.fieldtype === "Dynamic Link") {
		return props.node?.data?.[df.options] || "";
	}
	return df.options || df.target_doctype;
}

async function getAutocompleteOptions(df, txt) {
	if (df.fieldname === "action_type") {
		return getActionTypeOptions().map((t) => ({
			value: t,
			label: window.__ ? __(t) : t,
		}));
	}

	if (df.options === "action_id") {
		const currentId = props.node?.data?.action_id;
		return (store.nodes || [])
			.filter((n) => n.id !== currentId && n.type !== "start" && n.id !== "root")
			.map((n) => ({
				value: n.id,
				label: n.data?.action_label || n.label || n.id,
			}));
	}
	// For other Link fields, return null to let ComboBoxControl handle standard search
	return null;
}

function isFullWidth(df) {
	return ["Code", "Text", "Small Text", "Long Text"].includes(df.fieldtype);
}

const controlRefs = ref([]);
onBeforeUpdate(() => {
	controlRefs.value = [];
});

async function validate() {
	const results = await Promise.all(
		(controlRefs.value || []).map((ref) => {
			if (ref && typeof ref.validate === "function") {
				return ref.validate();
			}
			return { valid: true };
		})
	);
	const errors = results.flatMap((r) => r.errors || []);
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });

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
	gap: 8px;
}

.settings-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

.grid-item.span-2 {
	grid-column: 1 / -1;
}

.section-title-mini {
	font-size: 11px;
	font-weight: 800;
	color: var(--fxr-text-soft);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	margin-bottom: 12px;
	padding-bottom: 4px;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.section-divider {
	height: 1px;
	background: var(--fxr-border-subtle);
	margin: 8px 0;
}

:deep(.fxr-control-wrapper) {
	margin-bottom: 0;
}

.w-100 {
	width: 100%;
}
</style>
