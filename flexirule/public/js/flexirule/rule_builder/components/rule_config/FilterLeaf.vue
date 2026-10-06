<template>
	<FilterGroup
		ref="filterGroupRef"
		:modelValue="modelValue"
		:doctype="doctype"
		:nodeId="nodeId"
		:readOnly="readOnly"
		:variableOptions="variableOptions"
		:showValidation="showValidation"
		:navigableFields="navigableFields"
		:singleRow="true"
		:hideActions="true"
		@update:modelValue="handleUpdate"
	/>
</template>

<script setup>
import { ref } from "vue";
import { useNavigableFields } from "../../composables/useNavigableFields";
import FilterGroup from "./FilterGroup.vue";

const filterGroupRef = ref(null);

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

// Each tree leaf owns one stable navigation composable instance.
const navigableFields = useNavigableFields(
	() => props.doctype,
	() => props.modelValue?.[0]?.field || ""
);

function handleUpdate(value) {
	emit("update:modelValue", value);
}

async function validate() {
	return (
		(await filterGroupRef.value?.validate?.()) || {
			valid: true,
			errors: [],
		}
	);
}

defineExpose({ validate });
</script>
