<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Start Date") }}</label>
		<div class="d-flex fxr-gap-2">
			<SelectControl
				class="flex-1"
				v-model="modelValue.diff_start_type"
				:options="typeOptions"
				:read_only="readOnly"
				no-label
			/>
			<ComboBoxControl
				v-if="modelValue.diff_start_type === 'doc_field'"
				class="flex-1"
				v-model="modelValue.diff_start_field"
				:options="dateFieldOptions"
				:read_only="readOnly"
				no-label
				:placeholder="__('Select field...')"
			/>
		</div>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("End Date") }}</label>
		<div class="d-flex fxr-gap-2">
			<SelectControl
				class="flex-1"
				v-model="modelValue.diff_end_type"
				:options="typeOptions"
				:read_only="readOnly"
				no-label
			/>
			<ComboBoxControl
				v-if="modelValue.diff_end_type === 'doc_field'"
				class="flex-1"
				v-model="modelValue.diff_end_field"
				:options="dateFieldOptions"
				:read_only="readOnly"
				no-label
				:placeholder="__('Select field...')"
			/>
		</div>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<SelectControl
			v-model="modelValue.diff_unit"
			:options="unitOptions"
			:read_only="readOnly"
			:df="{ label: __('Result Unit') }"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import { __ } from "../utils";
import SelectControl from "../../SelectControl.vue";
import ComboBoxControl from "../../ComboBoxControl.vue";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const typeOptions = [
	{ value: "today", label: __("Today") },
	{ value: "doc_field", label: __("Document Field") },
];

const unitOptions = [
	{ value: "days", label: __("Days") },
	{ value: "months", label: __("Months") },
	{ value: "years", label: __("Years") },
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
