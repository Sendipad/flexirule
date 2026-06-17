<template>
	<div class="d-flex flex-column fxr-gap-1">
		<SelectControl
			v-model="modelValue.fmt_op"
			:options="formatOptions"
			:read_only="readOnly"
			:df="{ label: __('Format Type') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<ComboBoxControl
			v-model="modelValue.fmt_field"
			:options="activeFieldOptions"
			:read_only="readOnly"
			:df="{ label: __('Field') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<DataControl
			v-model="modelValue.fmt_config"
			:read_only="readOnly"
			:df="{
				label: configLabel,
				placeholder: modelValue.fmt_op === 'format_date' ? 'YYYY-MM-DD' : '',
			}"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import { __ } from "../utils";
import SelectControl from "../../SelectControl.vue";
import ComboBoxControl from "../../ComboBoxControl.vue";
import DataControl from "../../DataControl.vue";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const formatOptions = [
	{ value: "format_date", label: __("Date/Time Format") },
	{ value: "fmt_money", label: __("Currency Format") },
	{ value: "format", label: __("String Template") },
];

const configLabel = computed(() => {
	if (props.modelValue.fmt_op === "fmt_money") return __("Currency (Field or Code)");
	if (props.modelValue.fmt_op === "format_date") return __("Date Format (e.g. YYYY-MM-DD)");
	return __("Template");
});

const activeFieldOptions = computed(() => {
	if (props.modelValue.fmt_op === "fmt_money") return numericFieldOptions.value;
	if (props.modelValue.fmt_op === "format_date") return dateFieldOptions.value;
	return stringFieldOptions.value;
});

const dateFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Date", "Datetime"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});

const numericFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});

const stringFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Data", "Text", "Small Text", "Select"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});
</script>
