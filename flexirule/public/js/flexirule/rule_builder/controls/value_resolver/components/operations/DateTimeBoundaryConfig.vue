<template>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<ComboBoxControl
			v-model="modelValue.base_field"
			:options="dateFieldOptions"
			:read_only="readOnly"
			:df="{ label: __('Date / Time Field') }"
			:placeholder="__('Select field...')"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<SelectControl
			v-model="modelValue.boundary_type"
			:options="boundaryTypeOptions"
			:read_only="readOnly"
			:df="{ label: __('Boundary Period') }"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../../stores";
import { __ } from "../../utils";
import SelectControl from "../../../SelectControl.vue";
import ComboBoxControl from "../../../ComboBoxControl.vue";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({
			base_field: "",
			boundary_type: "start_of_month",
		}),
	},
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const boundaryTypeOptions = [
	{ value: "start_of_day", label: __("Start of Day") },
	{ value: "end_of_day", label: __("End of Day") },
	{ value: "start_of_week", label: __("Start of Week") },
	{ value: "end_of_week", label: __("End of Week") },
	{ value: "start_of_month", label: __("Start of Month") },
	{ value: "end_of_month", label: __("End of Month") },
	{ value: "start_of_quarter", label: __("Start of Quarter") },
	{ value: "end_of_quarter", label: __("End of Quarter") },
	{ value: "start_of_year", label: __("Start of Year") },
	{ value: "end_of_year", label: __("End of Year") },
];

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
</script>
