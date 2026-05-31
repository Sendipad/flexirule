<script setup>
/**
 * SimpleCondition - Leaf condition editor (left op right)
 * Uses backend-driven operator configuration
 */
import ControlFactory from "../../controls/ControlFactory.vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import ComboBoxControl from "../../controls/ComboBoxControl.vue";
import { useMetaStore } from "../../stores/useMetaStore";
import { inject, ref, computed, watch } from "vue";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["remove"]);
const metaStore = useMetaStore();

// Injected operator config from ConditionBuilder
const operatorConfig = inject(
	"operatorConfig",
	ref({ fieldtype_operators: {}, operator_labels: {} })
);

const store = inject("store");
const variableOptions = inject("variableOptions", ref([]));

// Dynamic Link State
const dynamicLinkDocType = ref("");

// Find the selected field metadata
const lastValidField = ref(null);
const selectedField = computed(() => {
	const ref = props.node.left?.ref;
	if (!ref) return null;
	const found = props.docFields.find((f) => f.value === ref);
	if (found) {
		lastValidField.value = found;
		return found;
	}
	// Fallback to last known good metadata during transitions (e.g. drag-and-drop)
	if (lastValidField.value?.value === ref) {
		return lastValidField.value;
	}
	return null;
});

const doctypeContextRefs = ["doctype", "rule.document_type", "caller.document_type"];
const isDoctypeContextField = computed(() =>
	doctypeContextRefs.includes(selectedField.value?.value)
);

// Available operators based on field type - backend-driven
const operators = computed(() => {
	const config = operatorConfig.value;
	const ft = selectedField.value?.fieldtype || "Data";
	const fieldOps = selectedField.value?.operators;

	// Get valid operators for this fieldtype
	const validOps =
		Array.isArray(fieldOps) && fieldOps.length
			? fieldOps
			: config.fieldtype_operators?.[ft] ||
			  config.fieldtype_operators?.["_default"] || ["==", "!=", "is_set", "is_not_set"];
	const labels = config.operator_labels || {};

	return validOps.map((op) => ({
		value: op,
		label: __(labels[op] || op),
	}));
});

// Computed Schema for Value Input
const valueFieldSchema = computed(() => {
	if (!selectedField.value) return { fieldtype: "Data" };

	if (
		["length_eq", "length_gt", "length_gte", "length_lt", "length_lte"].includes(props.node.op)
	) {
		return {
			fieldtype: "Int",
			label: __("Length"),
			placeholder: __("e.g. 1"),
		};
	}

	// Helper operators
	if (props.node.op === "has_field") {
		return {
			fieldtype: "Data",
			label: __("DocField"),
			placeholder: __("e.g. customer"),
		};
	}

	let schema = { ...selectedField.value };

	// Use DocType picker for context doctype filters
	if (isDoctypeContextField.value) {
		if (["in", "not in"].includes(props.node.op)) {
			schema = {
				...schema,
				fieldtype: "MultiSelectList",
				displayMode: "compact",
				options: [],
				get_data: async (txt) => {
					return await metaStore.search_link_options({
						doctype: "DocType",
						txt: txt || "",
						page_length: 40,
					});
				},
				placeholder: __("Select DocTypes"),
			};
		} else {
			schema = {
				...schema,
				fieldtype: "Link",
				options: "DocType",
				placeholder: __("Select DocType"),
			};
		}
	}

	// 1. DocStatus Handling
	if (schema.value === "doc.docstatus" || schema.fieldname === "docstatus") {
		schema.fieldtype = "Select";
		schema.options = [
			{ label: __("Draft"), value: 0 },
			{ label: __("Submitted"), value: 1 },
			{ label: __("Cancelled"), value: 2 },
		];
	}

	// 2. Multi-Select Handling for IN/NOT IN
	const isMultiSelectOp = ["in", "not in", "in list", "not in list"].includes(props.node.op);
	const isEqualsOp = ["==", "!=", "equal", "equals", "not equal", "not equals"].includes(
		props.node.op
	);

	if (isMultiSelectOp && !isDoctypeContextField.value) {
		const originalFieldtype = schema.fieldtype;
		const originalOptions = schema.options;

		if (originalFieldtype === "Link" && originalOptions) {
			schema.fieldtype = "MultiSelectList";
			schema.displayMode = "compact";
			schema.get_data = async (txt) => {
				if (!originalOptions) return [];
				return await metaStore.search_link_options({
					doctype: originalOptions,
					txt: txt || "",
					page_length: 40,
				});
			};
		} else if (originalFieldtype === "Select") {
			schema.fieldtype = "MultiCheck";
			if (typeof originalOptions === "string") {
				schema.options = originalOptions
					.split("\n")
					.map((opt) => opt.trim())
					.filter(Boolean);
			} else if (Array.isArray(originalOptions)) {
				schema.options = originalOptions;
			} else {
				schema.options = [];
			}
		} else {
			schema.fieldtype = "MultiSelect";
			schema.options = [];
		}
	} else if (isEqualsOp && schema.fieldtype === "Link") {
		// Ensure Link dropdown is shown for equality operators
		schema.fieldtype = "Link";
	}

	// 3. Dynamic Link Handling (Step 2: The actual link picker)
	if (schema.fieldtype === "Dynamic Link") {
		if (dynamicLinkDocType.value) {
			schema.fieldtype = "Link";
			schema.options = dynamicLinkDocType.value;
		} else {
			// If no doctype selected, show Data or ReadOnly
			schema.fieldtype = "Data";
			schema.read_only = 1;
			schema.placeholder = __("Select DocType first");
		}
	}

	return schema;
});

const valueControlKey = computed(() => {
	const schema = valueFieldSchema.value || {};
	return [
		selectedField.value?.value || "",
		props.node.op || "",
		schema.fieldtype || "",
		schema.options || "",
		dynamicLinkDocType.value || "",
	].join("|");
});

function isStructuredValue(val) {
	return Boolean(val && typeof val === "object" && !Array.isArray(val) && val.mode);
}

function ensureStructuredValue(rawValue) {
	if (isStructuredValue(rawValue)) return rawValue;
	return { mode: "static", value: rawValue };
}

function getStaticDefaultForOperator() {
	return ["in", "not in", "in list", "not in list"].includes(props.node.op) ? [] : "";
}

// Wrapped Value for Link/Dynamic Link Tuple handling
const wrappedValue = computed({
	get() {
		const val = props.node.right?.value;
		const ft = selectedField.value?.fieldtype;

		// Non-link field or context-doctype: always use structured object.
		if ((ft !== "Link" && ft !== "Dynamic Link") || isDoctypeContextField.value) {
			if (val === undefined || val === null || val === "") {
				return { mode: "static", value: getStaticDefaultForOperator() };
			}
			return ensureStructuredValue(val);
		}

		// Link tuple [DocType, ValuePayload]
		if (Array.isArray(val) && val.length === 2 && typeof val[0] === "string") {
			const tupleValue = val[1];
			if (tupleValue === undefined || tupleValue === null || tupleValue === "") {
				return { mode: "static", value: getStaticDefaultForOperator() };
			}
			return ensureStructuredValue(tupleValue);
		}

		if (val === undefined || val === null || val === "") {
			return { mode: "static", value: getStaticDefaultForOperator() };
		}

		return ensureStructuredValue(val);
	},
	set(newVal) {
		const ft = selectedField.value?.fieldtype;
		const normalized = ensureStructuredValue(newVal);

		if (!props.node.right || typeof props.node.right !== "object") {
			props.node.right = {};
		}

		if ((ft !== "Link" && ft !== "Dynamic Link") || isDoctypeContextField.value) {
			props.node.right.value = normalized;
			return;
		}

		// Structured non-static values should not be wrapped inside link tuples.
		if (normalized.mode !== "static") {
			props.node.right.value = normalized;
			return;
		}

		let docType = "";
		if (ft === "Link") {
			docType = selectedField.value.options;
		} else if (ft === "Dynamic Link") {
			docType = dynamicLinkDocType.value;
		}

		if (!docType) {
			props.node.right.value = normalized;
			return;
		}

		// Static link values keep tuple semantics for evaluator/compiler compatibility.
		props.node.right.value = [docType, normalized.value];
	},
});

watch(
	() => [selectedField.value?.fieldtype, props.node.op],
	() => {
		if (!props.node.right || typeof props.node.right !== "object") {
			props.node.right = { value: { mode: "static", value: getStaticDefaultForOperator() } };
			return;
		}
		if (props.node.right.value === undefined) {
			props.node.right.value = { mode: "static", value: getStaticDefaultForOperator() };
		}
	},
	{ immediate: true }
);
</script>

<template>
	<div class="simple-condition">
		<div class="condition-main-row">
			<!-- Field -->
			<div class="condition-col field-col">
				<ComboBoxControl
					:df="{ label: '', fieldtype: 'FieldPicker', read_only: readOnly }"
					v-model="node.left.ref"
					:options="docFields"
					:read_only="readOnly"
					:trigger="'button'"
					:hideLabel="true"
					:rule="store?.rule_doc"
					:context="store?.rule_doc"
					class="w-100 m-0"
				/>
			</div>

			<!-- Operator -->
			<div class="condition-col operator-col">
				<select v-model="node.op" class="fxr-select operator-select" :disabled="readOnly">
					<option v-for="op in operators" :key="op.value" :value="op.value">
						{{ op.label }}
					</option>
				</select>
			</div>

			<!-- Value Group -->
			<div
				class="condition-col value-group-col"
				v-if="
					![
						'is_set',
						'is_not_set',
						'is_submittable',
						'is_empty',
						'is_not_empty',
					].includes(node.op)
				"
			>
				<div class="value-input-wrapper">
					<div
						v-if="selectedField?.fieldtype === 'Dynamic Link'"
						class="dynamic-dt-picker"
					>
						<ControlFactory
							:df="{
								fieldtype: 'Link',
								options: 'DocType',
								placeholder: __('Select DocType'),
								read_only: readOnly,
							}"
							v-model="dynamicLinkDocType"
							:hideLabel="true"
						/>
					</div>

					<FlexValueControl
						:key="valueControlKey"
						v-model="wrappedValue"
						:context="{
							df: valueFieldSchema,
							operator: node.op,
							referenceDoctype:
								valueFieldSchema.options || store?.rule_doc?.document_type,
						}"
						:engine="store"
						:doc="store?.rule_doc"
						:variableOptions="variableOptions"
						:readOnly="readOnly"
						:disabled="readOnly"
						class="w-100 min-w-0"
					/>
				</div>
			</div>
			<div v-else class="condition-col empty-value-col"></div>

			<!-- Remove -->
			<div class="condition-col action-col" v-if="!readOnly">
				<button
					class="fxr-btn fxr-btn--icon fxr-btn--danger"
					@click="emit('remove')"
					:title="__('Remove')"
				>
					<i class="fa fa-trash"></i>
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped>
.simple-condition {
	background: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	padding: var(--fxr-space-1) var(--fxr-space-2);
	transition: border-color var(--fxr-transition-fast), background-color var(--fxr-transition-fast);
}

.simple-condition:hover {
	border-color: var(--fxr-border-strong);
}

.condition-main-row {
	display: grid;
	grid-template-columns: 1.5fr 0.7fr 2.6fr auto;
	gap: var(--fxr-space-2);
	align-items: center;
	overflow: visible !important;
	position: relative;
	z-index: 1;
}

.condition-col {
	min-width: 0;
}

.operator-select {
	font-weight: var(--fxr-weight-semibold);
	color: var(--fxr-text);
	background-color: var(--fxr-bg-muted);
}

.value-group-col {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-1);
	background: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	padding: 2px;
}

.value-input-wrapper {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	overflow: visible !important;
}

.dynamic-dt-picker {
	margin-bottom: var(--fxr-space-1);
}

.condition-main-row :deep(.form-control) {
	height: var(--fxr-input-height);
	font-size: var(--fxr-input-font-size);
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x);
	border: 1px solid transparent;
}

.condition-main-row :deep(.fxr-control),
.condition-main-row :deep(.combobox-container),
.condition-main-row :deep(.multi-select-list) {
	width: 100%;
	min-width: 0;
}

.condition-main-row :deep(.form-control:focus) {
	border-color: var(--fxr-node-accent, var(--fxr-accent));
	box-shadow: 0 0 0 2px var(--fxr-node-accent-light, var(--fxr-accent-light));
}

.empty-value-col {
	flex: 1;
}

/* Responsive adjustments */
@media (max-width: 768px) {
	.condition-main-row {
		display: flex;
		flex-direction: column;
		gap: var(--fxr-space-2);
		align-items: stretch;
	}
	.condition-col {
		width: 100%;
	}
	.action-col {
		align-self: flex-end;
	}
}
</style>
