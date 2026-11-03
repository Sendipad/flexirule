<template>
	<div class="canonical-leaf-summary">
		<span class="leaf-operand font-monospace">{{ leftSummary }}</span>
		<span class="leaf-operator badge">{{ operatorLabel }}</span>
		<span v-if="!isUnary" class="leaf-operand font-monospace">{{ rightSummary }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { UNARY_OPERATORS } from "./canonical_condition_adapter.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	contract: { type: Object, default: () => ({}) },
});

const isUnary = computed(() => {
	const op = props.node.operator;
	return UNARY_OPERATORS.has(op) || props.contract?.operators?.[op]?.arity === 1;
});

const operatorLabel = computed(() => {
	const op = props.node.operator;
	return props.contract?.operators?.[op]?.label || op || "==";
});

function summarizeFlexValue(val) {
	if (!val || typeof val !== "object") return String(val ?? "");
	if (val.mode === "variable") {
		const path = val.path || {};
		const scope = path.scope || "doc";
		const segments = Array.isArray(path.segments) ? path.segments : [];
		return segments.length ? `${scope}.${segments.join(".")}` : scope;
	}
	if (val.mode === "static") {
		if (val.value === null) return "null";
		if (typeof val.value === "boolean") return val.value ? "true" : "false";
		return String(val.value ?? "");
	}
	if (val.mode === "resolver") {
		return `resolver(${val.family || ""}.${val.operation || ""})`;
	}
	if (val.mode === "template") {
		return "template(...)";
	}
	return JSON.stringify(val);
}

const leftSummary = computed(() => summarizeFlexValue(props.node.left));
const rightSummary = computed(() => summarizeFlexValue(props.node.right));
</script>

<style scoped>
.canonical-leaf-summary {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-2, 6px);
	font-size: var(--fxr-text-sm, 12px);
	color: var(--fxr-text-strong, #1f2937);
	padding: 2px 4px;
	border-radius: var(--fxr-radius-sm, 4px);
}
.leaf-operator {
	background-color: var(--fxr-surface-2, #f3f4f6);
	color: var(--fxr-accent, #2563eb);
	font-weight: var(--fxr-weight-bold, 700);
	padding: 2px 6px;
	border-radius: 4px;
}
.leaf-operand {
	color: var(--fxr-text-secondary, #4b5563);
}
</style>
