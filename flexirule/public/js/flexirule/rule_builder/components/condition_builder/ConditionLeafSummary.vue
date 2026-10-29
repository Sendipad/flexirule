<template>
	<div class="condition-leaf-summary">
		<span class="operand-summary left">{{ formatOperand(domain.left) }}</span>
		<span class="operator-badge badge badge-secondary">{{ operatorLabel }}</span>
		<span v-if="requiresRightOperand" class="operand-summary right">{{ formatOperand(domain.right) }}</span>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	domain: {
		type: Object,
		required: true,
	},
	operators: {
		type: Array,
		default: () => [],
	},
});

const currentOperatorMeta = computed(() => {
	return props.operators.find((op) => op.id === props.domain?.op);
});

const operatorLabel = computed(() => {
	return currentOperatorMeta.value?.label || props.domain?.op || "equals";
});

const requiresRightOperand = computed(() => {
	return currentOperatorMeta.value ? currentOperatorMeta.value.arity !== 1 : true;
});

function formatOperand(operand) {
	if (!operand) return "-";

	if (operand.value_type === "variable") {
		return operand.path || "-";
	}

	if (operand.value_type === "static") {
		if (operand.value === null || operand.value === undefined || operand.value === "") {
			return '""';
		}
		return typeof operand.value === "string" ? `"${operand.value}"` : String(operand.value);
	}

	if (operand.value_type === "resolver") {
		return `resolver:${operand.resolver?.resolver_id || "func"}`;
	}

	return JSON.stringify(operand);
}
</script>

<style scoped>
.condition-leaf-summary {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-size: 13px;
	color: var(--fxr-text-base, #374151);
}

.operand-summary {
	font-family: monospace;
	font-weight: 600;
	padding: 2px 6px;
	border-radius: 4px;
	background-color: var(--fxr-bg-subtle, #f3f4f6);
}

.operator-badge {
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: 0.5px;
}
</style>
