<template>
	<node-view-wrapper class="resolver-token-wrapper" :class="{ 'is-selected': selected }">
		<ValueResolverControl
			ref="resolverControlRef"
			viewMode="popover"
			:modelValue="currentModelValue"
			:family="node.attrs.family"
			:operation="node.attrs.operation"
			:valueType="node.attrs.value_type"
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

import { computed, ref, onMounted, nextTick } from "vue";

const props = defineProps(nodeViewProps);
const resolverControlRef = ref(null);

onMounted(() => {
	if (props.node?.attrs?.autoOpen && !props.extension.options.readOnly) {
		nextTick(() => {
			resolverControlRef.value?.open?.();
			props.updateAttributes({ autoOpen: false });
		});
	}
});

const currentModelValue = computed(() => {
	const raw = props.node?.attrs?.config;
	if (raw && typeof raw === "object") {
		return {
			...raw,
			family: props.node?.attrs?.family || raw.family,
			operation: props.node?.attrs?.operation || raw.operation,
			value_type: props.node?.attrs?.value_type || raw.value_type,
		};
	}
	return raw;
});

const handleUpdate = (config, details) => {
	const fam = config?.family || props.node?.attrs?.family || "";
	const op = config?.operation || props.node?.attrs?.operation || "";
	const vType = config?.value_type || props.node?.attrs?.value_type || "";

	props.updateAttributes({
		config: config,
		family: fam,
		operation: op,
		value_type: vType,
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
</style>
