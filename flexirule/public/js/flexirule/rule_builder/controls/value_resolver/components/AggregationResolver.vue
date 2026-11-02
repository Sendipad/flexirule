<template>
	<div class="d-flex flex-column fxr-gap-1">
		<ComboBoxControl
			v-model="modelValue.agg_table"
			:options="tableFieldOptions"
			:read_only="readOnly"
			:df="{ label: __('Child Table') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2" v-if="modelValue.agg_op !== 'count'">
		<ComboBoxControl
			v-model="modelValue.agg_field"
			:options="aggFieldOptions"
			:read_only="readOnly"
			:df="{ label: __('Numeric Field') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<SelectControl
			v-model="modelValue.agg_op"
			:options="opOptions"
			:read_only="readOnly"
			:df="{ label: __('Operation') }"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useMetaStore, useRuleStore } from "../../../stores";
import { __ } from "../utils";
import ComboBoxControl from "../../ComboBoxControl.vue";
import SelectControl from "../../SelectControl.vue";

const props = defineProps({
	modelValue: Object,
	doctype: String,
	readOnly: Boolean,
});

const metaStore = useMetaStore();
const ruleStore = useRuleStore();

const opOptions = [
	{ value: "sum", label: __("Sum") },
	{ value: "avg", label: __("Average") },
	{ value: "count", label: __("Count Rows") },
];

const tableFieldOptions = computed(() => {
	const dt = ruleStore.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = metaStore.doc_meta[dt];
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
	const childFields = metaStore.doc_meta[tableMeta.options];
	if (!childFields || !Array.isArray(childFields)) return [];
	return childFields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => ({
			label: `${f.label || f.fieldname} (${f.fieldname})`,
			value: f.fieldname,
		}));
});
</script>
