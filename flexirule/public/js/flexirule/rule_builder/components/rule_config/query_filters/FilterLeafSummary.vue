<template>
	<div class="filter-leaf-summary" :class="{ 'is-invalid': !summary.isValid }">
		<template v-if="!summary.isValid">
			<span class="summary-badge summary-badge--invalid">
				<i class="fa fa-exclamation-circle" aria-hidden="true"></i>
				<span>{{ summary.invalidReason }}</span>
			</span>
		</template>
		<template v-else>
			<span class="summary-field">{{ summary.fieldLabel }}</span>
			<span class="summary-operator">{{ summary.operatorLabel }}</span>
			<span v-if="summary.hasValue" class="summary-value">{{ summary.valueLabel }}</span>
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useMetaStore } from "../../../stores/useMetaStore";
import { formatFilterSummary } from "./filter_summary_formatter.mjs";

const props = defineProps({
	node: { type: Object, required: true },
	doctype: { type: String, required: true },
	variableOptions: { type: Array, default: null },
});

const metaStore = useMetaStore();

const summary = computed(() => formatFilterSummary(props.node, props.doctype, metaStore.doc_meta));
</script>

<style scoped>
.filter-leaf-summary {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-1, 6px);
	padding: var(--fxr-space-1, 4px) var(--fxr-space-2, 8px);
	border-radius: var(--fxr-radius-md, 6px);
	background: var(--fxr-bg-card, #fff);
	border: 1px solid var(--fxr-border-subtle, #e5e7eb);
	font-size: var(--fxr-text-sm, 12px);
	line-height: 1.4;
	color: var(--fxr-text, #111827);
	min-width: 0;
	box-sizing: border-box;
}

.summary-field {
	font-weight: var(--fxr-weight-semibold, 600);
	color: var(--fxr-text-strong, #111827);
}

.summary-operator {
	color: var(--fxr-text-muted, #6b7280);
	font-style: normal;
}

.summary-value {
	font-weight: var(--fxr-weight-medium, 500);
	color: var(--fxr-text, #111827);
	background: var(--fxr-surface-soft, #f3f4f6);
	padding: 1px 6px;
	border-radius: var(--fxr-radius-sm, 4px);
}

.summary-badge--invalid {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-1, 4px);
	color: var(--fxr-text-danger, #dc2626);
	font-weight: var(--fxr-weight-medium, 500);
}
</style>
