<template>
	<div class="d-flex flex-column fxr-gap-1">
		<SelectControl
			v-model="modelValue.str_op"
			:options="operationOptions"
			:read_only="readOnly"
			:df="{ label: __('Operation') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ labelA }}</label>
		<div class="d-flex gap-2">
			<SelectControl
				class="flex-1"
				v-model="modelValue.str_a_type"
				:options="typeOptions"
				:read_only="readOnly"
				no-label
			/>
			<ComboBoxControl
				v-if="modelValue.str_a_type === 'field'"
				class="flex-1"
				v-model="modelValue.str_a"
				:options="optionsA"
				:read_only="readOnly"
				no-label
				:placeholder="__('Select field...')"
			/>
			<DataControl
				v-else
				class="flex-1"
				v-model="modelValue.str_a"
				:read_only="readOnly"
				no-label
				:placeholder="__('Enter text')"
			/>
		</div>
	</div>
	<div
		class="d-flex flex-column fxr-gap-1 mt-2"
		v-if="['concat', 'fmt_money'].includes(modelValue.str_op)"
	>
		<label class="fxr-label-sm">{{ labelB }}</label>
		<div class="d-flex gap-2">
			<SelectControl
				class="flex-1"
				v-model="modelValue.str_b_type"
				:options="typeBOptions"
				:read_only="readOnly"
				no-label
			/>
			<ComboBoxControl
				v-if="modelValue.str_b_type === 'field'"
				class="flex-1"
				v-model="modelValue.str_b"
				:options="stringFieldOptions"
				:read_only="readOnly"
				no-label
				:placeholder="__('Select field...')"
			/>
			<DataControl
				v-else
				class="flex-1"
				v-model="modelValue.str_b"
				:read_only="readOnly"
				no-label
				:placeholder="modelValue.str_op === 'fmt_money' ? __('e.g. USD') : __('Enter text')"
			/>
		</div>
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

const operationOptions = [
	{ value: "concat", label: __("Concatenate") },
	{ value: "fmt_money", label: __("Format Currency") },
	{ value: "uppercase", label: __("Uppercase") },
	{ value: "lowercase", label: __("Lowercase") },
];

const typeOptions = [
	{ value: "field", label: __("Document Field") },
	{ value: "constant", label: __("Fixed Text") },
];

const typeBOptions = computed(() => {
	const fixedLabel =
		props.modelValue.str_op === "fmt_money" ? __("Fixed Currency") : __("Fixed Text");
	return [
		{ value: "field", label: __("Document Field") },
		{ value: "constant", label: fixedLabel },
	];
});

const labelA = computed(() => {
	return props.modelValue.str_op === "fmt_money" ? __("Numeric Field") : __("Value A");
});

const labelB = computed(() => {
	return props.modelValue.str_op === "fmt_money" ? __("Currency") : __("Value B");
});

const optionsA = computed(() => {
	return props.modelValue.str_op === "fmt_money"
		? numericFieldOptions.value
		: stringFieldOptions.value;
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
