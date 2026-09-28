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
			v-model="modelValue.component"
			:options="componentOptions"
			:read_only="readOnly"
			:df="{ label: __('Component to Extract') }"
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
			component: "year",
		}),
	},
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const componentOptions = [
	{ value: "year", label: __("Year") },
	{ value: "month", label: __("Month (1 - 12)") },
	{ value: "day", label: __("Day of Month (1 - 31)") },
	{ value: "weekday", label: __("Weekday (ISO: 1=Mon .. 7=Sun)") },
	{ value: "quarter", label: __("Quarter (1 - 4)") },
	{ value: "hour", label: __("Hour (0 - 23)") },
	{ value: "minute", label: __("Minute (0 - 59)") },
	{ value: "second", label: __("Second (0 - 59)") },
];

const dateFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Date", "Datetime", "Time"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});
</script>
