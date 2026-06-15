<template>
	<div class="d-flex flex-column fxr-gap-1">
		<label class="fxr-label-sm">{{ __("Child Table") }}</label>
		<select class="fxr-select" v-model="modelValue.agg_table" :disabled="readOnly">
			<option value="">{{ __("Select child table...") }}</option>
			<option v-for="opt in tableFieldOptions" :key="opt.value" :value="opt.value">
				{{ opt.label }}
			</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2" v-if="modelValue.agg_op !== 'count'">
		<label class="fxr-label-sm">{{ __("Numeric Field") }}</label>
		<select class="fxr-select" v-model="modelValue.agg_field" :disabled="readOnly">
			<option value="">{{ __("Select field...") }}</option>
			<option v-for="opt in aggFieldOptions" :key="opt.value" :value="opt.value">
				{{ opt.label }}
			</option>
		</select>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Operation") }}</label>
		<select class="fxr-select" v-model="modelValue.agg_op" :disabled="readOnly">
			<option value="sum">{{ __("Sum") }}</option>
			<option value="avg">{{ __("Average") }}</option>
			<option value="count">{{ __("Count Rows") }}</option>
		</select>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import { __ } from "../utils";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
});

const store = useStore();

const tableFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => f.fieldtype === "Table")
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
			options: f.options,
		}));
});

const aggFieldOptions = computed(() => {
	const tableField = props.modelValue.agg_table;
	if (!tableField) return [];
	const tableMeta = tableFieldOptions.value.find((f) => f.value === tableField);
	if (!tableMeta || !tableMeta.options) return [];
	const childFields = store.doc_meta[tableMeta.options];
	if (!childFields || !Array.isArray(childFields)) return [];
	return childFields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});
</script>
