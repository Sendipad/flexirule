<template>
	<CanonicalConditionBuilder
		ref="canonicalBuilderRef"
		v-bind="$attrs"
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
	/>
</template>

<script setup>
import { ref } from "vue";
import CanonicalConditionBuilder from "./CanonicalConditionBuilder.vue";

defineProps({
	modelValue: {
		type: Object,
		default: () => null,
	},
});

defineEmits(["update:modelValue"]);

const canonicalBuilderRef = ref(null);

function validate() {
	if (canonicalBuilderRef.value) {
		return canonicalBuilderRef.value.validate();
	}
	return { isValid: true, errors: [] };
}

defineExpose({
	validate,
});
</script>
