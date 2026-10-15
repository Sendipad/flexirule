<template>
	<ComboBoxControl
		:df="{ label: label || __('Select field'), fieldtype: 'FieldPicker', reqd: reqd ? 1 : 0 }
		:options="navigableFields.currentFields.value"
		:doctype="doctype"
		:modelValue="modelValue"
		:read_only="readOnly"
		:placeholder="placeholder || label || __('Select field')"
		:showValidation="showValidation"
		:trigger="'button'"
		:hideLabel="true"
		:navigable="canNavigate"
		:navStack="navigableFields.navStack.value"
		@navigate="navigableFields.handleNavigate"
		@back="navigableFields.handleBack"
		@update:modelValue="onUpdate"
	/>
</template>

<script setup>
import { computed } from "vue";
import ComboBoxControl from "../../../../controls/ComboBoxControl.vue";
import { useNavigableFields } from "../../../../composables/useNavigableFields";

const props = defineProps({
	doctype: { type: String, required: true },
	modelValue: { type: String, default: "" },
	readOnly: { type: Boolean, default: false },
	rootOnly: { type: Boolean, default: false },
	label: { type: String, default: "" },
	reqd: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
	placeholder: { type: String, default: "" },
});
const emit = defineEmits(["update:modelValue"]);

const navigableFields = useNavigableFields(
	computed(() => props.doctype),
	() => (props.rootOnly ? "" : props.modelValue)
);

// The branch capability tests show Frappe v15 does not parse multi-level
// relationship field paths, so allow browsing only from the root DocType.
const canNavigate = computed(() => {
	if (props.rootOnly) return false;
	const pathPrefix = navigableFields.currentContext.value?.pathPrefix || "";
	return pathPrefix.split(".").filter(Boolean).length === 0;
});

function onUpdate(value) {
	emit("update:modelValue", value);
	navigableFields.resetStack();
}
</script>
