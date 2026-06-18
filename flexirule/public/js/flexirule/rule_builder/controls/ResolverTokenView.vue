<template>
	<node-view-wrapper
		class="resolver-token-wrapper"
		:class="{ 'is-selected': selected, 'is-invalid': isInvalid }"
	>
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
import { computed, inject } from "vue";
import ValueResolverControl from "./ValueResolverControl.vue";

const props = defineProps(nodeViewProps);

const logicValidation = inject("logicValidation", null);
const isInvalid = computed(() => {
	if (!logicValidation || !logicValidation.showValidation) return false;
	const key = props.node.attrs._key;
	if (!key) return false;
	return logicValidation.errors.some((e) => e._key === key);
});

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
	vertical-align: top;
	line-height: 1;
	margin-top: 1px;
}

.resolver-token-wrapper.is-selected :deep(.fxr-token) {
	outline: 2px solid var(--fxr-accent);
}

.resolver-token-wrapper.is-invalid :deep(.fxr-token) {
	border-color: var(--fxr-text-danger) !important;
	background-color: var(--fxr-bg-danger) !important;
	box-shadow: 0 0 0 2px var(--fxr-bg-danger) !important;
}
</style>
