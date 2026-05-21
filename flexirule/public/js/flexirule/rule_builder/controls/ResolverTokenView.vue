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
	display: inline-block;
	vertical-align: middle;
	line-height: 1;
}

.resolver-token-wrapper.is-selected :deep(.fxr-token) {
	outline: 2px solid var(--fxr-accent);
}
</style>
