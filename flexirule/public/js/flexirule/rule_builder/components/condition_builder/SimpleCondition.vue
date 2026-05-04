<script setup>
/**
 * SimpleCondition - Leaf condition editor (left op right)
 * Uses backend-driven operator configuration
 */
import ControlFactory from "../../controls/ControlFactory.vue";
import SelectControl from "../../controls/SelectControl.vue";
import FieldPickerControl from "../../controls/FieldPickerControl.vue";
import ContextPicker from "../ContextPicker.vue";
import { inject, ref, computed, watch, nextTick } from "vue";

const props = defineProps({
	node: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["remove"]);

// Injected operator config from ConditionBuilder
const operatorConfig = inject(
	"operatorConfig",
	ref({ fieldtype_operators: {}, operator_labels: {} })
);

const context = inject("conditionContext", { alias: "doc" });

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
				options: [],
				get_data: async (txt) => {
					const rows = await frappe.db.get_link_options("DocType", txt || "");
					return (rows || []).map((row) => ({
						value: row.value || row,
						description: row.description || "",
					}));
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
			schema.get_data = async (txt) => {
				if (!originalOptions) return [];
				try {
					const rows = await frappe.db.get_link_options(originalOptions, txt || "");
					return (rows || []).map((row) => ({
						value: row.value || row,
						description: row.description || "",
					}));
				} catch (e) {
					console.error("MultiSelectList fetch error:", e);
					return [];
				}
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

// Wrapped Value for Link/Dynamic Link Tuple handling
const wrappedValue = computed({
	get() {
		const val = props.node.right?.value;
		const ft = selectedField.value?.fieldtype;
		const op = props.node.op;

		// If not a Link/Dynamic Link, return raw value
		if ((ft !== "Link" && ft !== "Dynamic Link") || isDoctypeContextField.value) return val;

		// If value is empty, return empty
		if (val === undefined || val === null || val === "")
			return op === "in" || op === "not in" ? [] : "";

		// If it's a tuple [DocType, Value], return Value
		if (Array.isArray(val) && val.length === 2 && typeof val[0] === "string") {
			return val[1];
		}

		// Legacy/Fallback: return raw value
		return val;
	},
	set(newVal) {
		const ft = selectedField.value?.fieldtype;

		if ((ft !== "Link" && ft !== "Dynamic Link") || isDoctypeContextField.value) {
			props.node.right.value = newVal;
			return;
		}

		// Determine DocType
		let docType = "";
		if (ft === "Link") {
			docType = selectedField.value.options;
		} else if (ft === "Dynamic Link") {
			docType = dynamicLinkDocType.value;
		}

		if (!docType) {
			// Should not happen if UI is correct, but falback
			props.node.right.value = newVal;
			return;
		}

		// Wrap it: [DocType, Value]
		props.node.right.value = [docType, newVal];
	},
});

// Watch for changes in existing node value to init dynamicLinkDocType if needed
watch(
	() => props.node,
	(newNode) => {
		// Attempt to extract existing Dynamic Link DocType from saved tuple
		if (selectedField.value?.fieldtype === "Dynamic Link" && !dynamicLinkDocType.value) {
			const val = newNode.right?.value;
			if (Array.isArray(val) && val.length === 2 && typeof val[0] === "string") {
				dynamicLinkDocType.value = val[0];
			}
		}
	},
	{ immediate: true, deep: true }
);

// Value Type State (Static vs Field)
const valueType = computed({
	get: () => (props.node.right?.ref ? "field" : "static"),
	set: (type) => {
		if (type === "field") {
			props.node.right.value = "";
			if (!props.node.right.ref) props.node.right.ref = context.alias + ".";
		} else {
			props.node.right.ref = "";
		}
	},
});
</script>

<template>
	<div class="simple-condition">
		<div class="condition-main-row">
			<!-- Field -->
			<div class="condition-col field-col">
				<FieldPickerControl
					:df="{ label: '', read_only: readOnly }"
					v-model="node.left.ref"
					:fields="docFields"
					:disabled="readOnly"
					class="w-100 m-0"
				/>
			</div>

			<!-- Operator -->
			<div class="condition-col operator-col">
				<select
					v-model="node.op"
					class="form-control input-xs operator-select"
					:disabled="readOnly"
				>
					<option v-for="op in operators" :key="op.value" :value="op.value">
						{{ op.label }}
					</option>
				</select>
			</div>

			<!-- Value Group (Type + Value) -->
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
				<select
					v-model="valueType"
					class="form-control input-xs value-type-select"
					:disabled="readOnly"
				>
					<option value="static">{{ __("Static") }}</option>
					<option value="field">{{ __("Field") }}</option>
				</select>

				<div class="value-input-wrapper">
					<div
						v-if="selectedField?.fieldtype === 'Dynamic Link' && valueType === 'static'"
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

					<template v-if="valueType === 'field'">
						<ContextPicker
							v-model="node.right.ref"
							:docFields="docFields"
							:disabled="readOnly"
						/>
					</template>
					<template v-else>
						<ControlFactory
							:df="{ ...valueFieldSchema, label: '' }"
							v-model="wrappedValue"
							:read_only="readOnly"
							:hideLabel="true"
						/>
					</template>
				</div>
			</div>
			<div v-else class="condition-col empty-value-col"></div>

			<!-- Remove -->
			<div class="condition-col action-col" v-if="!readOnly">
				<button
					class="btn btn-xs btn-link text-danger"
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
	background: #f8f9fa;
	border: 1px solid #e9ecef;
	border-radius: 4px;
	padding: 6px;
	transition: border-color 0.2s, background-color 0.2s;
}

.simple-condition:hover {
	border-color: #cbd5e1;
}

.condition-main-row {
	display: grid;
	grid-template-columns: 1.5fr 0.8fr 2.5fr auto;
	gap: 8px;
	align-items: center;
	overflow: visible !important;
}

.condition-col {
	min-width: 0;
}

.operator-select {
	font-weight: 600;
	color: #1e293b;
	background-color: #f1f5f9;
}

.value-group-col {
	display: flex;
	align-items: center;
	gap: 4px;
	background: #fff;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	padding: 2px;
}

.value-type-select {
	width: auto;
	min-width: 70px;
	border: none;
	background-color: #f8fafc;
	color: #64748b;
	font-weight: 600;
	font-size: 10px;
	text-transform: uppercase;
	height: 24px;
	border-inline-end: 1px solid #e2e8f0;
	border-radius: 4px 0 0 4px;
	cursor: pointer;
}

[dir="rtl"] .value-type-select {
	border-radius: 0 4px 4px 0;
}

.value-input-wrapper {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	overflow: visible !important;
}

.dynamic-dt-picker {
	margin-bottom: 4px;
}

.condition-main-row :deep(.form-control) {
	height: 28px;
	font-size: 12px;
	padding: 4px 8px;
	border: 1px solid transparent;
}

.condition-main-row :deep(.form-control:focus) {
	border-color: var(--primary);
	box-shadow: none;
}

.empty-value-col {
	flex: 1;
}

/* Responsive adjustments */
@media (max-width: 768px) {
	.condition-main-row {
		display: flex;
		flex-direction: column;
		gap: 8px;
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
