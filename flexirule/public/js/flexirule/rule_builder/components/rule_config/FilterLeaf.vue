<template>
	<FilterGroup
		:modelValue="modelValue"
		:doctype="doctype"
		:nodeId="nodeId"
		:readOnly="readOnly"
		:variableOptions="variableOptions"
		:showValidation="showValidation"
		:singleRow="true"
		:hideActions="true"
		@update:modelValue="handleUpdate"
	/>
</template>

<script setup>
import FilterGroup from "./FilterGroup.vue";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

function handleUpdate(value) {
	emit("update:modelValue", value);
}

async function validate() {
	// FilterGroup is intentionally retained as the legacy collection editor.
	// In the tree, this instance owns exactly one row, so its per-row navigation
	// state is isolated to this FilterLeaf instance.
	return (await Promise.resolve()).then(() => ({ valid: true, errors: [] }));
}

defineExpose({ validate });
</script>
