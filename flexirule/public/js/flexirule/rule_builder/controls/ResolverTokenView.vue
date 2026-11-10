<template>
	<node-view-wrapper class="resolver-token-wrapper" :class="{ 'is-selected': selected }">
		<span class="inline-resolver-token" :title="tokenTitle">
			<i v-if="tokenIcon" :class="tokenIcon" class="resolver-token-icon"></i>
			<span class="resolver-operation-name">{{ operationDisplayName }}</span>
		</span>
	</node-view-wrapper>
</template>

<script setup>
import { computed } from "vue";
import { nodeViewProps, NodeViewWrapper } from "@tiptap/vue-3";
import { getFunctionIcon } from "../../core/formula_registry";

const props = defineProps(nodeViewProps);

const operationName = computed(() => {
	const raw = props.node?.attrs?.config;
	const op =
		props.node?.attrs?.operation ||
		(raw && typeof raw === "object" ? raw.operation || raw.agg_op : "") ||
		props.node?.attrs?.family ||
		(raw && typeof raw === "object" ? raw.family || raw.kind : "") ||
		"resolver";
	return String(op);
});

const operationDisplayName = computed(() => {
	const op = operationName.value;
	return op.replace(/_/g, " ");
});

const tokenIcon = computed(() => {
	const fam = props.node?.attrs?.family || props.node?.attrs?.config?.family || "";
	const op = props.node?.attrs?.operation || props.node?.attrs?.config?.operation || "";
	if (fam === "math" || op === "formula") return "fa fa-calculator";
	if (fam === "date_time" || fam === "date") return "fa fa-calendar";
	if (fam === "lookup") return "fa fa-search";
	if (fam === "collection") return "fa fa-list-ol";
	if (fam === "text") return "fa fa-font";
	return getFunctionIcon(op, "fa fa-bolt");
});

const tokenTitle = computed(() => {
	const fam = props.node?.attrs?.family || props.node?.attrs?.config?.family || "";
	return fam ? `${fam}.${operationName.value}` : operationName.value;
});
</script>

<style scoped>
.resolver-token-wrapper {
	display: inline-block;
	vertical-align: middle;
	line-height: 1;
	margin: 0 2px;
}

.inline-resolver-token {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 7px;
	border-radius: 4px;
	background: var(--fxr-surface-subtle, #f1f5f9);
	color: var(--fxr-accent, #2563eb);
	border: 1px solid var(--fxr-border, #e2e8f0);
	font-family: var(--fxr-font-mono, monospace);
	font-size: 11px;
	font-weight: 600;
	user-select: all;
	cursor: default;
}

.resolver-token-icon {
	font-size: 10px;
	opacity: 0.85;
}

.resolver-token-wrapper.is-selected .inline-resolver-token {
	outline: 2px solid var(--fxr-accent, #2563eb);
	border-color: var(--fxr-accent, #2563eb);
}
</style>
