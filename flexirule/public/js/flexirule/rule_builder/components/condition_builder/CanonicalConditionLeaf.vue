<template>
	<div class="canonical-condition-leaf" :class="{ 'is-invalid': hasError }">
		<div
			v-if="node.is_unsupported"
			class="unsupported-alert alert alert-warning mb-2 py-1 px-2 small"
		>
			<i class="fa fa-exclamation-triangle mr-1"></i>
			<span>{{ node.unsupported_reason || __("Unsupported legacy condition format") }}</span>
		</div>

		<div class="condition-main-row">
			<!-- Left Operand (FlexValueControl) -->
			<div class="condition-col operand-col left-col">
				<FlexValueControl
					v-model="leftValueModel"
					:context="{
						referenceDoctype: currentDocType,
						isLeftOperand: true,
					}"
					:engine="store"
					:doc="store?.rule_doc"
					:variableOptions="variableOptions"
					:readOnly="readOnly"
					:disabled="readOnly"
					class="w-100 min-w-0"
				/>
			</div>

			<!-- Operator Select -->
			<div class="condition-col operator-col">
				<SelectControl
					class="operator-select"
					:df="{
						fieldtype: 'Select',
						options: operatorOptions,
						reqd: 1,
						read_only: readOnly,
					}"
					:modelValue="node.operator"
					:read_only="readOnly"
					:hideLabel="true"
					@update:modelValue="onOperatorChange"
				/>
			</div>

			<!-- Right Operand (FlexValueControl) -->
			<div v-if="!isUnary" class="condition-col operand-col right-col">
				<FlexValueControl
					v-model="rightValueModel"
					:context="{
						referenceDoctype: rightReferenceDocType,
						operator: node.operator,
					}"
					:engine="store"
					:doc="store?.rule_doc"
					:variableOptions="variableOptions"
					:readOnly="readOnly"
					:disabled="readOnly"
					class="w-100 min-w-0"
				/>
			</div>
			<div v-else class="condition-col empty-col"></div>

			<!-- Action (Remove) -->
			<div v-if="!readOnly" class="condition-col action-col">
				<button
					type="button"
					class="fxr-btn fxr-btn--icon fxr-btn--danger"
					@click="$emit('remove')"
					:title="__('Remove')"
				>
					<i class="fa fa-trash"></i>
				</button>
			</div>
		</div>

		<div v-if="nodeErrors.length" class="node-errors mt-1">
			<div v-for="(err, idx) in nodeErrors" :key="idx" class="text-danger small">
				<i class="fa fa-info-circle mr-1"></i>{{ err }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import FlexValueControl from "../../controls/FlexValueControl.vue";
import SelectControl from "../../controls/SelectControl.vue";
import {
	UNARY_OPERATORS,
	toCanonicalFlexValue,
	fieldExpressionToCanonicalVariable,
} from "./canonical_condition_adapter.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	contract: { type: Object, default: () => ({}) },
	docFields: { type: Array, default: () => [] },
	variableOptions: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
	store: { type: Object, default: null },
	currentDocType: { type: String, default: "" },
	errors: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue", "change", "remove"]);

const isUnary = computed(() => {
	const op = props.node.operator;
	return UNARY_OPERATORS.has(op) || props.contract?.operators?.[op]?.arity === 1;
});

const operatorOptions = computed(() => {
	const ops = props.contract?.operators;
	if (ops && Object.keys(ops).length > 0) {
		return Object.entries(ops).map(([k, v]) => ({
			label: v.label || k,
			value: k,
		}));
	}
	return [
		{ label: "Equals (==)", value: "eq" },
		{ label: "Not Equals (!=)", value: "ne" },
		{ label: "Greater Than (>)", value: "gt" },
		{ label: "Greater Than or Equal (>=)", value: "gte" },
		{ label: "Less Than (<)", value: "lt" },
		{ label: "Less Than or Equal (<=)", value: "lte" },
		{ label: "In", value: "in" },
		{ label: "Not In", value: "not_in" },
		{ label: "Contains", value: "contains" },
		{ label: "Not Contains", value: "not_contains" },
		{ label: "Starts With", value: "starts_with" },
		{ label: "Ends With", value: "ends_with" },
		{ label: "Is Set", value: "is_set" },
		{ label: "Is Not Set", value: "is_not_set" },
		{ label: "Is Empty", value: "is_empty" },
		{ label: "Is Not Empty", value: "is_not_empty" },
		{ label: "Is Submittable", value: "is_submittable" },
		{ label: "Has Field", value: "has_field" },
	];
});

const nodeErrors = computed(() => props.errors || []);
const hasError = computed(() => nodeErrors.value.length > 0 || props.node.is_unsupported);

const leftValueModel = computed({
	get() {
		return props.node.left || { mode: "variable", path: { scope: "doc", segments: [] } };
	},
	set(val) {
		let canonical = val;
		if (typeof val === "string") {
			canonical = fieldExpressionToCanonicalVariable(val);
		} else if (val && typeof val === "object" && !val.mode) {
			canonical = toCanonicalFlexValue(val);
		}
		props.node.left = canonical;
		emit("change", props.node);
	},
});

const rightReferenceDocType = computed(() => {
	const left = props.node.left;
	if (left?.mode === "variable" && left.path?.segments?.length) {
		const fieldname = left.path.segments[0];
		const field = (props.docFields || []).find((f) => f.fieldname === fieldname);
		if (field?.fieldtype === "Link" && field.options) {
			return field.options;
		}
	}
	return props.currentDocType;
});

const rightValueModel = computed({
	get() {
		return props.node.right || { mode: "static", value_type: "string", value: "" };
	},
	set(val) {
		let canonical = val;
		if (val && typeof val === "object" && !val.mode) {
			canonical = toCanonicalFlexValue(val);
		} else if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
			canonical = toCanonicalFlexValue(val);
		}
		props.node.right = canonical;
		emit("change", props.node);
	},
});

function onOperatorChange(newOp) {
	props.node.operator = newOp;
	if (UNARY_OPERATORS.has(newOp) || props.contract?.operators?.[newOp]?.arity === 1) {
		props.node.right = null;
	} else if (!props.node.right) {
		props.node.right = { mode: "static", value_type: "string", value: "" };
	}
	emit("change", props.node);
}
</script>

<style scoped>
.canonical-condition-leaf {
	background: var(--fxr-bg-card, #ffffff);
	border: 1px solid var(--fxr-border, #e5e7eb);
	border-radius: var(--fxr-radius-md, 6px);
	padding: var(--fxr-space-1, 4px) var(--fxr-space-2, 8px);
	transition: border-color var(--fxr-transition-fast), background-color var(--fxr-transition-fast);
}

.canonical-condition-leaf:hover {
	border-color: var(--fxr-border-strong, #cbd5e1);
}

.canonical-condition-leaf.is-invalid {
	border-color: var(--fxr-text-danger, #ef4444) !important;
	background-color: var(--fxr-danger-soft, #fef2f2) !important;
	box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.1);
}

.condition-main-row {
	display: grid;
	grid-template-columns: 1.8fr 1.2fr 2.4fr auto;
	gap: var(--fxr-space-2, 8px);
	align-items: center;
	position: relative;
	z-index: 1;
}

.condition-col {
	min-width: 0;
}

.operator-select {
	width: 100%;
	min-width: 100px;
	font-weight: var(--fxr-weight-semibold, 600);
	color: var(--fxr-text-strong, #1f2937);
	background-color: var(--fxr-surface-2, #f3f4f6);
}

.action-col .fxr-btn--danger {
	color: var(--fxr-text-danger, #ef4444);
	opacity: 0.8;
}

.action-col .fxr-btn--danger:hover {
	opacity: 1;
}

@media (max-width: 768px) {
	.condition-main-row {
		display: flex;
		flex-direction: column;
		gap: var(--fxr-space-2, 8px);
		align-items: stretch;
	}
	.condition-col {
		width: 100%;
	}
}
</style>
