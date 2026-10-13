<template>
	<node-view-wrapper class="resolver-token-wrapper" :class="{ 'is-selected': selected }">
		<ValueResolverControl
			viewMode="popover"
			:modelValue="node.attrs.config"
			:doctype="extension.options.doctype"
			:readOnly="extension.options.readOnly"
			:context="extension.options.context"
			@update:modelValue="handleUpdate"
		/>
	</node-view-wrapper>
</template>

<script setup>
import { nodeViewProps, NodeViewWrapper } from "@tiptap/vue-3";
import ValueResolverControl from "./ValueResolverControl.vue";

const props = defineProps(nodeViewProps);

const handleUpdate = (config, details) => {
	// Directly update attributes with both config and details (label, expression)
	props.updateAttributes({
		config: config,
		label: details?.label || "",
		expression: details?.expression || "",
	});
};
</script>

<style scoped>
.resolver-token-wrapper {
	display: inline-flex;
	align-items: center;
	vertical-align: middle;
	max-width: min(360px, 78vw);
	margin: 1px 2px;
	line-height: 1.2;
}

.resolver-token-wrapper :deep(.fxr-token) {
	max-width: 100%;
	min-width: 0;
	text-align: left;
}

.resolver-token-wrapper.is-selected :deep(.fxr-token) {
	outline: 2px solid var(--fxr-accent);
	outline-offset: 1px;
}

.resolver-token-wrapper :deep(.fxr-token__details) {
	max-width: 100%;
}

@media (max-width: 480px) {
	.resolver-token-wrapper {
		max-width: 240px;
	}
}
</style>
