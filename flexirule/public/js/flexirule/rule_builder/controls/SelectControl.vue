<!--
  SelectControl - Styled dropdown using ComboBoxControl
-->
<script setup>
import { computed, ref } from "vue";
import ComboBoxControl from "./ComboBoxControl.vue";

const props = defineProps({
	df: Object,
	modelValue: [String, Number],
	read_only: Boolean,
	no_label: Boolean,
	hideLabel: { type: Boolean, default: false },
	hideDescription: { type: Boolean, default: false },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change"]);

const comboRef = ref(null);

const options = computed(() => {
	let opts = props.df?.options;
	let finalOptions = [];

	if (opts) {
		// String options (newline separated)
		if (typeof opts === "string") {
			finalOptions = opts
				.split("\n")
				.filter(Boolean)
				.map((opt) => ({
					label: __(opt.trim()),
					value: opt.trim(),
				}));
		}
		// Array of strings
		else if (Array.isArray(opts) && opts.length && typeof opts[0] === "string") {
			finalOptions = opts.map((opt) => ({
				label: __(opt),
				value: opt,
			}));
		}
		// Array of objects with label/value
		else if (Array.isArray(opts)) {
			finalOptions = opts.map((opt) => ({
				label: __(opt.label || opt.value),
				value: opt.value,
			}));
		}
	}

	// Add "Select..." option if not required
	if (!props.df?.reqd) {
		finalOptions.unshift({
			label: __("Select..."),
			value: "",
		});
	}

	return finalOptions;
});

function on_change(value) {
	emit("update:modelValue", value);
	emit("change", value);
}

function validate() {
	return comboRef.value?.validate() || { valid: true, errors: [] };
}

defineExpose({ validate });
</script>

<template>
	<ComboBoxControl
		ref="comboRef"
		:df="df"
		:model-value="modelValue"
		:options="options"
		:read_only="read_only || df?.read_only"
		:hide-label="hideLabel || no_label"
		:hide-description="hideDescription"
		:show-validation="showValidation"
		trigger="button"
		:hide-search="true"
		@update:model-value="on_change"
	/>
</template>

<style scoped>
/* Scoped styles removed as ComboBoxControl handles the layout */
</style>
