<template>
	<div class="d-flex flex-column fxr-gap-1">
		<ComboBoxControl
			v-model="modelValue.field_a"
			:options="numericFieldOptions"
			:read_only="readOnly"
			:df="{ label: __('Field A') }"
			:class="{ 'is-invalid': !isFieldAValid }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<SelectControl
			v-model="modelValue.math_op"
			:options="mathOpOptions"
			:read_only="readOnly"
			:df="{ label: __('Operator') }"
		/>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Field B / Value") }}</label>
		<div class="d-flex fxr-gap-2">
			<SelectControl
				class="flex-1"
				v-model="modelValue.field_b_type"
				:options="fieldBTypeOptions"
				:read_only="readOnly"
				no-label
			/>
			<ComboBoxControl
				v-if="modelValue.field_b_type === 'field'"
				class="flex-1"
				v-model="modelValue.field_b"
				:options="numericFieldOptions"
				:read_only="readOnly"
				no-label
				:class="{ 'is-invalid': !isFieldBValid }"
				:placeholder="__('Select field...')"
			/>
			<DataControl
				v-else
				class="flex-1"
				v-model="modelValue.constant_b"
				:df="{ fieldtype: 'Float' }"
				:read_only="readOnly"
				no-label
				:placeholder="__('Enter value')"
			/>
		</div>
	</div>
	<div class="d-flex flex-column fxr-gap-1 mt-2">
		<label class="fxr-label-sm">{{ __("Round To") }}</label>
		<div class="d-flex align-items-center fxr-gap-2">
			<DataControl
				style="width: 80px"
				v-model="modelValue.precision"
				:df="{ fieldtype: 'Int' }"
				:read_only="readOnly"
				no-label
			/>
			<span class="text-muted fxr-text-xs">{{ __("decimal places") }}</span>
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

const mathOpOptions = [
	{ value: "+", label: __("Add (+)") },
	{ value: "-", label: __("Subtract (-)") },
	{ value: "*", label: __("Multiply (×)") },
	{ value: "/", label: __("Divide (÷)") },
];

const fieldBTypeOptions = [
	{ value: "field", label: __("Document Field") },
	{ value: "constant", label: __("Fixed Value") },
];

const numericFieldOptions = computed(() => {
	const dt = store.rule_doc?.document_type || props.doctype;
	if (!dt) return [];
	const fields = store.doc_meta[dt];
	if (!fields || !Array.isArray(fields)) return [];
	return fields
		.filter((f) => ["Int", "Float", "Currency", "Percent"].includes(f.fieldtype))
		.map((f) => {
			let realLabel = f.label;
			const match = f.label?.match(/\((.*?)\)/);
			if (match && match[1]) realLabel = match[1];
			return {
				label: `${realLabel} (${f.fieldname})`,
				value: f.value || f.fieldname,
			};
		});
});

const isFieldAValid = computed(() => {
	if (!props.modelValue.field_a) return true; // Optional or handled by overall validation
	return numericFieldOptions.value.some((opt) => opt.value === props.modelValue.field_a);
});

const isFieldBValid = computed(() => {
	if (props.modelValue.field_b_type !== "field") return true;
	if (!props.modelValue.field_b) return true;
	return numericFieldOptions.value.some((opt) => opt.value === props.modelValue.field_b);
});
</script>
